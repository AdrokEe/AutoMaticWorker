"""Non-executing validation and bounded ZIP import."""
import ast
import json
import math
import re
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from jsonschema import Draft202012Validator
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import Version

from awm import __version__

ROOT = Path(__file__).resolve().parent.parent
MAX_BYTES = 20 * 1024 * 1024
MAX_FILES = 500
SCHEMA = json.loads((ROOT / "schemas/manifest.schema.json").read_text(encoding="utf-8"))
RESERVED = re.compile(r"^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)", re.I)


class FlowError(ValueError):
    pass


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    temp.replace(path)


def safe_name(name):
    path = PurePosixPath(name)
    if (not name or "\\" in name or path.is_absolute() or
            any(p in ("", ".", "..") or ":" in p or p.endswith((".", " ")) or
                RESERVED.match(p) or any(ord(c) < 32 for c in p)
                for p in name.rstrip("/").split("/"))):
        raise FlowError(f"包内路径不合法：{name}")
    return path


def validate_value(parameter, value, check_paths=True):
    kind = parameter["type"]
    if kind == "number":
        valid = type(value) in (int, float) and math.isfinite(value)
        if valid:
            valid = parameter.get("minimum", -math.inf) <= value <= parameter.get("maximum", math.inf)
    elif kind == "boolean":
        valid = type(value) is bool
    else:
        valid = isinstance(value, str) and len(value) <= 10000
        if kind == "enum":
            valid = valid and value in parameter["options"]
        elif kind in ("file", "directory") and valid and value and check_paths:
            target = Path(value)
            valid = target.is_file() if kind == "file" else target.is_dir()
    if not valid:
        raise FlowError(f"参数「{parameter['label']}」的类型、范围或路径不正确")


def validate_config(manifest, supplied):
    if not isinstance(supplied, dict):
        raise FlowError("配置必须是 JSON 对象")
    keys = {p["key"] for p in manifest["parameters"]}
    if set(supplied) - keys:
        raise FlowError("配置包含未声明的参数")
    config = {}
    for p in manifest["parameters"]:
        value = supplied.get(p["key"], p.get("default"))
        if value is None or value == "":
            if p.get("required"):
                raise FlowError(f"请填写「{p['label']}」")
            continue
        validate_value(p, value)
        config[p["key"]] = value
    return config


def public_config(manifest, config):
    return {p["key"]: config[p["key"]] for p in manifest["parameters"]
            if not p.get("secret") and p["key"] in config}


def validate_directory(directory):
    directory = Path(directory).resolve()
    try:
        files = [p for p in directory.rglob("*") if p.is_file() or p.is_symlink()]
        if len(files) > MAX_FILES or sum(p.stat().st_size for p in files) > MAX_BYTES:
            raise FlowError("流程包超过 500 个文件或 20 MB 限制")
        for p in files:
            safe_name(p.relative_to(directory).as_posix())
            if p.is_symlink() or not p.resolve().is_relative_to(directory):
                raise FlowError("流程包不能包含符号链接")
        manifest = read_json(directory / "manifest.json")
        errors = sorted(Draft202012Validator(SCHEMA).iter_errors(manifest), key=lambda e: str(e.path))
        if errors:
            e = errors[0]
            raise FlowError(f"清单错误 {'.'.join(map(str, e.path)) or 'manifest'}：{e.message}")
        safe_name(manifest["id"])
        if Version(__version__) not in SpecifierSet(manifest["platform"]):
            raise FlowError(f"平台版本不兼容：当前 {__version__}，要求 {manifest['platform']}")
        keys = [p["key"] for p in manifest["parameters"]]
        if len(keys) != len(set(keys)):
            raise FlowError("参数 key 不可重复")
        for p in manifest["parameters"]:
            if p.get("minimum", -math.inf) > p.get("maximum", math.inf):
                raise FlowError("参数最小值不能大于最大值")
            if "default" in p:
                validate_value(p, p["default"], check_paths=False)
        tree = ast.parse((directory / "flow.py").read_text(encoding="utf-8-sig"))
        if not any(isinstance(n, ast.FunctionDef) and n.name == "run" for n in tree.body):
            raise FlowError("flow.py 必须定义同步入口 run(ctx, config)")
        return manifest
    except (OSError, UnicodeError, json.JSONDecodeError, SyntaxError, InvalidSpecifier) as exc:
        raise FlowError(f"流程包无法读取：{exc}") from exc


def extract_package(archive, destination):
    try:
        with zipfile.ZipFile(archive) as zf:
            infos = zf.infolist()
            if len(infos) > MAX_FILES or sum(i.file_size for i in infos) > MAX_BYTES:
                raise FlowError("流程包超过 500 个文件或 20 MB 限制")
            seen = set()
            for info in infos:
                name = safe_name(info.filename)
                normalized = str(name).casefold()
                if normalized in seen:
                    raise FlowError("包内存在重复路径")
                seen.add(normalized)
                if stat.S_ISLNK(info.external_attr >> 16) or info.flag_bits & 1:
                    raise FlowError("不支持符号链接或加密 ZIP")
                target = Path(destination).joinpath(*name.parts)
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(info) as source, target.open("wb") as output:
                        shutil.copyfileobj(source, output)
        return validate_directory(destination)
    except (zipfile.BadZipFile, OSError, RuntimeError) as exc:
        raise FlowError(f"ZIP 包无法读取：{exc}") from exc


def pack(directory, output):
    directory, output = Path(directory).resolve(), Path(output).resolve()
    validate_directory(directory)
    if output.is_relative_to(directory):
        raise FlowError("输出 ZIP 必须放在流程目录之外")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(directory.rglob("*")):
            if path.is_file() and not any(p in ("__pycache__", ".git", ".venv") for p in path.parts):
                if path.name == ".env" or path.suffix in (".pyc", ".zip"):
                    continue
                zf.write(path, path.relative_to(directory).as_posix())
    with tempfile.TemporaryDirectory() as temp:
        extract_package(output, temp)
    return output

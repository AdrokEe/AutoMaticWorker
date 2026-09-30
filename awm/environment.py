"""Local-only browser configuration. This module never installs or downloads."""
import importlib.util
import os
import re
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from urllib.parse import urlparse

from awm.packages import FlowError, safe_name

DEFAULTS = {"backend": "playwright", "executable_path": "", "headless": False,
            "profile": "", "cdp_url": "", "input_mode": "browser", "interaction": "natural"}


def settings(value):
    if not isinstance(value, dict) or set(value) - set(DEFAULTS):
        raise FlowError("浏览器环境包含未知字段")
    result = {**DEFAULTS, **value}
    for key in DEFAULTS:
        if type(result[key]) is not type(DEFAULTS[key]):
            raise FlowError(f"浏览器环境字段类型错误：{key}")
    for key, choices in {"backend": ("playwright", "patchright"),
                         "input_mode": ("browser", "desktop"),
                         "interaction": ("direct", "natural")}.items():
        if result[key] not in choices:
            raise FlowError(f"浏览器环境选项无效：{key}")
    if result["profile"] and not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}", result["profile"]):
        raise FlowError("登录目录名称只允许字母、数字、下划线和短横线（1–64 位）")
    if result["profile"]:
        safe_name(result["profile"])
    if result["cdp_url"]:
        u = urlparse(result["cdp_url"])
        try:
            valid = (u.scheme == "http" and u.hostname in ("localhost", "127.0.0.1") and
                     u.port and not u.username and not u.password and u.path in ("", "/") and
                     not u.query and not u.fragment)
        except ValueError:
            valid = False
        if not valid:
            raise FlowError("接管地址必须为本机 http://127.0.0.1:端口")
        if result["profile"] or result["headless"]:
            raise FlowError("接管现有浏览器时不能设置登录目录或无头模式")
    if result["input_mode"] == "desktop" and result["headless"]:
        raise FlowError("系统输入需要可见浏览器窗口")
    return result


def inspect_environment(value):
    config = settings(value)
    errors = []
    versions = {}
    for name in [config["backend"]] + (["pywinauto"] if config["input_mode"] == "desktop" else []):
        try:
            versions[name] = version(name)
            if importlib.util.find_spec(name) is None:
                errors.append(f"无法导入本地组件 {name}")
        except (PackageNotFoundError, ValueError, ImportError):
            errors.append(f"缺少本地组件 {name}；请通过离线材料安装，不会自动下载")
    if not config["cdp_url"]:
        path = Path(config["executable_path"])
        if not config["executable_path"] or not path.is_absolute() or not path.is_file():
            errors.append("请选择已安装的本地 Chromium/Chrome/Edge 可执行文件")
    if config["input_mode"] == "desktop" and os.name != "nt":
        errors.append("系统输入仅支持 Windows")
    return {"settings": config, "ready": not errors, "errors": errors, "versions": versions,
            "note": "仅检查本地组件；浏览器兼容性及接管端口将在启动时验证，不执行下载"}


def require_environment(value, requirement=None):
    report = inspect_environment(value)
    if not report["ready"]:
        raise FlowError("；".join(report["errors"]))
    config = report["settings"]
    if requirement:
        if config["backend"] not in requirement["backends"]:
            raise FlowError("此流程不支持所选浏览器后端")
        if config["input_mode"] not in requirement["input_modes"]:
            raise FlowError("此流程不支持所选输入模式")
    return config


class FileLock:
    """Kernel lock; released even if the owning worker is forcefully killed."""
    def __init__(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.file = path.open("a+b")
        self.file.seek(0)
        self.file.write(b"0")
        self.file.flush()
        self.file.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.file.close()
            raise FlowError("浏览器登录目录或桌面输入正在被其他任务使用") from exc

    def close(self):
        self.file.close()

"""python -m awm: create, validate, pack and run flow packages."""
import argparse
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

from awm.packages import ROOT, FlowError, extract_package, pack, read_json, validate_directory, write_json
from awm.runtime import ACTIVE, Runtime


def main():
    parser = argparse.ArgumentParser(description="AutoMaticWorker flow author tools")
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="Create a working flow from the report template")
    init.add_argument("directory")
    init.add_argument("--id", required=True)
    init.add_argument("--template", choices=["report", "browser-form"], default="report")
    check = commands.add_parser("validate", help="Validate a folder or ZIP without executing it")
    check.add_argument("source")
    build = commands.add_parser("pack")
    build.add_argument("source")
    build.add_argument("output")
    run = commands.add_parser("run")
    run.add_argument("source")
    run.add_argument("--config", help="JSON configuration file (keep secrets out of shared files)")
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--data-dir", required=True, help="Local run records and outputs")
    run.add_argument("--interactive", action="store_true", help="Allow manual login/continue prompts")
    environment = commands.add_parser("environment", help="Inspect or configure local browser components; never download")
    environment.add_argument("--data-dir", required=True)
    environment.add_argument("--config", help="Local JSON browser settings")
    args = parser.parse_args()
    if args.command == "environment":
        runtime = Runtime(args.data_dir)
        try:
            report = runtime.save_environment(read_json(args.config)) if args.config else runtime.environment()
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0 if report["ready"] else 1
        finally:
            runtime.close()
    if args.command == "init":
        target = Path(args.directory)
        if target.exists():
            raise FlowError("目标目录已存在；初始化不会覆盖文件")
        template = ROOT / "examples" / args.template
        manifest = read_json(template / "manifest.json")
        manifest.update(id=args.id, name=args.id, author="Flow author")
        # Validate ID before creating an unfinished target directory.
        with tempfile.TemporaryDirectory() as temp:
            candidate = Path(temp) / "flow"
            shutil.copytree(template, candidate)
            write_json(candidate / "manifest.json", manifest)
            validate_directory(candidate)
            shutil.copytree(candidate, target)
        print(str(target.resolve()))
        return 0
    if args.command == "pack":
        print(pack(args.source, args.output))
        return 0
    source = Path(args.source).resolve()
    with tempfile.TemporaryDirectory() as temp:
        if source.is_dir():
            manifest = validate_directory(source)
            package = pack(source, Path(temp) / "flow.zip") if args.command == "run" else None
        else:
            manifest = extract_package(source, Path(temp) / "unpacked")
            package = source
        if args.command == "validate":
            print(json.dumps({"valid": True, "id": manifest["id"], "version": manifest["version"]}, ensure_ascii=False))
            return 0
        runtime = Runtime(args.data_dir)
        try:
            installed = next((p for p in runtime.library() if p["id"] == manifest["id"]), None)
            if installed:
                # CLI run is an author workspace: refresh source even at the same version.
                runtime.uninstall(manifest["id"])
            runtime.install(package)
            record = runtime.start(manifest["id"], read_json(args.config) if args.config else {}, args.dry_run)
            while record["status"] in ACTIVE or not record["finished_at"]:
                if record["status"] == "waiting":
                    if not args.interactive:
                        raise FlowError("流程等待人工操作；CLI 请添加 --interactive，或通过桌面运行")
                    input(record.get("wait_message", "请完成人工操作") + "\n完成后按 Enter 继续（Ctrl+C 取消）：")
                    runtime.resume(record["id"], record["wait_id"])
                    # Wait for the worker to consume this signal before another prompt.
                    while runtime.get_run(record["id"]).get("wait_id") == record["wait_id"]:
                        time.sleep(.1)
                time.sleep(0.1)
                record = runtime.get_run(record["id"])
            print(json.dumps(record, ensure_ascii=False, indent=2))
            print(f"Outputs: {runtime.runs_dir / record['id'] / 'output'}")
            return 0 if record["status"] == "succeeded" else 1
        finally:
            runtime.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    try:
        raise SystemExit(main())
    except (FlowError, OSError, json.JSONDecodeError) as exc:
        raise SystemExit(str(exc))

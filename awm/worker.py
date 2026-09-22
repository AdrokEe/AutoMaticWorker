"""One worker process per run. Secrets arrive over stdin, never on command lines."""
import importlib.util
import json
import sys
import traceback
from pathlib import Path

from awm.sdk import Cancelled, Context

PREFIX = "@AWM@"


def main():
    request = json.loads(sys.stdin.readline())
    sys.stdin.close()
    protocol = sys.stdout

    def emit(event):
        protocol.write(PREFIX + json.dumps(event, ensure_ascii=False) + "\n")
        protocol.flush()

    ctx = Context(request["id"], request["output"], request["cancel"], request["dry_run"], emit)
    try:
        package = Path(request["package"])
        sys.path.insert(0, str(package))
        spec = importlib.util.spec_from_file_location("awm_user_flow", package / "flow.py")
        module = importlib.util.module_from_spec(spec)
        ctx.check_cancelled()
        spec.loader.exec_module(module)
        value = module.run(ctx, request["config"])
        ctx.check_cancelled()
        if not isinstance(value, dict) or set(value) != {"summary", "files"}:
            raise ValueError("run must return ctx.result(summary, files)")
        if not isinstance(value["summary"], str) or not isinstance(value["files"], list):
            raise ValueError("Invalid result types")
        checked = ctx.result(value["summary"], value["files"])
        emit({"type": "result", **checked})
        return 0
    except Cancelled:
        emit({"type": "cancelled"})
        return 2
    except BaseException as exc:
        emit({"type": "log", "level": "error", "message": traceback.format_exc()})
        emit({"type": "failure", "message": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

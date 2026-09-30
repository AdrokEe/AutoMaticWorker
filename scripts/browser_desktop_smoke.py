"""Opt-in visible Windows browser test. Temporarily uses the system mouse."""
import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from awm.packages import pack, read_json
from awm.runtime import Runtime


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="awm-desktop-test-") as temp:
        runtime = Runtime(Path(temp) / "data")
        try:
            report = runtime.save_environment({"executable_path": args.browser, "input_mode": "desktop", "interaction": "natural"})
            assert report["ready"], report
            runtime.install(pack(ROOT / "examples/browser-form", Path(temp) / "example.zip"))
            record = runtime.start("sample-browser-form", {"name": "测试 Name", "note": "literal +^%{}()"})
            runtime.thread.join(60)
            result = runtime.get_run(record["id"])
            assert result["status"] == "succeeded", result
            receipt = read_json(runtime.artifact(record["id"], "receipt.json"))
            assert receipt["note"] == "literal +^%{}()"
            assert receipt["submissions"] == 1
            evidence = {"passed": True, "receipt": receipt, "versions": report["versions"],
                        "scope": "Current desktop scale only; other DPI and RDP states are not certified."}
            output = ROOT / "output/browser-desktop-smoke.json"
            output.parent.mkdir(exist_ok=True)
            output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps(evidence, ensure_ascii=False))
        finally:
            runtime.close()


if __name__ == "__main__":
    main()

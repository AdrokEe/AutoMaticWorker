"""Run real WebView2 hidden; verify UI load, task cancellation, and service shutdown."""
import json
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, build_opener, ProxyHandler

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import webview
import main as desktop
from awm.packages import pack
from awm.runtime import Runtime


def main():
    original_create = webview.create_window
    original_start = webview.start
    loaded = threading.Event()
    evidence = {}
    errors = []
    window = None

    def create(*args, **kwargs):
        nonlocal window
        kwargs["hidden"] = True
        window = original_create(*args, **kwargs)
        window.events.loaded += loaded.set
        evidence["url"] = args[1]
        return window

    client = build_opener(ProxyHandler({}))

    def check():
        try:
            assert loaded.wait(25), "Desktop page failed to load"
            deadline = time.monotonic() + 15
            text = ""
            while time.monotonic() < deadline:
                text = window.evaluate_js("document.body.innerText") or ""
                if "合成数据报告" in text:
                    break
                time.sleep(0.2)
            assert "合成数据报告" in text and "流程工作台" in text, text
            evidence["desktop_ui_loaded"] = True
            base = evidence["url"]
            with client.open(base + "/api/bootstrap", timeout=5) as response:
                token = json.load(response)["token"]
            request = Request(base + "/api/runs", data=json.dumps({"flow_id": "sample-report", "config": {"rows": 100, "delay": 0.2}}).encode(), headers={"Content-Type": "application/json", "X-AWM-Token": token})
            with client.open(request, timeout=5) as response:
                evidence["run_id"] = json.load(response)["id"]
        except BaseException as exc:
            errors.append(str(exc))
        finally:
            window.destroy()

    def start(*args, **kwargs):
        original_start(check, gui="edgechromium")

    with tempfile.TemporaryDirectory() as temp:
        data = Path(temp) / "data"
        runtime = Runtime(data)
        runtime.install(pack(ROOT / "examples/report", Path(temp) / "report.zip"))
        runtime.close()
        webview.create_window = create
        webview.start = start
        sys.argv = ["main.py", "--data-dir", str(data)]
        desktop.main()
        if errors:
            raise AssertionError(errors)
        record = json.loads((data / "runs" / evidence["run_id"] / "record.json").read_text(encoding="utf-8"))
        assert record["status"] == "cancelled", record
        evidence["close_cancelled_task"] = True
        port = urlparse(evidence["url"]).port
        with socket.socket() as probe:
            probe.settimeout(1)
            assert probe.connect_ex(("127.0.0.1", port)) != 0
        evidence["close_stopped_server"] = True
        # Lock must be released after application close.
        runtime = Runtime(data)
        runtime.close()
        evidence["data_lock_released"] = True
    output = ROOT / "output/desktop-smoke.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False))


if __name__ == "__main__":
    main()

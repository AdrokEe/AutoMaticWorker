"""Managed loopback service and desktop window."""
import argparse
import threading

from werkzeug.serving import make_server

from awm.packages import FlowError
from awm.runtime import Runtime
from awm.server import create_app


def main():
    parser = argparse.ArgumentParser(description="AutoMaticWorker desktop")
    parser.add_argument("--browser", action="store_true", help="Serve UI without desktop window")
    parser.add_argument("--port", type=int, default=0, help="0 chooses a free loopback port")
    parser.add_argument("--data-dir", help="Isolated application data directory")
    args = parser.parse_args()
    runtime = Runtime(args.data_dir)
    server = None
    thread = None
    try:
        app = create_app(runtime)
        server = make_server("127.0.0.1", args.port, app, threaded=True)
        url = f"http://127.0.0.1:{server.server_port}"
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        print(f"AutoMaticWorker: {url}", flush=True)
        if args.browser:
            while thread.is_alive():
                thread.join(timeout=0.5)
        else:
            try:
                import webview
            except ImportError as exc:
                raise FlowError("桌面模式需要 pywebview；请安装 requirements-desktop.txt，或使用 --browser") from exc
            webview.settings["ALLOW_DOWNLOADS"] = True
            window = webview.create_window("AutoMaticWorker", url, width=1280, height=860, min_size=(900, 640))

            def pick_directory():
                result = window.create_file_dialog(webview.FileDialog.FOLDER)
                return result[0] if result else None

            app.config["DIRECTORY_PICKER"] = pick_directory
            webview.start()
    except KeyboardInterrupt:
        pass
    finally:
        runtime.close()
        if server:
            server.shutdown()
            server.server_close()
        if thread:
            thread.join(timeout=3)


if __name__ == "__main__":
    try:
        main()
    except FlowError as error:
        raise SystemExit(str(error))

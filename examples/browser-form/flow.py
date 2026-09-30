"""Synthetic local website. No real accounts, business endpoints or CDN assets."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def run(ctx, config):
    submitted = []
    html = Path(__file__).with_name("site.html").read_bytes()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_GET(self):
            self.send_response(200 if self.path == "/" else 404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            if self.path == "/":
                self.wfile.write(html)

        def do_POST(self):
            if self.path != "/submit" or submitted:
                self.send_error(409)
                return
            size = int(self.headers.get("Content-Length", 0))
            if not 0 < size < 65536:
                self.send_error(400)
                return
            value = json.loads(self.rfile.read(size))
            submitted.append({"id": "LOCAL-001", **value})
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(submitted[0], ensure_ascii=False).encode())

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with ctx.browser() as browser:
            page, actions = browser.page, browser.actions()
            base = f"http://127.0.0.1:{server.server_port}"
            # This demonstration permits only its own loopback page requests.
            # Browser/OS background traffic is outside this route handler's scope.
            browser.context.route("**/*", lambda route: route.continue_()
                                  if route.request.url.startswith(base + "/") else route.abort())
            with ctx.step("打开本地演示站并登录"):
                if config.get("manual_login") and browser.config["headless"]:
                    raise ValueError("人工登录需要关闭无头模式")
                page.goto(base + "/")
                if config.get("manual_login"):
                    ctx.wait_for_user("请在演示浏览器点击‘登录演示系统’，然后返回这里点击继续。", timeout=300)
                else:
                    actions.click(page.get_by_role("button", name="登录演示系统"))
                actions.wait_visible(page.get_by_role("button", name="查询演示记录"))
            ctx.progress(1, 3, "登录已确认")
            with ctx.step("查询与填表"):
                actions.click(page.get_by_role("button", name="查询演示记录"))
                actions.type_text(page.get_by_label("姓名"), config["name"])
                actions.type_text(page.get_by_label("备注"), config.get("note", ""))
            ctx.progress(2, 3, "字段已校验")
            with ctx.step("预览或提交并确认回执"):
                if ctx.dry_run:
                    result = {"mode": "preview", "name": config["name"], "note": config.get("note", ""), "submissions": 0}
                else:
                    actions.click(page.get_by_role("button", name="提交记录"),
                                  after=lambda: page.locator("#receipt").inner_text() == "已保存：LOCAL-001")
                    result = {"mode": "normal", **json.loads(page.locator("#receipt").get_attribute("data-value")), "submissions": len(submitted)}
                    if result["name"] != config["name"] or result["submissions"] != 1:
                        raise ValueError("回执校验失败")
                result["events"] = json.loads(page.locator("html").get_attribute("data-events"))
                ctx.output_path("receipt.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            ctx.progress(3, 3, "本地回执已生成")
        return ctx.result("预览完成，未提交" if ctx.dry_run else "已完成一次本地提交并确认回执", ["receipt.json"])
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

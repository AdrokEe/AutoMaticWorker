import html
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode
from urllib.request import Request, build_opener, ProxyHandler
from html.parser import HTMLParser


class ReceiptParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.capture = False
        self.receipt = ""

    def handle_starttag(self, tag, attrs):
        self.capture = tag == "p" and dict(attrs).get("id") == "receipt"

    def handle_data(self, data):
        if self.capture:
            self.receipt += data

    def handle_endtag(self, tag):
        self.capture = False


def run(ctx, config):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            self.respond('<form method="post"><input name="name"><button>提交</button></form>')

        def do_POST(self):
            form = parse_qs(self.rfile.read(int(self.headers["Content-Length"])).decode())
            self.respond(f'<p id="receipt">已接收：{html.escape(form["name"][0])}</p>')

        def respond(self, text):
            data = text.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/"
        client = build_opener(ProxyHandler({}))
        with client.open(url, timeout=5) as response:
            if '<form method="post">' not in response.read().decode():
                raise ValueError("模拟网页没有表单")
        ctx.progress(1, 3, "已读取本地模拟表单")
        data = urlencode({"name": config["name"]}).encode()
        with client.open(Request(url, data=data), timeout=5) as response:
            page = response.read().decode("utf-8")
        ctx.progress(2, 3, "已提交演示表单")
        parser = ReceiptParser()
        parser.feed(page)
        if parser.receipt != f"已接收：{config['name']}":
            raise ValueError("回执内容与输入不符")
        ctx.output_path("receipt.json").write_text(json.dumps({"receipt": parser.receipt, "simulation": ctx.dry_run}, ensure_ascii=False), encoding="utf-8")
        ctx.progress(3, 3, "回执验证通过")
        return ctx.result(parser.receipt, ["receipt.json"])
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

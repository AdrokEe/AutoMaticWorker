"""Loopback API and built frontend."""
import secrets
import tempfile
import uuid
from pathlib import Path

from flask import Flask, jsonify, request, send_file, send_from_directory
from werkzeug.exceptions import HTTPException
from werkzeug.utils import secure_filename

from awm import __version__
from awm.packages import FlowError, MAX_BYTES, ROOT, pack
from awm.runtime import Runtime


def create_app(runtime=None):
    runtime = runtime or Runtime()
    app = Flask(__name__, static_folder=None)
    app.config["MAX_CONTENT_LENGTH"] = MAX_BYTES + 1024 * 1024
    app.extensions["runtime"] = runtime
    token = secrets.token_urlsafe(32)

    @app.before_request
    def local_only():
        if request.host.split(":")[0] not in ("localhost", "127.0.0.1"):
            return jsonify(error="仅允许本地访问"), 403
        origin = request.headers.get("Origin")
        if origin and origin != request.host_url.rstrip("/"):
            return jsonify(error="拒绝跨来源请求"), 403
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            if not secrets.compare_digest(request.headers.get("X-AWM-Token", ""), token):
                return jsonify(error="会话已失效，请刷新页面"), 403

    @app.after_request
    def headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(FlowError)
    def flow_error(error):
        return jsonify(error=str(error)), 400

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(error="请求或上传文件无效" if error.code == 413 else error.description), error.code

    @app.errorhandler(Exception)
    def unexpected(error):
        app.logger.exception("API failure")
        return jsonify(error="操作失败，请检查本地服务日志"), 500

    def body():
        value = request.get_json()
        if not isinstance(value, dict):
            raise FlowError("请求必须是 JSON 对象")
        return value

    @app.get("/api/bootstrap")
    def bootstrap():
        return jsonify(version=__version__, token=token, data_dir=str(runtime.home))

    @app.get("/api/flows")
    def flows():
        return jsonify(runtime.library())

    @app.post("/api/examples")
    def examples():
        installed = {p["id"] for p in runtime.library()}
        with tempfile.TemporaryDirectory(dir=runtime.home) as temp:
            for name, flow_id in (("report", "sample-report"), ("local-web", "sample-local-web")):
                if flow_id not in installed:
                    archive = pack(ROOT / "examples" / name, Path(temp) / f"{name}.zip")
                    runtime.install(archive)
        return jsonify(ok=True)

    @app.post("/api/flows/import")
    def import_flow():
        upload = request.files.get("file")
        if not upload:
            raise FlowError("请选择 ZIP 流程包")
        with tempfile.TemporaryDirectory(dir=runtime.home) as temp:
            path = Path(temp) / "flow.zip"
            upload.save(path)
            manifest = runtime.install(path, replace=request.form.get("replace") == "true")
        return jsonify(manifest), 201

    @app.delete("/api/flows/<flow_id>")
    def remove_flow(flow_id):
        runtime.uninstall(flow_id)
        return jsonify(ok=True)

    @app.route("/api/flows/<flow_id>/config", methods=["GET", "PUT"])
    def config(flow_id):
        if request.method == "PUT":
            runtime.save_config(flow_id, body())
        return jsonify(runtime.config(flow_id))

    @app.post("/api/inputs")
    def upload_input():
        upload = request.files.get("file")
        if not upload:
            raise FlowError("请选择输入文件")
        name = secure_filename(upload.filename or "input") or "input"
        directory = runtime.home / "inputs" / uuid.uuid4().hex
        directory.mkdir()
        path = directory / name
        upload.save(path)
        return jsonify(path=str(path))

    @app.post("/api/pick-directory")
    def pick_directory():
        picker = app.config.get("DIRECTORY_PICKER")
        if not picker:
            raise FlowError("浏览器模式请填写本机目录路径；桌面模式支持选择目录")
        return jsonify(path=picker())

    @app.get("/api/runs")
    def runs():
        return jsonify(runtime.history())

    @app.post("/api/runs")
    def start():
        value = body()
        return jsonify(runtime.start(value.get("flow_id"), value.get("config", {}), value.get("dry_run", False))), 201

    @app.get("/api/runs/<run_id>")
    def get_run(run_id):
        return jsonify(runtime.get_run(run_id))

    @app.post("/api/runs/<run_id>/cancel")
    def cancel(run_id):
        return jsonify(runtime.cancel(run_id))

    @app.get("/api/runs/<run_id>/files/<path:filename>")
    def artifact(run_id, filename):
        return send_file(runtime.artifact(run_id, filename), as_attachment=True)

    @app.get("/")
    @app.get("/<path:filename>")
    def frontend(filename="index.html"):
        dist = ROOT / "vue_frontend/dist"
        if not (dist / "index.html").exists():
            return "前端尚未构建。请在 vue_frontend 运行 npm ci 和 npm run build。", 503
        return send_from_directory(dist, filename)

    return app

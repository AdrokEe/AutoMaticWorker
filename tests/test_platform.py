import io
import json
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

import pytest

from awm.packages import ROOT, FlowError, extract_package, pack, read_json, validate_config, validate_directory, write_json
from awm.runtime import Runtime
from awm.server import create_app


@pytest.fixture
def runtime(tmp_path):
    instance = Runtime(tmp_path / "data")
    yield instance
    instance.close()


def install(runtime, tmp_path, name="report", code=None, mutate=None):
    source = tmp_path / ("source-" + str(time.monotonic_ns()))
    shutil.copytree(ROOT / "examples" / name, source)
    if code:
        (source / "flow.py").write_text(code, encoding="utf-8")
    if mutate:
        value = read_json(source / "manifest.json")
        mutate(value)
        write_json(source / "manifest.json", value)
    archive = pack(source, tmp_path / (source.name + ".zip"))
    runtime.install(archive)
    return source, archive


def finish(runtime, record):
    runtime.thread.join(timeout=12)
    assert not runtime.thread.is_alive(), "Worker did not finish"
    result = runtime.get_run(record["id"])
    assert result["finished_at"]
    return result


@pytest.mark.parametrize("dry_run", [False, True])
def test_report_roundtrip_and_persistence(runtime, tmp_path, dry_run):
    install(runtime, tmp_path)
    record = finish(runtime, runtime.start("sample-report", {"rows": 3, "delay": 0}, dry_run))
    assert record["status"] == "succeeded"
    result = read_json(runtime.artifact(record["id"], "report.json"))
    assert result["total"] == 72
    assert result["mode"] == ("simulation" if dry_run else "normal")
    assert len(runtime.artifact(record["id"], "details.csv").read_text(encoding="utf-8-sig").splitlines()) == 4
    runtime.close()
    reopened = Runtime(runtime.home)
    try:
        assert reopened.get_run(record["id"])["files"] == ["report.json", "details.csv"]
    finally:
        reopened.close()


def test_local_web(runtime, tmp_path):
    install(runtime, tmp_path, "local-web")
    record = finish(runtime, runtime.start("sample-local-web", {"name": "中文<&>测试"}, True))
    assert record["status"] == "succeeded"
    assert read_json(runtime.artifact(record["id"], "receipt.json"))["receipt"] == "已接收：中文<&>测试"


@pytest.mark.parametrize("path", ["../escape.py", "/absolute.py", "C:/bad.py", "a\\b.py", "CON.txt", "folder/../bad.py"])
def test_zip_path_rejection(tmp_path, path):
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr(path, "bad")
    with pytest.raises(FlowError):
        extract_package(archive, tmp_path / "extract")
    assert not (tmp_path / "escape.py").exists()


def test_duplicate_archive_names(tmp_path):
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("FLOW.py", "")
        z.writestr("flow.py", "")
    with pytest.raises(FlowError, match="重复"):
        extract_package(archive, tmp_path / "extract")


def test_manifest_compatibility_and_no_import_execution(tmp_path):
    source = tmp_path / "source"
    shutil.copytree(ROOT / "examples/report", source)
    marker = tmp_path / "executed"
    (source / "flow.py").write_text(f"from pathlib import Path\nPath({str(marker)!r}).touch()\ndef run(ctx, config): pass\n")
    validate_directory(source)
    assert not marker.exists()
    manifest = read_json(source / "manifest.json")
    manifest["platform"] = ">=9.0.0"
    write_json(source / "manifest.json", manifest)
    with pytest.raises(FlowError, match="不兼容"):
        validate_directory(source)
    manifest["platform"] = ">=0.2.0"
    del manifest["name"]
    write_json(source / "manifest.json", manifest)
    with pytest.raises(FlowError, match="清单错误"):
        validate_directory(source)


@pytest.mark.parametrize("config", [{"rows": -1}, {"rows": True}, {"rows": float('nan')}, {"currency": "EUR"}, {"title": ""}, {"unknown": "x"}])
def test_config_rejections(config):
    manifest = validate_directory(ROOT / "examples/report")
    with pytest.raises(FlowError):
        validate_config(manifest, config)


def test_file_directory_and_secret_parameters(tmp_path):
    file = tmp_path / "input.csv"
    file.write_text("a,b\n1,2")
    manifest = {"parameters": [
        {"key": "file", "label": "文件", "type": "file", "required": True},
        {"key": "directory", "label": "目录", "type": "directory", "required": True}]}
    assert validate_config(manifest, {"file": str(file), "directory": str(tmp_path)})
    with pytest.raises(FlowError):
        validate_config(manifest, {"file": str(tmp_path), "directory": str(file)})


def test_cancel_single_task_and_close(runtime, tmp_path):
    install(runtime, tmp_path)
    record = runtime.start("sample-report", {"rows": 100, "delay": 0.1})
    with pytest.raises(FlowError, match="运行中"):
        runtime.start("sample-report", {})
    with pytest.raises(FlowError):
        runtime.uninstall("sample-report")
    runtime.cancel(record["id"])
    assert finish(runtime, record)["status"] == "cancelled"
    again = runtime.start("sample-report", {"rows": 100, "delay": 0.1})
    runtime.close()
    assert runtime.process.poll() is not None
    assert runtime.get_run(again["id"])["status"] == "cancelled"


def test_force_cancel_uncooperative_worker(runtime, tmp_path):
    install(runtime, tmp_path, code="import time\ndef run(ctx, config):\n    time.sleep(60)\n    return ctx.result('done')\n")
    record = runtime.start("sample-report", {})
    time.sleep(0.3)
    runtime.cancel(record["id"])
    assert finish(runtime, record)["status"] == "cancelled"
    assert runtime.process.poll() is not None


def test_descendant_inheriting_stdout_does_not_keep_task_alive(runtime, tmp_path):
    code = "import subprocess, sys\ndef run(ctx, config):\n    child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n    return ctx.result('child cleanup')\n"
    install(runtime, tmp_path, code=code)
    record = finish(runtime, runtime.start("sample-report", {}))
    assert record["status"] == "succeeded"
    assert runtime.process.awm_tree.closed


def test_failed_flow_and_result_escape(runtime, tmp_path):
    install(runtime, tmp_path, code="def run(ctx, config):\n    raise ValueError('sample failure')\n")
    record = finish(runtime, runtime.start("sample-report", {}))
    assert record["status"] == "failed"
    assert "sample failure" in record["error"]
    with pytest.raises(FlowError):
        runtime.artifact(record["id"], "../../record.json")


def test_secret_never_in_records_or_saved_config(runtime, tmp_path):
    secret = 'test-secret-中文-"quoted"'
    def mutate(m):
        m["parameters"].append({"key": "token", "label": "测试凭据", "type": "text", "secret": True, "required": True})
    code = "def run(ctx, config):\n    ctx.log(config['token'])\n    print(config['token'])\n    raise ValueError(config['token'])\n"
    install(runtime, tmp_path, code=code, mutate=mutate)
    runtime.save_config("sample-report", {"title": "无需凭据即可保存"})
    assert runtime.config("sample-report")["title"] == "无需凭据即可保存"
    runtime.save_config("sample-report", {"token": secret})
    assert "token" not in runtime.config("sample-report")
    record = finish(runtime, runtime.start("sample-report", {"token": secret}))
    assert "token" not in record["config"]
    assert secret not in json.dumps(record, ensure_ascii=False)
    persisted = (runtime.runs_dir / record["id"] / "record.json").read_text(encoding="utf-8")
    assert secret not in persisted
    assert "已隐藏" in persisted


def test_upgrade_and_uninstall_preserve_results(runtime, tmp_path):
    source, archive = install(runtime, tmp_path)
    record = finish(runtime, runtime.start("sample-report", {"delay": 0}))
    with pytest.raises(FlowError):
        runtime.install(archive)
    with pytest.raises(FlowError):
        runtime.install(archive, replace=True)
    manifest = read_json(source / "manifest.json")
    manifest["version"] = "1.1.0"
    write_json(source / "manifest.json", manifest)
    runtime.save_config("sample-report", {"title": "saved"})
    runtime.install(pack(source, tmp_path / "upgrade.zip"), replace=True)
    assert runtime.library()[0]["version"] == "1.1.0"
    assert runtime.config("sample-report") == {}
    runtime.uninstall("sample-report")
    assert runtime.library() == []
    assert runtime.artifact(record["id"], "report.json").exists()


def test_runtime_single_instance_and_interrupted_recovery(runtime):
    with pytest.raises(FlowError):
        Runtime(runtime.home)
    record = {"id": "a" * 32, "status": "running", "started_at": "now"}
    write_json(runtime.runs_dir / record["id"] / "record.json", record)
    runtime.close()
    reopened = Runtime(runtime.home)
    try:
        assert reopened.get_run(record["id"])["status"] == "failed"
    finally:
        reopened.close()


def test_api_import_run_download_origin_and_tokens(runtime, tmp_path):
    app = create_app(runtime)
    client = app.test_client()
    token = client.get("/api/bootstrap").json["token"]
    headers = {"X-AWM-Token": token}
    assert client.post("/api/examples", json={}).status_code == 403
    assert client.post("/api/examples", json={}, headers={**headers, "Origin": "https://example.com"}).status_code == 403
    assert client.get("/api/bootstrap", headers={"Host": "evil.example"}).status_code == 403
    archive = pack(ROOT / "examples/report", tmp_path / "report.zip")
    response = client.post("/api/flows/import", data={"file": (io.BytesIO(archive.read_bytes()), "report.zip")}, headers=headers)
    assert response.status_code == 201
    response = client.post("/api/runs", json={"flow_id": "sample-report", "config": {"rows": 2, "delay": 0}}, headers=headers)
    assert response.status_code == 201
    record = finish(runtime, response.json)
    response = client.get(f"/api/runs/{record['id']}/files/report.json")
    assert response.status_code == 200
    assert json.loads(response.data)["total"] == 36
    assert "attachment" in response.headers["Content-Disposition"]
    response.close()
    assert client.get("/api/runs").json[0]["status"] == "succeeded"
    assert client.post("/api/runs", json=[], headers=headers).status_code == 400


def test_cli_init_validate_run(tmp_path):
    source = tmp_path / "my-flow"
    def cli(*args):
        return subprocess.run([sys.executable, "-m", "awm", *map(str, args)], cwd=ROOT, capture_output=True, encoding="utf-8", errors="replace", timeout=20)
    assert cli("init", source, "--id", "my-flow").returncode == 0
    assert cli("validate", source).returncode == 0
    result = cli("run", source, "--dry-run", "--data-dir", tmp_path / "author-runs")
    assert result.returncode == 0, result.stderr
    assert '"status": "succeeded"' in result.stdout

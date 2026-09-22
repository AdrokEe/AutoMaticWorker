"""Persistent local flow library and single-task process supervisor."""
import copy
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from packaging.version import Version

from awm.packages import (ROOT, FlowError, extract_package, public_config, read_json,
                          validate_config, validate_directory, write_json)
from awm.worker import PREFIX
from awm.processes import ProcessTree

ACTIVE = {"running", "cancelling"}


def now():
    return datetime.now(timezone.utc).isoformat()


def default_data_dir():
    return Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local/share")) / "AutoMaticWorker"


class Runtime:
    def __init__(self, data_dir=None):
        self.home = Path(data_dir or default_data_dir()).resolve()
        self.packages = self.home / "packages"
        self.runs_dir = self.home / "runs"
        self.configs = self.home / "configs"
        for path in (self.packages, self.runs_dir, self.configs, self.home / "inputs"):
            path.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self._lock_file = (self.home / "instance.lock").open("a+b")
        self._lock_file.seek(0)
        self._lock_file.write(b"0")
        self._lock_file.flush()
        self._lock_file.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self._lock_file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self._lock_file.close()
            raise FlowError("该数据目录已由另一个 AutoMaticWorker 实例使用") from exc
        self.process = None
        self.thread = None
        self.current = None
        self.closed = False
        for path in self.runs_dir.glob("*/record.json"):
            record = read_json(path)
            if record["status"] in ACTIVE:
                record.update(status="failed", error="应用意外退出，运行已中断；未自动重试", finished_at=now())
                write_json(path, record)

    def library(self):
        with self.lock:
            return sorted([validate_directory(p) for p in self.packages.iterdir() if p.is_dir()], key=lambda p: p["name"])

    def package(self, flow_id):
        if not isinstance(flow_id, str) or not flow_id or Path(flow_id).name != flow_id or flow_id in (".", ".."):
            raise FlowError("流程 ID 无效")
        path = (self.packages / flow_id).resolve()
        if path.parent != self.packages or not path.is_dir():
            raise FlowError("找不到流程包")
        return path, validate_directory(path)

    def _idle(self):
        if self.closed:
            raise FlowError("应用正在退出")
        if self.current and (self.current["status"] in ACTIVE or self.thread and self.thread.is_alive()):
            raise FlowError("已有任务运行中，请等待完成或取消")

    def install(self, archive, replace=False):
        with self.lock:
            self._idle()
            with tempfile.TemporaryDirectory(dir=self.home, prefix="import-") as temp:
                manifest = extract_package(archive, temp)
                target = self.packages / manifest["id"]
                if target.exists():
                    if not replace:
                        raise FlowError("已安装同 ID 流程包；请选择更新已有流程")
                    previous = validate_directory(target)
                    if Version(manifest["version"]) <= Version(previous["version"]):
                        raise FlowError("更新包的版本必须高于已安装版本")
                    backup = self.home / ("backup-" + uuid.uuid4().hex)
                    target.rename(backup)
                    try:
                        shutil.copytree(temp, target)
                    except BaseException:
                        if target.exists():
                            shutil.rmtree(target)
                        backup.rename(target)
                        raise
                    shutil.rmtree(backup)
                    (self.configs / f"{manifest['id']}.json").unlink(missing_ok=True)
                else:
                    shutil.copytree(temp, target)
                return manifest

    def uninstall(self, flow_id):
        with self.lock:
            self._idle()
            path, _ = self.package(flow_id)
            shutil.rmtree(path)
            (self.configs / f"{flow_id}.json").unlink(missing_ok=True)

    def config(self, flow_id):
        with self.lock:
            _, manifest = self.package(flow_id)
            path = self.configs / f"{flow_id}.json"
            return public_config(manifest, read_json(path)) if path.exists() else {}

    def save_config(self, flow_id, values):
        with self.lock:
            _, manifest = self.package(flow_id)
            # Saving ordinary preferences must not require a runtime credential.
            draft = {**manifest, "parameters": [
                {**p, "required": False} if p.get("secret") else p for p in manifest["parameters"]]}
            config = validate_config(draft, values)
            write_json(self.configs / f"{flow_id}.json", public_config(manifest, config))

    def start(self, flow_id, values, dry_run=False):
        with self.lock:
            self._idle()
            path, manifest = self.package(flow_id)
            config = validate_config(manifest, values)
            if type(dry_run) is not bool:
                raise FlowError("dry_run 必须是布尔值")
            if dry_run and manifest["dry_run"] == "unsupported":
                raise FlowError("此流程不支持试运行")
            run_id = uuid.uuid4().hex
            run_dir = self.runs_dir / run_id
            (run_dir / "output").mkdir(parents=True)
            record = {"id": run_id, "flow_id": flow_id, "name": manifest["name"],
                      "version": manifest["version"], "dry_run": dry_run, "status": "running",
                      "started_at": now(), "finished_at": None, "progress": 0,
                      "config": public_config(manifest, config), "logs": [], "files": [],
                      "summary": "", "error": ""}
            self.current = record
            self._persist()
            secrets = [str(config[p["key"]]) for p in manifest["parameters"]
                       if p.get("secret") and p["key"] in config and config[p["key"]]]
            payload = {"id": run_id, "package": str(path), "config": config, "dry_run": dry_run,
                       "output": str(run_dir / "output"), "cancel": str(run_dir / "cancel")}
            env = os.environ.copy()
            env.update(PYTHONPATH=str(ROOT), PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
            kwargs = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}
            try:
                self.process = subprocess.Popen([sys.executable, "-u", "-m", "awm.worker"],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace", cwd=run_dir, env=env, **kwargs)
                self.process.awm_tree = ProcessTree(self.process)
                self.thread = threading.Thread(target=self._collect, args=(self.process, payload, secrets), daemon=True)
                self.thread.start()
            except OSError as exc:
                if self.process and self.process.poll() is None:
                    self._kill(self.process)
                record.update(status="failed", error="无法启动任务进程", finished_at=now())
                self._persist()
                raise FlowError("无法启动任务进程") from exc
            return copy.deepcopy(record)

    def _persist(self):
        write_json(self.runs_dir / self.current["id"] / "record.json", self.current)

    def _collect(self, process, payload, secrets):
        result = None
        failure = ""

        def redact(text):
            for secret in sorted(secrets, key=len, reverse=True):
                text = text.replace(secret, "[已隐藏]")
            return text

        try:
            process.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
            process.stdin.close()
            for line in iter(lambda: process.stdout.readline(16384), ""):
                event = None
                if line.startswith(PREFIX):
                    try:
                        event = json.loads(line[len(PREFIX):])
                    except (ValueError, TypeError):
                        pass
                if not isinstance(event, dict):
                    event = {"type": "log", "level": "info", "message": line.rstrip()}
                event = self._redact_object(event, redact)
                with self.lock:
                    kind = event.get("type")
                    if kind == "result":
                        result = event
                    elif kind == "failure":
                        failure = str(event.get("message", "任务失败"))
                    elif kind == "progress":
                        percent = event.get("percent", 0)
                        if type(percent) in (int, float) and 0 <= percent <= 100:
                            self.current["progress"] = percent
                        self._log("info", event.get("message", ""))
                    elif kind == "log":
                        self._log(event.get("level", "info"), event.get("message", ""))
                    self._persist()
            code = process.wait()
            with self.lock:
                if self.current["status"] == "cancelling":
                    self.current.update(status="cancelled", summary="运行已取消")
                elif code == 0 and result:
                    files = result.get("files")
                    if not isinstance(files, list) or any(not isinstance(f, str) for f in files):
                        raise FlowError("流程返回的文件列表无效")
                    for filename in files:
                        self.artifact(self.current["id"], filename, require_listed=False)
                    self.current.update(status="succeeded", progress=100,
                                        summary=str(result.get("summary", "")), files=files)
                else:
                    self.current.update(status="failed", error=failure or f"任务进程退出（代码 {code}），未返回有效结果")
        except BaseException as exc:
            with self.lock:
                self.current.update(status="cancelled" if self.current["status"] == "cancelling" else "failed",
                                    error=redact(str(exc)))
        finally:
            if process.poll() is None:
                self._kill(process)
            process.stdout.close()
            with self.lock:
                self.current["finished_at"] = now()
                self._persist()

    @staticmethod
    def _redact_object(value, redact):
        if isinstance(value, str):
            return redact(value)
        if isinstance(value, list):
            return [Runtime._redact_object(v, redact) for v in value]
        if isinstance(value, dict):
            return {k: Runtime._redact_object(v, redact) for k, v in value.items()}
        return value

    def _log(self, level, message):
        if message:
            self.current["logs"].append({"at": now(), "level": level, "message": str(message)[:8000]})
            self.current["logs"] = self.current["logs"][-500:]

    def get_run(self, run_id):
        if not isinstance(run_id, str) or len(run_id) != 32 or any(c not in "0123456789abcdef" for c in run_id):
            raise FlowError("运行 ID 无效")
        with self.lock:
            if self.current and self.current["id"] == run_id:
                return copy.deepcopy(self.current)
            path = self.runs_dir / run_id / "record.json"
            if not path.exists():
                raise FlowError("找不到运行记录")
            return read_json(path)

    def history(self):
        with self.lock:
            records = [read_json(p) for p in self.runs_dir.glob("*/record.json")]
            return sorted([{k: v for k, v in r.items() if k != "logs"} for r in records],
                          key=lambda r: r["started_at"], reverse=True)

    def artifact(self, run_id, filename, require_listed=True):
        record = self.get_run(run_id)
        if require_listed and filename not in record["files"]:
            raise FlowError("文件不在本次运行结果中")
        base = (self.runs_dir / run_id / "output").resolve()
        target = (base / filename).resolve()
        if not target.is_relative_to(base) or not target.is_file():
            raise FlowError("输出文件不存在或越界")
        return target

    def cancel(self, run_id):
        with self.lock:
            record = self.get_run(run_id)
            if record["status"] not in ACTIVE:
                return record
            self.current["status"] = "cancelling"
            (self.runs_dir / run_id / "cancel").touch()
            self._persist()
            threading.Thread(target=self._cancel_after_grace, args=(self.process,), daemon=True).start()
            return copy.deepcopy(self.current)

    def _cancel_after_grace(self, process):
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self._kill(process)

    @staticmethod
    def _kill(process):
        tree = getattr(process, "awm_tree", None)
        if tree:
            tree.close()
        if process.poll() is not None:
            return
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                           capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()

    def close(self):
        with self.lock:
            if self.closed:
                return
            self.closed = True
            if self.current and self.current["status"] in ACTIVE:
                self.cancel(self.current["id"])
            thread = self.thread
        if thread:
            thread.join(timeout=8)
        self._lock_file.close()

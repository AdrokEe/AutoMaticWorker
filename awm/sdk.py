"""Public, intentionally small API for flow authors."""
import json
import time
import uuid
from contextlib import contextmanager
from pathlib import Path


class Cancelled(Exception):
    pass


class Context:
    def __init__(self, run_id, output_dir, cancel_file, dry_run, emit, *, browser_settings=None, home=None):
        self.run_id = run_id
        self.output_dir = Path(output_dir)
        self.dry_run = dry_run
        self._cancel_file = Path(cancel_file)
        self._emit = emit
        self._browser_settings = browser_settings
        self._home = Path(home) if home else self.output_dir.parent
        self._resources = []

    def sleep(self, seconds):
        if not isinstance(seconds, (int, float)) or not 0 <= seconds <= 86400:
            raise ValueError("等待时间必须在 0–86400 秒之间")
        end = time.monotonic() + seconds
        while True:
            self.check_cancelled()
            remaining = end - time.monotonic()
            if remaining <= 0:
                return
            time.sleep(min(remaining, 0.05))

    def wait_for_user(self, message, timeout=300):
        if not isinstance(timeout, (int, float)) or not 0 < timeout <= 86400:
            raise ValueError("人工等待超时必须在 0–86400 秒之间")
        self.check_cancelled()
        wait_id = uuid.uuid4().hex
        signal = self._cancel_file.parent / ("resume-" + wait_id)
        self._emit({"type": "waiting", "wait_id": wait_id, "message": str(message)})
        deadline = time.monotonic() + timeout
        try:
            while not signal.exists():
                if time.monotonic() >= deadline:
                    raise TimeoutError("等待人工操作超时")
                self.sleep(0.1)
            self.check_cancelled()
        finally:
            signal.unlink(missing_ok=True)
        self._emit({"type": "resumed", "wait_id": wait_id})

    @contextmanager
    def step(self, name):
        self.log(f"开始步骤：{name}")
        started = time.monotonic()
        yield
        self.log(f"步骤完成：{name}（{time.monotonic() - started:.2f}s）")

    def browser(self):
        if self._browser_settings is None:
            raise ValueError("流程未声明 browser 运行需求")
        from awm.browser import BrowserSession
        session = BrowserSession(self, self._browser_settings)
        self._resources.append(session)
        return session

    def close(self):
        errors = []
        for resource in reversed(self._resources):
            try:
                resource.close()
            except Exception as exc:
                errors.append(exc)
        self._resources.clear()
        if errors:
            raise errors[0]

    def check_cancelled(self):
        if self._cancel_file.exists():
            raise Cancelled("运行已取消")

    def log(self, message, level="info"):
        self.check_cancelled()
        if level not in ("info", "warning", "error"):
            raise ValueError("Unsupported log level")
        self._emit({"type": "log", "level": level, "message": str(message)})

    def progress(self, current, total, message=""):
        self.check_cancelled()
        if total <= 0 or not 0 <= current <= total:
            raise ValueError("Progress requires 0 <= current <= total and total > 0")
        self._emit({"type": "progress", "percent": round(current / total * 100), "message": str(message)})

    def output_path(self, name):
        path = (self.output_dir / name).resolve()
        if not path.is_relative_to(self.output_dir.resolve()) or path == self.output_dir.resolve():
            raise ValueError("Output must stay inside output_dir")
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def result(self, summary, files=()):
        normalized = []
        for name in files:
            path = self.output_path(name)
            if not path.is_file():
                raise ValueError(f"Output file does not exist: {name}")
            normalized.append(path.relative_to(self.output_dir.resolve()).as_posix())
        return {"summary": str(summary), "files": normalized}

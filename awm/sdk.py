"""Public, intentionally small API for flow authors."""
import json
from pathlib import Path


class Cancelled(Exception):
    pass


class Context:
    def __init__(self, run_id, output_dir, cancel_file, dry_run, emit):
        self.run_id = run_id
        self.output_dir = Path(output_dir)
        self.dry_run = dry_run
        self._cancel_file = Path(cancel_file)
        self._emit = emit

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

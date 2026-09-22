"""Own the complete task process tree, including descendants retaining stdout."""
import os
import signal
import threading


class ProcessTree:
    def __init__(self, process):
        self.process = process
        self.lock = threading.Lock()
        self.handle = None
        self.closed = False
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes

            class BasicLimits(ctypes.Structure):
                _fields_ = [("process_time", ctypes.c_longlong), ("job_time", ctypes.c_longlong),
                            ("flags", wintypes.DWORD), ("min_working_set", ctypes.c_size_t),
                            ("max_working_set", ctypes.c_size_t), ("process_count", wintypes.DWORD),
                            ("affinity", ctypes.c_size_t), ("priority", wintypes.DWORD),
                            ("scheduling", wintypes.DWORD)]

            class IoCounters(ctypes.Structure):
                _fields_ = [(name, ctypes.c_ulonglong) for name in
                            ("read_ops", "write_ops", "other_ops", "read_bytes", "write_bytes", "other_bytes")]

            class ExtendedLimits(ctypes.Structure):
                _fields_ = [("basic", BasicLimits), ("io", IoCounters),
                            ("process_memory", ctypes.c_size_t), ("job_memory", ctypes.c_size_t),
                            ("peak_process_memory", ctypes.c_size_t), ("peak_job_memory", ctypes.c_size_t)]

            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
            kernel.CreateJobObjectW.restype = wintypes.HANDLE
            kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
            kernel.SetInformationJobObject.restype = wintypes.BOOL
            kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
            kernel.AssignProcessToJobObject.restype = wintypes.BOOL
            kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel.CloseHandle.restype = wintypes.BOOL
            self.kernel = kernel
            self.handle = kernel.CreateJobObjectW(None, None)
            if not self.handle:
                raise ctypes.WinError(ctypes.get_last_error())
            limits = ExtendedLimits()
            limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            if not kernel.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)) or not kernel.AssignProcessToJobObject(self.handle, int(process._handle)):
                error = ctypes.get_last_error()
                kernel.CloseHandle(self.handle)
                self.handle = None
                raise ctypes.WinError(error)
        # Parent may return while a child retains the stdout pipe. Close the tree
        # as soon as the entry process exits, so the collector can see EOF.
        threading.Thread(target=self._watch, daemon=True).start()

    def _watch(self):
        self.process.wait()
        self.close()

    def close(self):
        with self.lock:
            if self.closed:
                return
            self.closed = True
            if os.name == "nt":
                self.kernel.CloseHandle(self.handle)
                self.handle = None
            else:
                try:
                    os.killpg(self.process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

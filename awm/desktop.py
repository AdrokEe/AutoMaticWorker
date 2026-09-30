"""Opt-in Windows input. UI Automation supplies physical viewport coordinates."""
import ctypes
import os
import time
import uuid
from ctypes import wintypes


class DesktopInput:
    def __init__(self, page, ctx):
        if os.name != "nt":
            raise RuntimeError("系统输入仅支持 Windows")
        from pywinauto import Desktop
        self.Desktop, self.page, self.ctx = Desktop, page, ctx
        self.user = ctypes.WinDLL("user32", use_last_error=True)
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        self.kernel.CreateMutexW.restype = wintypes.HANDLE
        self.kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        self.kernel.ReleaseMutex.argtypes = [wintypes.HANDLE]
        self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self.user.GetForegroundWindow.restype = wintypes.HWND
        self.user.IsIconic.argtypes = [wintypes.HWND]
        self.user.SetThreadDpiAwarenessContext.argtypes = [ctypes.c_void_p]
        self.user.SetThreadDpiAwarenessContext.restype = ctypes.c_void_p
        self.dpi = self.user.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4))
        self.mutex = self.kernel.CreateMutexW(None, False, "Local\\AutoMaticWorker.DesktopInput")
        if not self.mutex:
            raise RuntimeError("无法获取桌面输入锁")
        status = self.kernel.WaitForSingleObject(self.mutex, 0)
        if status not in (0, 0x80):
            self.kernel.CloseHandle(self.mutex)
            self.mutex = None
            if self.dpi:
                self.user.SetThreadDpiAwarenessContext(self.dpi)
            raise RuntimeError("桌面正被另一项自动化任务使用")
        self.window = self.document = self.rect = None
        self.last_position = None
        self.button_down = False
        self.ctrl_down = False

    def prepare(self):
        self.ctx.check_cancelled()
        self.page.bring_to_front()
        marker = "AWM-" + uuid.uuid4().hex
        old_title = self.page.title()
        self.page.evaluate("title => document.title = title", marker)
        try:
            deadline = time.monotonic() + 2
            windows = []
            while time.monotonic() < deadline:
                windows = self.Desktop(backend="uia").windows(title_re=f".*{marker}.*", visible_only=True)
                if windows:
                    break
                self.ctx.sleep(.05)
            if len(windows) != 1:
                raise RuntimeError("无法唯一识别浏览器窗口；系统模式已停止")
            self.window = windows[0]
            self.window.set_focus()
            documents = [d for d in self.window.descendants(control_type="Document")
                         if d.is_visible() and d.rectangle().width() > 0]
            if not documents:
                raise RuntimeError("浏览器未提供可见 UIA 页面区域；请使用浏览器输入模式")
            self.document = max(documents, key=lambda d: d.rectangle().width()*d.rectangle().height())
            self.rect = self.document.rectangle()
            self.window_rect = self.window.rectangle()
            viewport = self.page.evaluate("({w:innerWidth,h:innerHeight})")
            self.scale_x, self.scale_y = self.rect.width()/viewport["w"], self.rect.height()/viewport["h"]
            if not .5 <= self.scale_x <= 4 or abs(self.scale_x-self.scale_y) > .04:
                raise RuntimeError("无法可靠映射窗口与视口坐标；系统模式已停止")
            self.last_position = None
            self._check()
        finally:
            self.page.evaluate("title => document.title = title", old_title)

    def _cursor(self):
        point = wintypes.POINT()
        if not self.user.GetCursorPos(ctypes.byref(point)):
            raise RuntimeError("无法读取鼠标位置")
        return point.x, point.y

    def local_position(self):
        x, y = self._cursor()
        return ((x-self.rect.left)/self.scale_x, (y-self.rect.top)/self.scale_y)

    def _check(self):
        self.ctx.check_cancelled()
        if not self.window or self.user.GetForegroundWindow() != self.window.handle or self.user.IsIconic(self.window.handle):
            raise RuntimeError("目标浏览器已失焦或最小化，停止系统输入")
        if self.window.rectangle() != self.window_rect or self.document.rectangle() != self.rect:
            raise RuntimeError("浏览器窗口或页面区域已移动，停止系统输入")
        if self.last_position and max(abs(a-b) for a, b in zip(self._cursor(), self.last_position)) > 4:
            raise RuntimeError("检测到用户移动鼠标，停止系统输入")

    def move(self, x, y):
        self._check()
        point = (round(self.rect.left+x*self.scale_x), round(self.rect.top+y*self.scale_y))
        if not self.user.SetCursorPos(*point):
            raise RuntimeError("系统鼠标移动失败")
        self.last_position = point

    def down(self):
        self._check()
        self.button_down = True
        self.user.mouse_event(0x0002, 0, 0, 0, 0)

    def up(self):
        if self.button_down:
            self.user.mouse_event(0x0004, 0, 0, 0, 0)
            self.button_down = False

    def clear(self):
        self._check()
        self.ctrl_down = True
        try:
            self.user.keybd_event(0x11, 0, 0, 0)
            self.user.keybd_event(0x41, 0, 0, 0)
            self.user.keybd_event(0x41, 0, 2, 0)
        finally:
            self.user.keybd_event(0x11, 0, 2, 0)
            self.ctrl_down = False
        self._check()
        self.user.keybd_event(0x08, 0, 0, 0)
        self.user.keybd_event(0x08, 0, 2, 0)

    def type_char(self, char):
        self._check()
        from pywinauto.keyboard import send_keys
        # Escape pywinauto's command syntax; never interpret input as shortcuts.
        escaped = {"{": "{{}", "}": "{}}", "+": "{+}", "^": "{^}", "%": "{%}",
                   "~": "{~}", "(": "{(}", ")": "{)}"}.get(char, char)
        send_keys(escaped, pause=0, with_spaces=True, with_tabs=True, with_newlines=True, vk_packet=True)

    def end(self):
        self._check()
        self.ctrl_down = True
        try:
            self.user.keybd_event(0x11, 0, 0, 0)
            self.user.keybd_event(0x23, 0, 0, 0)
            self.user.keybd_event(0x23, 0, 2, 0)
        finally:
            self.user.keybd_event(0x11, 0, 2, 0)
            self.ctrl_down = False

    def scroll(self, delta_y):
        if self.window is None:
            self.prepare()
        self._check()
        self.user.mouse_event(0x0800, 0, 0, int(-delta_y), 0)

    def close(self):
        self.up()
        if self.ctrl_down:
            self.user.keybd_event(0x11, 0, 2, 0)
            self.ctrl_down = False
        if self.mutex:
            self.kernel.ReleaseMutex(self.mutex)
            self.kernel.CloseHandle(self.mutex)
            self.mutex = None
        if self.dpi:
            self.user.SetThreadDpiAwarenessContext(self.dpi)
            self.dpi = None

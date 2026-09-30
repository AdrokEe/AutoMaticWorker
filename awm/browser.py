"""Synchronous Playwright-compatible sessions and cancellable input actions."""
import importlib
import math
import random
import time
from contextlib import contextmanager

from awm.environment import FileLock, require_environment


class InteractionError(RuntimeError):
    pass


class OutcomeUnknown(InteractionError):
    """An action was dispatched; do not repeat it without reconciling state."""


def trajectory(start, end, rng):
    """Bounded cubic curve with smooth acceleration; no empirical stealth claim."""
    distance = math.dist(start, end)
    steps = max(2, min(70, int(distance / 10) + 8))
    dx, dy = end[0] - start[0], end[1] - start[1]
    bend = rng.uniform(-0.18, 0.18)
    c1 = (start[0] + dx * .3 - dy * bend, start[1] + dy * .3 + dx * bend)
    c2 = (start[0] + dx * .7 - dy * bend, start[1] + dy * .7 + dx * bend)
    points = []
    for i in range(1, steps + 1):
        t = i / steps
        t = t * t * (3 - 2 * t)
        s = 1 - t
        points.append(tuple(s**3 * start[j] + 3*s*s*t*c1[j] + 3*s*t*t*c2[j] + t**3*end[j]
                            for j in (0, 1)))
    return points


class BrowserSession:
    def __init__(self, ctx, config):
        self.ctx = ctx
        self.config = require_environment(config)
        self.engine = self.browser = self.context = self.page = None
        self._locks = []
        self._owned_pages = []
        self._actions = []
        self._entered = False

    def __enter__(self):
        if self._entered:
            raise InteractionError("会话不可重复启动")
        self._entered = True
        self.ctx.check_cancelled()
        config = self.config
        try:
            if config["profile"]:
                self._locks.append(FileLock(self.ctx._home / "profiles" / (config["profile"] + ".lock")))
            self.module = importlib.import_module(config["backend"] + ".sync_api")
            self.engine = self.module.sync_playwright().start()
            if config["cdp_url"]:
                self.browser = self.engine.chromium.connect_over_cdp(config["cdp_url"], timeout=10000)
                if not self.browser.contexts:
                    raise InteractionError("接管浏览器没有可用上下文")
                self.context = self.browser.contexts[0]
                # Never navigate or close a pre-existing user tab.
                self.page = self.context.new_page()
                self._owned_pages.append(self.page)
            else:
                launch = {"executable_path": config["executable_path"], "headless": config["headless"],
                          "timeout": 10000, "args": ["--disable-background-networking", "--no-first-run"]}
                if config["input_mode"] == "desktop":
                    launch["args"].append("--force-renderer-accessibility")
                if config["profile"]:
                    self.context = self.engine.chromium.launch_persistent_context(
                        str(self.ctx._home / "profiles" / config["profile"]), no_viewport=True, **launch)
                    self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
                else:
                    self.browser = self.engine.chromium.launch(**launch)
                    self.context = self.browser.new_context(no_viewport=True)
                    self.page = self.context.new_page()
            self.context.set_default_timeout(1000)
            self.context.set_default_navigation_timeout(10000)
            self.ctx.check_cancelled()
            return self
        except BaseException:
            self.close()
            raise

    def actions(self, page=None, *, seed=None):
        if self.context is None:
            raise InteractionError("请在 with ctx.browser() 中操作浏览器")
        result = Actions(self, page or self.page, seed=seed)
        self._actions.append(result)
        return result

    def new_page(self):
        self.ctx.check_cancelled()
        page = self.context.new_page()
        self._owned_pages.append(page)
        return page

    @contextmanager
    def popup(self, page=None, timeout_ms=10000):
        """Pair with an action. Returned Playwright EventInfo exposes .value."""
        with (page or self.page).expect_popup(timeout=timeout_ms) as pending:
            yield pending
        self._owned_pages.append(pending.value)

    def close(self):
        # Cleanup must not check cancellation: release even during forced shutdown.
        errors = []

        def release(callback):
            try:
                callback()
            except Exception as exc:
                errors.append(exc)

        for action in reversed(self._actions):
            release(action.close)
        self._actions.clear()
        if self.config["cdp_url"]:
            for page in self._owned_pages:
                try:
                    page.close()
                except Exception:
                    pass  # External user may already have closed this owned tab.
            # stop() disconnects; browser.close() would risk closing external resources.
        elif self.context:
            release(self.context.close)
        if self.browser and not self.config["cdp_url"]:
            release(self.browser.close)
        if self.engine:
            release(self.engine.stop)
        self.engine = self.context = self.browser = self.page = None
        self._owned_pages.clear()
        for lock in reversed(self._locks):
            release(lock.close)
        self._locks.clear()
        if errors:
            raise errors[0]

    def __exit__(self, *_):
        self.close()


class Actions:
    def __init__(self, session, page, *, seed=None):
        self.session, self.page, self.ctx = session, page, session.ctx
        self.rng = random.Random(seed)
        self.position = (0., 0.)
        self.desktop = None
        if session.config["input_mode"] == "desktop":
            from awm.desktop import DesktopInput
            self.desktop = DesktopInput(page, self.ctx)

    def close(self):
        if self.desktop:
            self.desktop.close()
            self.desktop = None

    def wait(self, predicate, timeout_ms=10000):
        if not isinstance(timeout_ms, (int, float)) or not 0 < timeout_ms <= 86400000:
            raise ValueError("timeout_ms 必须在 0–86400000 之间")
        deadline = time.monotonic() + timeout_ms / 1000
        while True:
            self.ctx.check_cancelled()
            try:
                value = predicate()
                if value:
                    return value
            except self.session.module.TimeoutError:
                pass
            if time.monotonic() >= deadline:
                raise TimeoutError("等待页面条件超时")
            self.ctx.sleep(.05)

    def wait_visible(self, target, timeout_ms=10000):
        self.wait(lambda: target.is_visible(), timeout_ms)
        return target

    def _profile(self, profile):
        result = profile or self.session.config["interaction"]
        if result not in ("direct", "natural"):
            raise ValueError("profile 只支持 direct 或 natural")
        return result

    def _move(self, point, profile):
        viewport = self.page.evaluate("({width:innerWidth,height:innerHeight})")
        points = trajectory(self.position, point, self.rng) if profile == "natural" else [point]
        for x, y in points:
            self.ctx.check_cancelled()
            x = min(max(x, 0), viewport["width"] - 1)
            y = min(max(y, 0), viewport["height"] - 1)
            if self.desktop:
                self.desktop.move(x, y)
            else:
                self.page.mouse.move(x, y)
            self.position = (x, y)
            if profile == "natural":
                self.ctx.sleep(self.rng.uniform(.006, .016))

    def _aim(self, target, profile, timeout_ms):
        def ready():
            target.click(trial=True, timeout=200)
            box = target.bounding_box(timeout=200)
            if not box or box["width"] < 1 or box["height"] < 1:
                return False
            viewport = self.page.evaluate("({width:innerWidth,height:innerHeight})")
            left, top = max(0, box["x"]), max(0, box["y"])
            right = min(viewport["width"], box["x"] + box["width"])
            bottom = min(viewport["height"], box["y"] + box["height"])
            if right - left < 1 or bottom - top < 1:
                return False
            fraction = self.rng.uniform(.35, .65) if profile == "natural" else .5
            point = (left + (right-left)*fraction, top + (bottom-top)*fraction)
            if self.desktop:
                self.desktop.prepare()
                self.position = self.desktop.local_position()
            self._move(point, profile)
            if profile == "natural":
                self.ctx.sleep(self.rng.uniform(.04, .13))
            current = target.bounding_box(timeout=200)
            if not current or any(abs(box[k]-current[k]) > .5 for k in box):
                return False
            # Trial at the exact offset verifies hit-testing, including ancestor iframe overlays.
            target.click(trial=True, position={"x": point[0]-box["x"], "y": point[1]-box["y"]}, timeout=200)
            final = target.bounding_box(timeout=200)
            return bool(final and all(abs(box[k]-final[k]) <= .5 for k in box))
        self.wait(ready, timeout_ms)

    def hover(self, target, *, profile=None, timeout_ms=10000):
        self._aim(target, self._profile(profile), timeout_ms)

    def click(self, target, *, profile=None, timeout_ms=10000, after=None):
        profile = self._profile(profile)
        self._aim(target, profile, timeout_ms)
        self.ctx.check_cancelled()
        mouse = self.desktop or self.page.mouse
        try:
            try:
                mouse.down()
                if profile == "natural":
                    self.ctx.sleep(self.rng.uniform(.035, .09))
            finally:
                mouse.up()
            if after:
                self.wait(after, timeout_ms)
        except Exception as exc:
            from awm.sdk import Cancelled
            if isinstance(exc, Cancelled):
                raise
            raise OutcomeUnknown("点击可能已发送但未确认结果；请核对页面，不能直接重复提交") from exc

    def _focused(self, target):
        return target.evaluate("el => el === el.getRootNode().activeElement", timeout=200)

    def type_text(self, target, value, *, clear=True, profile=None, sensitive=False, timeout_ms=10000):
        if not isinstance(value, str):
            raise ValueError("输入内容必须是字符串")
        try:
            self.wait(lambda: target.is_editable(timeout=200), timeout_ms)
            self.click(target, profile=profile, timeout_ms=timeout_ms)
            self.wait(lambda: self._focused(target), timeout_ms)
            expected = "" if clear else target.input_value(timeout=200)
            if clear:
                if self.desktop:
                    self.desktop.clear()
                else:
                    self.page.keyboard.press("ControlOrMeta+A")
                    self.page.keyboard.press("Backspace")
            elif self.desktop:
                self.desktop.end()
            else:
                self.page.keyboard.press("ControlOrMeta+End")
            for char in value:
                self.ctx.check_cancelled()
                if not self._focused(target):
                    raise InteractionError("输入焦点已改变，已停止；没有自动重输")
                if self.desktop:
                    self.desktop.type_char(char)
                else:
                    self.page.keyboard.type(char)
                if self._profile(profile) == "natural":
                    self.ctx.sleep(self.rng.uniform(.035, .12))
            if target.input_value(timeout=200) != expected + value:
                raise InteractionError("输入值与预期不一致；没有自动重输")
        except Exception:
            from awm.sdk import Cancelled
            import sys
            if sensitive and not isinstance(sys.exception(), Cancelled):
                raise InteractionError("敏感字段输入失败；已隐藏输入细节") from None
            raise

    def scroll(self, delta_y):
        if not isinstance(delta_y, (int, float)) or not math.isfinite(delta_y) or abs(delta_y) > 100000:
            raise ValueError("滚动距离无效")
        remaining = delta_y
        while abs(remaining) > .1:
            self.ctx.check_cancelled()
            step = math.copysign(min(120, abs(remaining)), remaining)
            if self.desktop:
                self.desktop.scroll(step)
            else:
                self.page.mouse.wheel(0, step)
            remaining -= step
            self.ctx.sleep(.03)

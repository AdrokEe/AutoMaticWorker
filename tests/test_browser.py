import importlib.util
import json
import os
import shutil
import threading
import time
from pathlib import Path

import pytest

from awm.browser import OutcomeUnknown, InteractionError
from awm.environment import DEFAULTS, FileLock, inspect_environment, settings
from awm.packages import ROOT, FlowError, pack, read_json, validate_directory, write_json
from awm.runtime import Runtime
from awm.sdk import Context, Cancelled
from awm.server import create_app


def eventually(fn, timeout=15):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        value = fn()
        if value:
            return value
        time.sleep(.03)
    raise AssertionError("Condition not reached")


@pytest.fixture
def runtime(tmp_path):
    runtime = Runtime(tmp_path / "data")
    yield runtime
    runtime.close()


def install(runtime, tmp_path, code=None, name="report"):
    path = tmp_path / "flow"
    shutil.copytree(ROOT / "examples" / name, path)
    if code:
        (path / "flow.py").write_text(code, encoding="utf-8")
    runtime.install(pack(path, tmp_path / "flow.zip"))


def test_environment_checks_do_not_launch_or_download(monkeypatch, tmp_path):
    import subprocess
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: pytest.fail("Preflight launched a process"))
    result = inspect_environment({"executable_path": str(tmp_path / "missing.exe")})
    assert not result["ready"] and "本地" in result["errors"][-1]


@pytest.mark.parametrize("value", [{"unknown": True}, {"headless": "false"}, {"profile": "../escape"},
    {"cdp_url": "http://example.com:9222"}, {"cdp_url": "http://user:pass@localhost:9222"},
    {"input_mode": "desktop", "headless": True}, {"cdp_url": "http://localhost:9222", "profile": "a"}])
def test_environment_rejects_invalid_settings(value):
    with pytest.raises(FlowError):
        settings(value)


def test_profile_lock_released(tmp_path):
    lock = FileLock(tmp_path / "profile.lock")
    try:
        with pytest.raises(FlowError):
            FileLock(tmp_path / "profile.lock")
    finally:
        lock.close()
    FileLock(tmp_path / "profile.lock").close()


def test_cleanup_releases_remaining_resources_after_failure(tmp_path):
    from types import SimpleNamespace
    from awm.browser import BrowserSession
    released = []

    def fail():
        raise RuntimeError("cleanup failed")

    session = object.__new__(BrowserSession)
    session.config = DEFAULTS.copy()
    session._actions = [SimpleNamespace(close=fail)]
    session.context = SimpleNamespace(close=fail)
    session.browser = SimpleNamespace(close=lambda: released.append("browser"))
    session.engine = SimpleNamespace(stop=lambda: released.append("engine"))
    session.page = None
    session._owned_pages = []
    session._locks = [FileLock(tmp_path / "profile.lock")]
    ctx = Context("test", tmp_path, tmp_path / "cancel", False, lambda _: None)
    ctx._resources = [SimpleNamespace(close=lambda: released.append("other")), session]
    with pytest.raises(RuntimeError, match="cleanup failed"):
        ctx.close()
    assert released == ["browser", "engine", "other"]
    FileLock(tmp_path / "profile.lock").close()
    ctx.close()
    session.close()


def test_manifest_browser_requires_new_schema_and_capability(tmp_path):
    source = tmp_path / "flow"
    shutil.copytree(ROOT / "examples/browser-form", source)
    m = validate_directory(source)
    m["schema_version"] = "1.0"
    write_json(source / "manifest.json", m)
    with pytest.raises(FlowError):
        validate_directory(source)
    m["schema_version"] = "1.1"
    m["capabilities"].remove("desktop-input")
    write_json(source / "manifest.json", m)
    with pytest.raises(FlowError):
        validate_directory(source)


def test_missing_browser_fails_before_start(runtime, tmp_path):
    install(runtime, tmp_path, name="browser-form")
    with pytest.raises(FlowError, match="本地"):
        runtime.start("sample-browser-form", {})
    assert not runtime.history()


def test_wait_resume_stale_signal_and_cancel(runtime, tmp_path):
    install(runtime, tmp_path, code="def run(ctx, config):\n ctx.wait_for_user('first', 10)\n ctx.wait_for_user('second', 10)\n return ctx.result('done')\n")
    record = runtime.start("sample-report", {})
    rid = record["id"]
    first = eventually(lambda: (r if (r := runtime.get_run(rid))["status"] == "waiting" else None))
    with pytest.raises(FlowError):
        runtime.save_environment({})
    with pytest.raises(FlowError):
        runtime.resume(rid, "bad")
    runtime.resume(rid, first["wait_id"])
    second = eventually(lambda: (r if (r := runtime.get_run(rid))["status"] == "waiting" and r["wait_id"] != first["wait_id"] else None))
    with pytest.raises(FlowError):
        runtime.resume(rid, first["wait_id"])
    runtime.cancel(rid)
    runtime.thread.join(5)
    assert runtime.get_run(rid)["status"] == "cancelled"
    assert second["wait_message"] == "second"


def test_resume_api_and_timeout(runtime, tmp_path):
    install(runtime, tmp_path, code="def run(ctx, config):\n ctx.wait_for_user('confirm', 10)\n return ctx.result('done')\n")
    client = create_app(runtime).test_client()
    token = client.get('/api/bootstrap').json['token']
    rid = runtime.start("sample-report", {})["id"]
    record = eventually(lambda: (r if (r := runtime.get_run(rid))["status"] == "waiting" else None))
    assert client.post(f'/api/runs/{rid}/resume', json={"wait_id": record['wait_id']}).status_code == 403
    assert client.post(f'/api/runs/{rid}/resume', json={"wait_id": record['wait_id']}, headers={'X-AWM-Token': token}).status_code == 200
    runtime.thread.join(5)
    assert runtime.get_run(rid)["status"] == "succeeded"


@pytest.fixture
def browser_path():
    value = os.environ.get("AWM_TEST_BROWSER")
    if not value:
        pytest.skip("Set AWM_TEST_BROWSER to run local browser integration tests")
    return value


@pytest.fixture(params=["playwright", "patchright"])
def context(request, tmp_path, browser_path):
    if importlib.util.find_spec(request.param) is None:
        pytest.skip(f"Optional {request.param} is not installed")
    output = tmp_path / "output"
    output.mkdir()
    ctx = Context("test", output, tmp_path / "cancel", False, lambda _: None,
                  browser_settings={**DEFAULTS, "backend": request.param, "headless": True,
                                    "executable_path": browser_path}, home=tmp_path)
    yield ctx
    ctx.close()


def test_real_actions_and_no_duplicate_submission(context):
    with context.browser() as browser:
        page = browser.page
        page.set_content('''<input aria-label="name"><input id="other"><button>Save</button>
        <script>document.body.dataset.count=0;document.body.dataset.moves=0;document.onmousemove=()=>document.body.dataset.moves++;document.querySelector('button').onclick=()=>document.body.dataset.count++;</script>''')
        actions = browser.actions(seed=5)
        target = page.get_by_label("name")
        actions.type_text(target, "Hello 中文🙂")
        assert target.input_value() == "Hello 中文🙂"
        assert int(page.locator('body').get_attribute('data-moves')) > 5
        with pytest.raises(OutcomeUnknown):
            actions.click(page.get_by_role("button"), after=lambda: False, timeout_ms=500)
        assert page.locator('body').get_attribute('data-count') == '1'
        page.evaluate("document.querySelector('input').oninput=()=>document.querySelector('#other').focus()")
        with pytest.raises(InteractionError, match="焦点"):
            actions.type_text(target, "secret", clear=False)


def test_cancel_mid_input(context):
    with context.browser() as browser:
        browser.page.set_content('<input aria-label="name">')
        actions = browser.actions()
        timer = threading.Timer(.4, context._cancel_file.touch)
        timer.start()
        try:
            with pytest.raises(Cancelled):
                actions.type_text(browser.page.get_by_label("name"), "x"*100)
        finally:
            timer.join()


def test_profile_persists_and_popup_owned(context):
    context._browser_settings["profile"] = "test-profile"
    with context.browser() as browser:
        browser.context.add_cookies([{"name": "demo", "value": "saved", "domain": "localhost", "path": "/", "expires": time.time()+3600}])
        browser.page.set_content('<button onclick="window.open(\'about:blank\')">New tab</button>')
        with browser.popup() as popup:
            browser.actions().click(browser.page.get_by_role('button'))
        assert popup.value != browser.page
    with context.browser() as browser:
        assert any(c['name'] == 'demo' and c['value'] == 'saved' for c in browser.context.cookies())


def test_attached_browser_survives_sdk_close(context, tmp_path, browser_path):
    import subprocess
    from urllib.request import build_opener, ProxyHandler
    from awm.processes import ProcessTree
    profile = tmp_path / 'external-profile'
    process = subprocess.Popen([browser_path, '--headless=new', '--remote-debugging-port=0',
        '--no-first-run', '--no-default-browser-check', '--disable-background-networking',
        f'--user-data-dir={profile}', 'about:blank'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    tree = ProcessTree(process)
    try:
        port_file = profile / 'DevToolsActivePort'
        eventually(port_file.exists)
        port = port_file.read_text().splitlines()[0]
        url = f'http://127.0.0.1:{port}'
        client = build_opener(ProxyHandler({}))
        def tabs():
            with client.open(url+'/json/list', timeout=3) as response:
                return {t['id'] for t in json.load(response) if t['type'] == 'page'}
        original = tabs()
        context._browser_settings.update(cdp_url=url, headless=False)
        with context.browser() as browser:
            browser.page.set_content('<h1>owned test tab</h1>')
            assert len(tabs()) > len(original)
        assert process.poll() is None
        assert tabs() == original
    finally:
        tree.close()
        process.wait(timeout=5)


def test_worker_browser_cancel_releases_profile(runtime, tmp_path, browser_path):
    runtime.save_environment({'executable_path': browser_path, 'headless': True, 'profile': 'cancel-profile'})
    install(runtime, tmp_path, name='browser-form', code="def run(ctx, config):\n with ctx.browser() as browser:\n  ctx.wait_for_user('ready', 30)\n return ctx.result('done')\n")
    rid = runtime.start('sample-browser-form', {})['id']
    eventually(lambda: runtime.get_run(rid)['status'] == 'waiting')
    runtime.cancel(rid)
    runtime.thread.join(8)
    assert runtime.get_run(rid)['status'] == 'cancelled'
    assert runtime.process.awm_tree.closed
    FileLock(runtime.home/'profiles/cancel-profile.lock').close()


def test_overlay_prevents_click_and_iframe(context):
    with context.browser() as browser:
        page = browser.page
        page.set_content('''<button onclick="document.body.dataset.clicked='yes'">Save</button><div style="position:fixed;inset:0;background:red"></div>''')
        with pytest.raises(TimeoutError):
            browser.actions().click(page.get_by_role('button'), timeout_ms=400)
        assert page.locator('body').get_attribute('data-clicked') is None
        page.set_content('''<iframe srcdoc='<input aria-label="field">'></iframe>''')
        target = page.frame_locator('iframe').get_by_label('field')
        browser.actions().type_text(target, 'frame text')
        assert target.input_value() == 'frame text'


@pytest.mark.parametrize("backend", ["playwright", "patchright"])
@pytest.mark.parametrize("preview", [True, False])
def test_browser_package_real_worker(runtime, tmp_path, browser_path, backend, preview):
    if importlib.util.find_spec(backend) is None:
        pytest.skip("Optional backend missing")
    runtime.save_environment({"backend": backend, "headless": True, "executable_path": browser_path})
    install(runtime, tmp_path, name="browser-form")
    rid = runtime.start("sample-browser-form", {"name": "中文🙂", "note": "test"}, preview)["id"]
    runtime.thread.join(30)
    record = runtime.get_run(rid)
    assert record["status"] == "succeeded", record
    receipt = read_json(runtime.artifact(rid, "receipt.json"))
    assert receipt["name"] == "中文🙂"
    assert receipt["submissions"] == (0 if preview else 1)
    assert runtime.process.awm_tree.closed

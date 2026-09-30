# 浏览器 SDK · 平台 0.2.1

使用基础 Playwright 的 Page / Locator，配合 `ctx.browser()` 和动作 SDK 制作流程。标准后端 Playwright，可选 Patchright；均只启动已配置的本地浏览器，不下载组件。任意 pip 依赖仍不支持由流程包安装。

## 准备环境

开发机可安装 `requirements-browser.txt`；可选后端见 `requirements-browser-patchright.txt`，Windows 系统输入见 `requirements-desktop-input.txt`。目标断网机器使用事先准备的本地依赖和浏览器；缺项时平台只报告错误。

已验证的完整可选组件版本记录在 `requirements-browser-lock-windows.txt`。在相同系统、架构和 Python 版本的构建环境准备 wheelhouse 后，目标环境可执行：

```powershell
.venv\Scripts\python.exe -m pip install --no-index --find-links X:\wheelhouse -r requirements-browser-lock-windows.txt
```

wheelhouse 必须包括所有传递依赖；此命令不包含 Python 安装、浏览器或 WebView2，不等于 M4 的完整离线安装包。平台基础依赖也须预备。不要在目标机运行 `playwright install`。

在工作台的“浏览器环境”填写本地 Chromium / Chrome / Edge 可执行文件完整路径，保存并检查。选择实际已安装后端。组件检查不启动浏览器；版本兼容、企业策略和端口是否可用在实际启动时验证。

CLI 使用同一配置：

```powershell
python -m awm environment --data-dir output/dev --config browser-settings.json
python -m awm environment --data-dir output/dev
python -m awm init output/my-browser --id my-browser --template browser-form
python -m awm run output/my-browser --data-dir output/dev --dry-run
```

`browser-settings.json` 示例（替换成本机路径）：

```json
{
  "backend": "playwright",
  "executable_path": "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "headless": false,
  "profile": "",
  "cdp_url": "",
  "input_mode": "browser",
  "interaction": "natural"
}
```

浏览器配置按平台数据目录保存；CLI 和桌面使用相同数据目录时不可同时运行。任务运行期间不可修改配置；每次浏览器任务保存环境快照。

## 清单与入口

浏览器流程使用规范 1.1、平台 `>=0.2.1,<0.3.0`，在标准清单中增加：

```json
{
  "schema_version": "1.1",
  "capabilities": ["browser", "network", "file-write"],
  "dependencies": [],
  "browser": {"backends": ["playwright", "patchright"], "input_modes": ["browser"]}
}
```

这里只展示新增字段，完整清单见 [浏览器示例](../examples/browser-form/manifest.json)。如果支持系统输入，在 `input_modes` 中增加 `desktop`，同时声明 `desktop-input` 能力。平台在创建任务前检查所选后端和输入模式是否被流程接受。只用旧规范 1.0 的标准库流程无需浏览器组件。

```python
def run(ctx, config):
    with ctx.browser() as browser:
        page = browser.page
        actions = browser.actions()
        page.goto(config["intranet_url"])
        actions.type_text(page.get_by_label("姓名"), config["name"])
        if ctx.dry_run:
            return ctx.result("已填表预览，未提交")
        actions.click(
            page.get_by_role("button", name="保存", exact=True),
            after=lambda: page.get_by_role("status").inner_text() == "保存成功",
        )
    return ctx.result("页面已确认保存成功")
```

示例定位器及 URL 参数须由真实流程定义。本地可执行参考包在 [examples/browser-form](../examples/browser-form)。其试运行不点击提交，正式运行核对恰好一次回执。

## 已实现接口

| 接口 | 行为 |
| --- | --- |
| `with ctx.browser() as session` | 启动所声明的浏览器环境，退出释放自建资源；遗漏退出时 worker 也清理已注册会话 |
| `session.page` / `session.context` | 原生同步 Playwright-compatible Page / BrowserContext，可直接使用定位器和网页 API |
| `session.actions(page=None, seed=None)` | 为页面创建操作器；seed 用于测试复现，不是隐身参数 |
| `session.new_page()` | 新建本次流程拥有的标签页 |
| `with session.popup(page=None, timeout_ms=10000) as pending` | 与打开窗口的动作配对，结束后通过 `pending.value` 取得并登记新页面 |
| `actions.click(target, profile=None, timeout_ms=10000, after=None)` | 可执行性检查、曲线或直接移动、左键点击；可选后置条件 |
| `actions.hover(target, profile=None, timeout_ms=10000)` | 使用与点击相同的定位及命中检查后悬停；目标须可点击 |
| `actions.type_text(target, value, clear=True, profile=None, sensitive=False, timeout_ms=10000)` | 点击聚焦后清空或移至末尾追加，逐字输入并核对最终值；支持 input/textarea |
| `actions.scroll(delta_y)` | 分段纵向滚动；实际页面状态可用 wait 检查 |
| `actions.wait(predicate, timeout_ms=10000)` | 可取消轮询无副作用的页面判据，只重试等待超时，不吞掉其他业务异常 |
| `actions.wait_visible(target, timeout_ms=10000)` | 等待可见并返回定位器 |
| `ctx.sleep(seconds)` | 可取消等待；上限一天 |
| `with ctx.step(name)` | 记录步骤开始、成功结束及耗时，异常继续向上抛出 |
| `ctx.wait_for_user(message, timeout=300)` | 进入人工等待，界面可以继续或取消；继续后作者必须重新验证页面；上限一天 |

`profile` 为 `natural` 或 `direct`，默认使用环境设置。natural 是受约束曲线、悬停和随机间隔；direct 直接移动并快速逐字输入。两者都做目标及最终值检查。不是鼠标行为统计模型或反检测保证。

点击准备阶段可以重新定位，但发送后不自动补点；后置检查失败抛出 `awm.browser.OutcomeUnknown`，应先核实业务结果，不得直接重试提交。未给 after 只代表动作发送结束，不代表业务成功。轮询判据必须快速返回；原生 Playwright 的长阻塞调用仍受进程级取消保障，不保证逐调用即时取消。

输入不使用剪贴板或随机错字。`sensitive=True` 隐藏输入阶段异常细节；秘密参数仍应在清单标记 `secret`，不要用秘密构造定位器、日志和截图。中文和 emoji 支持文本提交，不实现拼音候选或 IME composition；依赖真实输入法事件的页面需专门适配。

## 登录、接管与资源归属

- profile 留空为临时上下文，结束时关闭；填入名称后使用平台专用持久目录（字母/数字/下划线/短横线），跨进程独占。认证状态保留在本机，不入 ZIP。
- 人工登录选择可见窗口，调用 `ctx.wait_for_user`；桌面运行详情显示继续按钮。CLI 添加 `--interactive`，完成后按 Enter；不加该选项的 CLI 遇到等待会停止并解释原因。
- 接管地址只支持本机 HTTP 调试端口。接管时 profile 留空、headless 为 false；SDK 创建新标签页，复用浏览器上下文，不导航原有标签页。
- 结束接管会话只关闭 SDK 显式登记的页面并断开连接，不调用外部浏览器关闭接口。通过原生 API 创建的额外资源由作者管理；优先使用 new_page/popup。
- 新建浏览器按任务进程树管理；取消先协作退出，超过宽限期终止进程树。外部接管浏览器不属于任务进程树。
- Patchright 默认脚本执行上下文与 Playwright 有差别。跨后端流程优先读取 DOM 内容/属性，不依赖页面的 `window` 业务变量；需要原生扩展时限制清单后端。

## Windows 系统输入

系统模式只在用户明确选择后启用，不作为浏览器模式失败后的自动回退。使用 UI Automation 识别浏览器页面的物理边界并映射 CSS 坐标，检查窗口焦点、位置及鼠标被人为移动；异常停止操作。它占用真实桌面光标，并通过当前桌面会话的命名互斥锁避免两个自动化进程同时输入。

要求 Windows、可见浏览器窗口、pywinauto 组件和可用 UIA 文档区域。无法可靠取得区域或缩放映射时失败，不猜坐标。已在本机当前桌面配置实测；不同缩放、多屏、远程桌面、锁屏和自定义浏览器外壳不作通用兼容承诺，需要现场验收。人工输入造成焦点或光标改变会中止当次动作。

可重复的可见测试（会短暂占用鼠标键盘）：

```powershell
.venv\Scripts\python.exe scripts/browser_desktop_smoke.py --browser "C:\Program Files\Google\Chrome\Application\chrome.exe"
```

## 验证与离线边界

```powershell
$env:AWM_TEST_BROWSER="C:\Program Files\Google\Chrome\Application\chrome.exe"
.venv\Scripts\python.exe -m pytest -q
```

没有 AWM_TEST_BROWSER 时，真实浏览器用例明确跳过；基础包测试仍执行。测试只访问临时本地页面，不执行客户业务。配置和 SDK 不含下载逻辑；浏览器/操作系统的后台通信仍须按 [离线部署矩阵](OFFLINE_DESIGN.md) 独立观测。本次交付不等于完整离线安装包、反爬通过率或涉密认证。

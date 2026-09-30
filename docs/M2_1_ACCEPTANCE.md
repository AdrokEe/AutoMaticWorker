# M2.1 浏览器 SDK 验收记录

日期：2026-09-30。平台版本：0.2.1 开发版；规范版本：1.0 / 1.1。

核心实现已完成并在当前 Windows 环境验证。本文记录功能证据，完整离线安装发行及隔离环境验收仍按 [M4 与离线矩阵](OFFLINE_DESIGN.md) 推进。

## 交付内容

- 本地浏览器环境配置与启动前检查；Playwright 默认、Patchright 可选；运行时不下载依赖或浏览器。
- `ctx.browser()` 会话、专用持久登录目录互斥、本机 CDP 接管、新标签页和弹窗归属、退出与取消清理。
- 默认浏览器内模拟输入；曲线移动、悬停、左键点击、逐字输入、滚动及可取消等待；可显式选择 Windows 系统鼠标键盘。
- 点击发送后不自动重试，后置判据失败使用 OutcomeUnknown；输入检查焦点与最终值，避免静默错填。
- 人工等待与继续、过期继续请求拒绝、等待时取消；桌面界面与 CLI 共用运行协议。
- 规范 1.1 浏览器需求声明、公开本地填表示例、初始化模板、制作文档及 AI Skill 更新。

接口及运行方法见 [BROWSER_SDK.md](BROWSER_SDK.md)，公开示例见 [browser-form](../examples/browser-form)。

## 实际环境与结果

Windows；Python 3.14.2；Node.js 24.12.0；本地 Chrome 154.0.8037.58；Playwright / Patchright 1.63.0；pywinauto 0.6.9。基础及可选依赖分别锁定在根目录 requirements-lock-windows.txt、requirements-browser-lock-windows.txt。

| 验证 | 实际结果 |
| --- | --- |
| Python 全量回归 | **56 passed，0 skipped**；指定 AWM_TEST_BROWSER，双后端均真实运行 |
| 浏览器行为 | 中文/emoji、iframe、遮挡拒绝点击、焦点变化中止、输入中取消、后置条件失败后仅提交一次 |
| 会话与进程 | 持久 cookie、弹窗归属、接管结束后外部浏览器及原标签保留、任务取消释放 profile 锁、清理失败仍释放其他资源 |
| 平台运行协议 | 环境缺项时创建任务前拒绝；等待/继续、过期 nonce 拒绝、取消和继续接口令牌校验 |
| 双后端示例 | 各自在真实 worker 中预览与正式运行，回执提交次数分别为 0 / 1 |
| 前端 | Vue TypeScript 检查及生产构建通过 |
| 工作台界面 | 环境保存、添加浏览器示例、试运行、正式运行、结果链接及 JSON 内容核验通过；临时合成等待包验证继续成功及等待时取消 |
| 界面检查 | 查看环境页、等待页和完成页截图；浏览器控制台 0 错误、0 警告 |
| Windows 系统输入 | 可见 Chrome 完整本地流程通过，中文姓名及 `+^%{}()` 特殊字符原样输出，提交恰好 1 次；回执记录 102 次移动、28 次键盘事件、22 次 input 事件（随机运行次数不固定） |
| 桌面生命周期 | 真实 WebView2 加载构建界面；关闭窗口取消运行、停止服务并释放数据锁 |
| 作者 CLI | 浏览器模板 init、environment、目录 validate、run --dry-run、pack、ZIP validate 全链路通过；回执提交为 0，运行记录保存后端版本 |
| 制作 Skill / 依赖 | quick_validate 通过；pip check 无冲突；Skill 已与实际接口同步，本次没有新增独立 AI 制作评测 |

重复执行主要检查：

```powershell
$env:AWM_TEST_BROWSER='C:\Program Files\Google\Chrome\Application\chrome.exe'
.venv\Scripts\python.exe -m pytest -q
npm run build --prefix vue_frontend
.venv\Scripts\python.exe scripts/desktop_smoke.py
# 以下测试会占用真实鼠标键盘，需在可交互的 Windows 桌面执行
.venv\Scripts\python.exe scripts/browser_desktop_smoke.py --browser $env:AWM_TEST_BROWSER
```

本地证据保存在忽略目录：output/browser-desktop-smoke.json、output/desktop-smoke.json、output/m21-cli-check.json、output/m21-ui-preview.png、output/m21-ui-run.png、output/playwright/m21-waiting.png、output/playwright/m21-environment.png，以及 output/m21-ui 的隔离运行记录。测试截图和机器配置不进入发行包。

## 已处理的问题

- Patchright 的隔离执行上下文不能按 Playwright 的方式读取页面 window 业务变量；示例和跨后端测试改为 DOM 回执属性，文档明确差异。
- Windows UIA 窗口标题更新存在延迟；定位增加有界等待，避免后续动作因标题尚未传播而失败。
- 输入追加显式移动到末尾；鼠标抬起在 finally 中执行；清理单个资源失败时仍继续释放浏览器引擎和锁。
- 提交动作与业务确认分开，确认超时不得触发第二次提交；人工继续绑定具体等待 ID，旧请求不能继续下一次等待。

## 尚未验证及后续范围

- 没有进行无公网、无缓存、干净机器的完整安装/升级/回滚，也没有全进程外联抓取。本地示例限制页面请求到自己的回环服务，不代表浏览器后台或操作系统零外联。
- Windows 系统输入只验证当前桌面；不同 DPI、多显示器、远程桌面、锁屏及自定义浏览器需要现场验证。未实现真实 IME 候选与 composition 流程。
- 本次没有测试真实客户站点或反爬通过率，也没有复制私人仓库的业务代码、账号或定位器。随机轨迹和可选后端不是隐身或反检测保证。
- GitHub Actions 已加入双后端本地浏览器测试配置；本文的通过结果来自本机，不将尚未核验的托管 CI 结果计为通过。
- M3 的多场景独立 AI 制作评测、M4 完整离线交付与客户试点、M5 稳定兼容策略仍未完成。

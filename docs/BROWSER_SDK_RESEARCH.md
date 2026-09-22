# 浏览器自动化选型与 SDK 设计

调研日期：2026-09-22。状态：调研与设计稿，尚未实现或实测下述浏览器 SDK。当前运行契约仍以 [FLOW_SPEC.md](FLOW_SPEC.md) 为准，v0.2 只支持标准库与现有 `awm.sdk`。

## 已确认的要求与选型结论

核心产品定位已进一步明确：完全离线运行，适配内网和涉密环境的本地部署需求；开发者只需基础 Python、简单 Playwright 与 SDK。详见 [离线部署要求](OFFLINE_DESIGN.md)。因此后端优先按离线可交付、稳定、易学来选择，反检测增强属于可选能力。完整断网交付和目标环境验收尚未完成。

平台、通用 SDK、流程规范和 AI 制作指导开源；商业收入来自独立流程包的定制、适配与维护。用户已确认同时支持浏览器内模拟和系统鼠标键盘输入，以浏览器内模拟为默认。点击需要曲线移动、悬停与左键动作；输入先点击聚焦，再逐字输入。

建议 **Playwright 为标准后端，Patchright 为可选 Chromium 后端**，共用动作接口和回归用例。Windows 桌面输入独立适配，优先研究 pywinauto / Win32；它不是另一个浏览器引擎。以下推荐是根据官方能力与许可证作出的工程判断，不是反爬通过率排名。

| 候选 | 官方能力与限制 | 对本项目的判断 |
| --- | --- | --- |
| [Playwright](https://playwright.dev/python/docs/actionability) | 内置动作可执行性等待，提供定位器、鼠标、键盘和浏览器上下文；[Apache-2.0](https://github.com/microsoft/playwright-python/blob/main/LICENSE) | 标准后端，先建立稳定性基线，不宣传为隐身工具 |
| [Patchright](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright) / [Python 包](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright-python) | 修改部分 Playwright 可检测特征；仅补丁支持 Chromium；Apache-2.0；官方说明存在兼容性例外、console 功能限制及上游变化后的修复滞后 | 可选增强后端；锁定版本组合，执行相同回归，不直接采信“不可检测”的宣传 |
| [Selenium](https://www.selenium.dev/documentation/selenium_manager/) | 当前 Selenium Manager 已能管理驱动及相关浏览器资源；旧脚本的 3.141.0 不能代表当前能力 | 保留旧流程迁移价值；新接口优先围绕 Playwright 设计 |
| [DrissionPage](https://github.com/g1879/DrissionPage) | 结合浏览器和 HTTP 会话；[当前仓库许可证](https://raw.githubusercontent.com/g1879/DrissionPage/master/LICENSE)要求商业用途取得版权方授权 | 付费流程包有直接的授权成本，暂不作为默认分发依赖；旧版也须核对对应版本条款 |
| [nodriver](https://github.com/ultrafunkamsterdam/nodriver) | Chromium 系直接控制，异步 API，无 Selenium / chromedriver 依赖；仓库标示 AGPL-3.0 | 可研究；AGPL 不等于禁止收费，但商业包组合与分发义务尚需明确，暂不默认引入 |
| [Camoufox](https://github.com/daijro/camoufox) | Firefox 分支、Playwright 兼容 Python 接口、鼠标轨迹；官方提示生产稳定性有限，并说明此前维护间断造成影响 | 预留后端；Python 包 MIT 元数据不能代表整个浏览器发行物，仓库标示 MPL-2.0 |

发布新鲜度来自 PyPI JSON 现场查询，见 [元数据快照](research/browser-packages-2026-09-22.json)。Python 包上传时间不等同于浏览器内核更新时间，也不证明在本项目 Python 3.14 环境可用。

| Python 包 | 调研时当前版本 | 上传日期（UTC） |
| --- | --- | --- |
| [selenium](https://pypi.org/project/selenium/) | 4.49.0 | 2026-09-09 |
| [playwright](https://pypi.org/project/playwright/) | 1.63.0 | 2026-09-15 |
| [patchright](https://pypi.org/project/patchright/) | 1.63.0 | 2026-09-20 |
| [nodriver](https://pypi.org/project/nodriver/) | 0.50.3 | 2026-05-13 |
| [DrissionPage](https://pypi.org/project/DrissionPage/) | 4.1.1.4 | 2026-05-27 |
| [camoufox](https://pypi.org/project/camoufox/) | 0.5.6 | 2026-09-06 |

## 反检测与交互模拟

检测可能综合浏览器、请求、会话及行为信号。[Cloudflare 的评分说明](https://developers.cloudflare.com/bots/concepts/bot-score/)展示了多种检测引擎的组合。随机轨迹只改变交互行为，不能修复所有浏览器特征或服务端判断。新发布、没有 WebDriver、系统输入，都不能单独证明更难被检测。

分别评估动作正确性、流程可靠性和指定环境的检测结果。本地填表成功不能记为通过真实网站反爬；OS 生成的输入也不等于物理硬件证明。产品使用“可配置交互模拟”“可选浏览器兼容后端”等可验证描述，不承诺“100% 反反爬”。验证页面保留人工处理衔接，继续前重新检查状态。

## 架构与双模式

```text
独立流程包：页面对象、站点定位器、业务步骤、成功判据
                         ↓
公共 SDK：会话 / 定位 / 点击 / 输入 / 窗口 / 步骤 / 结果
                         ↓
交互规划器：目标落点、运动曲线、时间间隔、取消检查
                 ↙                       ↘
浏览器输入适配器（默认）          Windows 桌面输入适配器
Playwright / Patchright          窗口定位 + pywinauto / Win32
                 ↘                       ↙
平台：环境安装、版本锁定、配置、记录、资源清理
```

作者接口与现有同步 `run(ctx, config)` 相容；异步后端未来由适配层明确执行模型。保留原生页面访问出口，但使用原生 API 的流程包须声明后端依赖，不能承诺原生代码跨后端通用。

| 属性 | 浏览器内模拟（默认） | Windows 系统输入（可选） |
| --- | --- | --- |
| 输入路径 | 浏览器接口发送鼠标/键盘事件 | OS 鼠标/键盘输入 |
| 系统鼠标 | 不移动桌面光标 | 占用桌面光标与键盘焦点 |
| 坐标 | 视口 CSS 像素 | 桌面坐标，涉及 DPI、窗口边框、工具栏、多屏 |
| 条件 | 不依赖桌面鼠标位置；后台标签页行为仍需实测 | 目标窗口可见、前台，桌面会话可用 |
| 互斥 | 单个页面动作串行 | 整个桌面会话互斥 |
| 失败 | 返回定位/可操作性/页面变化错误 | 失焦、窗口移动、坐标失效时停止动作并重新校准 |

模式必须显式选择，浏览器动作失败不得偷偷改用系统鼠标。首版不承诺锁屏、最小化窗口或所有远程桌面状态可用；[SendInput 官方说明](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendinput)还列出了权限级别等限制。用户打断与取消都要释放已按下的键和按钮。

## 会话与环境

- 支持新建临时会话、平台专用持久化登录目录、连接已有调试会话；用户数据目录独占，不装入流程 ZIP。
- 平台创建的浏览器由平台清理；外部接管只释放连接和明确归属本次流程的资源，各后端分别验证关闭行为。
- 登录成功由页面状态确认，不使用独立 HTTP 请求的 200 状态代替浏览器会话检查。
- [Chrome 136 起](https://developer.chrome.com/blog/remote-debugging-port)，普通 Chrome 对默认数据目录的远程调试开关有限制，启动要使用独立 `user-data-dir`，不能照搬旧脚本仅加端口的命令。
- [Playwright CDP 连接](https://playwright.dev/python/docs/api/class-browsertype#browser-type-connect-over-cdp)仅用于 Chromium，官方提示能力低于原生连接。接管模式单独验收。
- M2 的 `dependencies=[]` 和 `browser` 声明没有提供浏览器环境。新增平台管理的可选运行环境：开发侧预备依赖，交付匹配的 Python 包、驱动资源与浏览器二进制；目标机器只使用本地材料，安装与运行均不触发公网下载。组件缺失时给出本地诊断。

## 点击契约（待实现）

拟议接口：`actions.click(target, profile="natural", timeout_ms=...)`。本文 `actions` 及其方法均为设计，不能复制到 v0.2 流程包运行。

1. 唯一定位目标，等待可见、稳定、启用且能接收事件，滚动到可操作区域。
2. 在目标与视口相交的有效区域选落点，保留边距并检查遮挡。
3. 从当前指针位置生成受约束曲线；持续时间及采样数随距离调整，速度渐变。允许指定随机种子重现故障。
4. 逐点移动并检查取消；悬停后再次检查边界及命中区域。目标移动时重新定位，受总超时限制。
5. 左键按下、短暂停留、释放；异常也确保释放按钮。
6. 检查流程定义的后置条件，如弹窗、页面状态或成功回执。

[Playwright Mouse](https://playwright.dev/python/docs/api/class-mouse)的 `steps` 是插值移动，不能当作完整随机曲线算法；原始 mouse 动作也不继承定位器点击的全部检查。SDK 需补齐目标校验，以[原生等待规则](https://playwright.dev/python/docs/actionability)作为基线。

轨迹规划器只产生坐标和时间，适配器发送事件，目标校验器保证命中。不要在曲线算法中绑定 WebElement 或窗口句柄。[HumanCursor](https://github.com/riflosnake/HumanCursor)可作为参考候选，若引入则另行核对锁定版本的授权与依赖，不直接当作平台核心。

默认不模拟误点、随机双击。提交动作发送后超时，结果记为待确认；先核实后置状态，不自动补点。

## 输入契约（待实现）

拟议接口：`actions.type_text(target, value, clear=True, profile="natural", sensitive=False)`。

顺序：等待可编辑 → 使用点击过程聚焦 → 确认焦点 → 按配置全选/删除 → 逐字符或字素输入 → 字符/词组间等待 → 核对最终内容。中途失焦则终止，不把剩余内容写到别处；取消时释放修饰键，不自动发送 Enter。

行为策略：`direct` 使用后端常规点击/填充，便于测试与速度优先场景；`natural` 使用轨迹、悬停和按键间隔。两者都做正确性检查。初版分布只是可调工程参数，不能称为经过验证的人类行为模型。

中文单独处理：

- 英数等可发送逐键事件；中文逐字提交不等于拼音输入法候选选择及 composition 过程。
- [Playwright Keyboard](https://playwright.dev/python/docs/api/class-keyboard)明确说明非美式键盘字符的事件存在差异，`insert_text` 只发 input 事件。
- Windows 可研究 [pywinauto Unicode 输入](https://pywinauto.readthedocs.io/en/latest/code/pywinauto.keyboard.html)；VK_PACKET 同样不等于真实输入法。依赖 composition 的页面需要专门适配和测试。
- 默认不用剪贴板，不注入随机错字；敏感字段不记录明文、按键内容或未遮盖截图。

## 平台与 AI 制作规范衔接

增加运行环境需求、桌面输入能力和会话配置时，同步 Schema、校验器、执行器、CLI、前端及文档，保持旧标准库包兼容。设计阶段不提前放宽正式 Schema 接受尚不能执行的配置。

人工登录/验证需要新增可取消的等待与继续协议，当前状态机尚不支持。浏览器及桌面操作遵循任务取消和进程清理规则。区分“动作前失败可重试”“动作已发送结果未知”“已确认失败”，避免整段无条件重试。

接口实际实现并测试后再更新 AI Skill：优先语义定位器和页面对象、调用公共动作、声明原生后端依赖；先本地页面验证，再单独记录真实站点结果。Skill 不引用此设计稿作为已存在 API。

## 实施顺序与验收

| 阶段 | 交付 | 验收标准 |
| --- | --- | --- |
| M2.1-A | 本地 Playwright 环境、独立登录目录、会话生命周期、离线预检 | 使用预备的离线材料安装；缺失组件不下载；目录互斥；退出释放自建资源；接管行为独立验证 |
| M2.1-B | 公共动作、轨迹规划、可取消等待、结果判据；Patchright 适配 | 同一本地测试页验证两后端的正确性，记录确切版本；不因切换后端重复提交 |
| M2.1-C | Windows 输入、窗口坐标映射、DPI、桌面互斥和失焦处理 | 专用本地窗口验证 100%/125%/150% 缩放、跨屏或明确限制、窗口移动、用户打断、中文；停止后无按键残留 |
| M2.1-D | 平台环境设置、包规范、可取消人工衔接、浏览器示例和文档 | 实际导入包完成配置、运行、取消及回执下载；旧包仍可执行 |
| M3 | Skill 与双模式作者指南、制作评测 | AI 使用真实已发布接口制作包并通过本地页面验收；用户站点适配另行记录 |

公共测试页覆盖：延迟出现、遮挡、悬停移动、禁用/只读、iframe、新标签页、输入失焦、中文和 emoji、输入取消、点击后超时及重复提交。检查事件顺序、最终值、提交次数和资源退出。

反检测评估独立记录后端/Python/浏览器版本、输入模式、环境、会话条件、挑战结果、重试次数和功能成功率。完成受控 A/B 实测前，不提供“比 Selenium 隐蔽多少”的数字。

## 本次验证边界

已完成官方资料与许可证核查、PyPI 查询、双模式需求确认、行为设计和路线图更新。未安装或实测候选库，未实现新 SDK，未验证真实站点反检测效果，未运行私有业务流程。公开文档不包含私有定位器、业务站点或凭据。

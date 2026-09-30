---
name: automaticworker-flow-author
description: Create, modify, validate and package offline AutoMaticWorker workflows using implemented manifest 1.0/1.1, local browser environments and the SDK. Use for workflow authoring or repair; not for modifying the platform itself.
metadata:
  short-description: 制作和验证 AutoMaticWorker 流程包（Alpha）
---

# AutoMaticWorker 流程制作

本 Skill 随项目分发，适用于平台 0.2.1 和规范 1.0 / 1.1。需要能读取本地仓库并执行 Python 的 AI 开发环境。它依赖本仓库资源，不是独立安装包。

平台以完全离线与内网部署为核心。按 [离线部署要求](../../docs/OFFLINE_DESIGN.md) 制作：运行依赖与资料在本地准备，业务连接限定为目标部署环境指定的资源，不引入公网下载、云模型、在线激活或外部日志上报。缺少本地组件时报告缺项，不在隔离目标机上尝试联网补装。AI 是可选开发工具，不能成为流程执行依赖。

## 先读取真实契约

从本文件向上两级定位仓库根目录。先阅读 [制作说明](../../docs/AUTHORING.md) 与 [流程规范](../../docs/FLOW_SPEC.md)，字段以 [Schema](../../schemas/manifest.schema.json) 为准。需要示例时选择 [报告流程](../../examples/report/flow.py) 或 [本地网页流程](../../examples/local-web/flow.py)，不要同时加载无关资源。

使用仓库虚拟环境中的 Python；如果环境尚未建立，按 [快速开始](../../docs/QUICKSTART.md) 及部署环境约束准备依赖，注意其中的包源安装命令不是离线安装方案。所有 `python -m awm` 命令从仓库根目录运行。

## 制作与修改

1. 从用户请求提取目标、输入、输出、环境与验收条件。只补问影响执行的缺失信息；能用合成样例推进时先实现可验证部分。
2. 为新流程选择有效且独特的 ID，运行 `python -m awm init <新目录> --id <id>` 创建报告模板；浏览器场景加 `--template browser-form`。已有流程先读清单和代码，保留既有需求与兼容接口。
3. 修改清单与 `flow.py`。使用标准库、已实现 SDK，以及清单声明的平台浏览器后端；`dependencies` 必须为空。浏览器场景先读 [浏览器 SDK](../../docs/BROWSER_SDK.md)，采用规范 1.1，声明接受的后端和输入模式。不要猜测函数或隐式安装依赖。
4. 实现同步 `run(ctx, config)`，业务语义错误给出可定位消息。通过 `ctx.output_path` 创建输出，以 `ctx.result` 返回摘要和文件列表。循环检查取消，网络调用设置超时，在 `finally` 释放资源。
5. 按真实行为声明能力。需要试运行时，实现 `ctx.dry_run` 对应的模拟或预览；无法做到时声明 `unsupported`。不得仅加标记却仍执行真实外部写入。
6. 用合成输入、本地模拟或用户已授权的测试资源检查结果。制作代码与真实系统执行是不同操作，遵循用户给定的执行范围；涉及重复提交时明确停止条件，不自行增加无限重试。

参数应能由通用界面表达。秘密值标记为 `secret`，不设置默认值、不写入日志、样例、结果文件或 ZIP。真实账号和客户数据不作为模板资源。

浏览器流程复用 `with ctx.browser()` 和 `session.actions()`，目标使用原生 Playwright Locator，业务选择器放在流程包。浏览器内输入为默认；系统输入必须由环境显式选择，不能自动回退占用鼠标。人工登录用 `ctx.wait_for_user`，继续后验证页面。提交动作提供结果判据，捕获 OutcomeUnknown 后先核对业务状态，不直接重试点击。跨后端优先读取 DOM，不依赖 window 业务变量；Patchright 的隔离上下文与 Playwright 不完全相同。

## 验证与交付

依次进行静态检查、行为验证和打包检查：

```text
python -m awm validate <流程目录>
python -m awm run <流程目录> --config <合成配置.json> --dry-run --data-dir <专用测试目录>
python -m awm pack <流程目录> <目录外的交付.zip>
python -m awm validate <交付.zip>
```

没有配置时省略 `--config`；不支持试运行时，在明确可执行的本地测试场景中省略 `--dry-run`，不要通过更改清单伪造支持。测试目录不能使用客户桌面的实际数据目录，因为 CLI 会更新其中的同 ID 包。

检查生成文件的业务内容是否符合需求，并测试至少一个与该流程相关的错误输入。读取错误日志定位失败后再修复，不能把 Schema 通过当作业务验证完成。更新包时提升三段数字版本，说明参数变更和已保存配置的影响。

打包前审阅实际文件清单，排除凭据、客户数据、虚拟环境和运行产物。打包器不是敏感数据检测器。

交付说明列出所需本地组件和内网服务；只有实际执行过断网测试才声明通过。浏览器流程先通过 environment 命令预检，再用本地测试页面验证点击、中文输入、取消及提交次数。接口以 BROWSER_SDK.md 为准，历史调研稿不作为运行契约。需要人工等待的 CLI 验证添加 --interactive。

交付 ZIP、简短使用说明、兼容版本、实际执行的验证结果与未验证项。没有执行的测试直接说明未执行；需要真实站点才能验证的部分，不声称已经可用。

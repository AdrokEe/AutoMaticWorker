# AutoMaticWorker

**完全离线的自动化平台与 SDK，让内网流程开发更简单。**

AutoMaticWorker 以完全断网运行、内网部署和数据本地留存为核心，面向包括涉密环境在内的隔离部署需求。平台与通用 SDK 开源，商业服务为付费定制流程包、部署适配和维护。

开发者掌握基础 Python 和简单的 Playwright 页面操作，配合 SDK 即可快速制作流程；使用者通过导入、配置和运行完成重复工作。浏览器环境、交互操作、日志、取消和结果交付由平台与 SDK 统一管理。这是产品目标，浏览器 SDK 正在 M2.1 规划中。

当前版本：**0.2.0 · M2 开发版**。已实现本地 ZIP 导入与升级、自动参数表单、独立进程执行、试运行、取消、日志、历史与结果下载。

完整离线安装包、浏览器 SDK 和隔离环境专项验收尚未交付；当前不声明已取得涉密环境认证。目标与验收条件见 [完全离线与内网部署要求](docs/OFFLINE_DESIGN.md)。

## 核心价值

- **离线优先**：安装、运行与升级均以不依赖公网为目标，不依赖云账号、在线激活或云模型。
- **数据留在本地**：配置、流程、日志与结果在部署环境内处理；内网业务只连接指定系统。
- **开发门槛低**：简单 Playwright + 通用 SDK + 标准流程包，复用平台能力，聚焦业务步骤。
- **AI 可选**：公开 Skill 辅助制作，手工开发同样可用；隔离环境可搭配允许使用的本地模型。

## 开始使用

参阅 [安装与首次体验](docs/QUICKSTART.md)。以下是开发环境的源码安装方式，默认从包源获取依赖，不能当作完整离线安装方案：

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-desktop.txt
npm ci --prefix vue_frontend
npm run build --prefix vue_frontend
.venv\Scripts\python.exe main.py
```

默认只启动本地服务和桌面窗口。工作台内可添加“合成数据报告”和“本地网页表单演示”，无需业务账号。Windows 免开发环境安装包属于 M4。

## 制作流程

- [流程包规范 1.0](docs/FLOW_SPEC.md) 与 [机器可读 Schema](schemas/manifest.schema.json)
- [开发者制作指南](docs/AUTHORING.md)
- [AI 流程制作 Skill Alpha](skills/automaticworker-flow-author/SKILL.md)
- [开发路线图](ROADMAP.md) 与 [M2 验收报告](docs/M2_ACCEPTANCE.md)
- [浏览器 SDK 选型与双模式交互设计](docs/BROWSER_SDK_RESEARCH.md)（M2.1 规划，尚未实现）

制作工具：`python -m awm init / validate / run / pack`。本版仅支持 Python 标准库与平台 SDK，不自动安装外部依赖。流程包会执行本机代码，应使用可信来源；试运行语义由流程作者实现。

## 项目与商业边界

开源内容包含通用平台、自动化 SDK、流程包规范、制作 Skill 和公开示例。商业服务是付费制作流程包、部署适配和维护。具体业务流程独立交付，见 [公开范围说明](docs/PUBLIC_SCOPE.md)。

技术栈：Vue 3 + TypeScript + Flask + Pywebview；运行记录保存在本机，项目沿用 MIT 许可证。

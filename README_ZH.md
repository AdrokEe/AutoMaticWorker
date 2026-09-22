# AutoMaticWorker

支持可扩展流程包的开源自动化桌面平台。开发者或 AI 制作流程包，使用者通过导入、配置和运行完成重复工作。

当前版本：**0.2.0 · M2 开发版**。已实现本地 ZIP 导入与升级、自动参数表单、独立进程执行、试运行、取消、日志、历史与结果下载。

## 开始使用

参阅 [安装与首次体验](docs/QUICKSTART.md)。本机源码启动：

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

制作工具：`python -m awm init / validate / run / pack`。本版仅支持 Python 标准库与平台 SDK，不自动安装外部依赖。流程包会执行本机代码，应使用可信来源；试运行语义由流程作者实现。

## 项目与商业边界

开源内容包含通用平台、流程包规范、制作 Skill 和公开示例。商业服务是付费制作流程包、部署适配和维护。具体业务流程独立交付，见 [公开范围说明](docs/PUBLIC_SCOPE.md)。

技术栈：Vue 3 + TypeScript + Flask + Pywebview；运行记录保存在本机，项目沿用 MIT 许可证。

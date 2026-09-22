# 开发与使用快速开始

当前是 M2 开发版，提供源码启动与桌面窗口；免开发环境的 Windows 安装包安排在 M4。

## 环境与安装

本次验证环境：Windows、Python 3.14.2、Node.js 24.12.0、npm 11.6.2。桌面模式使用 Windows WebView2。其他 Python 版本和操作系统尚未完成桌面验收。

在仓库根目录打开 PowerShell：

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-desktop.txt
npm ci --prefix vue_frontend
npm run build --prefix vue_frontend
.venv\Scripts\python.exe main.py
```

窗口从同一进程管理的本地 HTTP 服务加载构建好的页面，不需要另行启动 Vite。默认自动选择空闲端口，仅监听 `127.0.0.1`。关闭窗口会取消正在运行的任务并停止本地服务。

安装与构建完成后，也可以双击根目录的 `Start-AutoMaticWorker.cmd` 启动。需要完全复现本次 Windows 开发依赖时，使用 `pip install -r requirements-lock-windows.txt`；该锁定文件包含测试和桌面依赖。

只使用浏览器时：

```powershell
.venv\Scripts\python.exe main.py --browser --port 5000
```

在浏览器打开终端显示的本地地址，使用 Ctrl+C 关闭服务。可用 `--data-dir output/my-workspace` 指定测试工作区；同一数据目录不允许两个应用实例同时运行。

## 首次体验

1. 在工作台点击“添加体验流程”，加入两个公开示例。
2. 选择“合成数据报告”，填写名称、条数和币种。
3. 点击“试运行”，观察进度和日志，下载 JSON 与 CSV 结果。
4. 回到工作台，点击“开始运行”；在“运行记录”查看两次执行。
5. 调高条数或每条等待时间，运行后点击“取消运行”，验证任务结束。

默认报告生成 5 条合成明细，合计 180 CNY。第二个示例会启动本地模拟网页、提交演示姓名、提取回执并关闭服务，不访问实际业务网站。

## 导入与配置

- 点击“导入流程包”，选择 ZIP，确认来源后导入。
- 更新同 ID 包时勾选更新选项，版本必须更高；更新会清空旧配置。
- 配置页由包参数声明自动生成，支持文字、数字、开关、枚举、文件和目录。
- 文件选择会将输入复制到应用的数据目录；目录选择只在桌面模式可用，浏览器模式可填写路径。
- “保存配置”只保存非敏感值；敏感字段需要每次运行重新填写。
- 卸载包保留历史记录和成功结果；失败任务不会自动重试。

默认数据目录为 `%LOCALAPPDATA%\AutoMaticWorker`。配置、上传的输入、历史和输出都保留在本机，目前没有自动清理功能。应用关闭后可自行备份或清理。

## 开发验证

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest -q
npm run build --prefix vue_frontend
```

日常 UI 开发可先运行 `main.py --browser --port 5000`，再在 `vue_frontend` 运行 `npm run dev`；Vite 代理 `/api`。交付验收使用构建产物，避免把开发服务器依赖带入桌面启动。

## 常见问题

- 页面提示尚未构建：运行 `npm ci` 和 `npm run build`。
- 页面显示服务断开：检查启动终端，恢复服务后刷新页面以重新获取会话。
- 流程包报依赖不支持：本版仅支持标准库和 SDK，不自动安装第三方包。
- 配置检查失败：根据字段提示检查类型、范围和本机路径；业务输入检查错误看运行日志。
- 数据目录已被占用：关闭该目录的另一个应用，或给测试实例指定独立目录。

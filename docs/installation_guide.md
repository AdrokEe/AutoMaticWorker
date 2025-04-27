# AutoMaticWorker 安装指南

本文档将指导您完成 AutoMaticWorker 的安装和初始配置过程。

## 系统要求

- 操作系统：Windows 10+、macOS 10.14+、Ubuntu 18.04+
- Python 3.8 或更高版本
- Node.js 14.0 或更高版本
- 至少 4GB RAM
- 500MB 可用磁盘空间

## 安装步骤

### 1. 获取项目代码

有两种方式获取项目代码：

**方式一：使用 Git 克隆**

```bash
git clone <项目仓库URL>
cd AutoMaticWorker
```

**方式二：直接下载**

1. 访问项目主页：`<项目URL>`
2. 点击"Download ZIP"按钮
3. 解压下载的ZIP文件到本地目录

### 2. 安装 Python 依赖

在项目根目录下，运行以下命令安装所需的 Python 依赖：

```bash
# 建议使用虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 构建前端（仅需运行一次）

AutoMaticWorker 的前端使用 Vue.js 构建。如果提供了预构建的前端文件，可以跳过此步骤。

```bash
cd vue_frontend
npm install
npm run build
cd ..
```

### 4. 配置数据库

AutoMaticWorker 默认使用 SQLite 数据库，无需额外配置。如果需要使用其他数据库，请修改 `config.py` 文件中的数据库配置。

## 启动应用

### 开发模式

在开发模式下，前端和后端分别运行：

```bash
# 终端1：启动前端
cd vue_frontend
npm run dev

# 终端2：启动后端
# 确保在项目根目录下
python main.py
```

### 生产模式

在生产模式下，后端会自动加载构建好的前端文件：

```bash
python main.py
```

启动后，应用会自动打开浏览器窗口。如果没有自动打开，请手动访问：
- http://localhost:5000/flow-editor/

## 验证安装

要验证安装是否成功，可以执行以下步骤：

1. 打开浏览器，访问 http://localhost:5000/flow-editor/
2. 应该能看到流程编辑器的主界面
3. 点击"创建新流程"按钮，创建一个测试流程
4. 添加几个节点并保存流程
5. 尝试导出为 Python 脚本并运行

## 常见安装问题

### 依赖安装失败

**问题**：安装 Python 依赖时出现错误

**解决方案**：
- 确保 Python 版本正确 (`python --version`)
- 尝试更新 pip：`pip install --upgrade pip`
- 对于 Windows 用户，某些库可能需要 Visual C++ 编译器，可以安装 [Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

### 前端构建失败

**问题**：前端构建时报错

**解决方案**：
- 确保 Node.js 版本正确 (`node --version`)
- 删除 `vue_frontend/node_modules` 目录，重新运行 `npm install`
- 确保 npm 版本最新：`npm install -g npm`

### 找不到模块错误

**问题**：运行时出现 "ModuleNotFoundError"

**解决方案**：
- 确保虚拟环境已激活
- 重新运行 `pip install -r requirements.txt`

### 端口被占用

**问题**：启动时提示端口被占用

**解决方案**：
- 修改 `config.py` 中的端口配置
- 或者在命令行启动时指定端口：`python main.py --port 5001`

## 升级指南

更新到新版本的步骤：

1. 备份您的数据和自定义配置
2. 拉取或下载最新代码
3. 安装最新依赖：`pip install -r requirements.txt`
4. 重新构建前端：`cd vue_frontend && npm install && npm run build`
5. 运行数据库迁移：`python migrate.py`（如果有）
6. 重启应用

## 附录

### 文件目录结构

```
AutoMaticWorker/
├── main.py                 # 主入口文件
├── requirements.txt        # Python 依赖
├── config.py               # 配置文件
├── models/                 # 数据模型
├── routes/                 # 后端路由
├── static/                 # 静态资源
├── templates/              # HTML 模板
├── vue_frontend/           # Vue.js 前端代码
│   ├── src/                # 源代码
│   ├── public/             # 公共资源
│   └── package.json        # npm 配置
└── docs/                   # 文档
    ├── user_manual.md      # 用户手册
    └── api_reference.md    # API 参考
```

### 环境变量

AutoMaticWorker 支持以下环境变量进行配置：

- `AMW_DB_URI`：数据库连接字符串
- `AMW_SECRET_KEY`：应用密钥
- `AMW_DEBUG`：是否启用调试模式（true/false）
- `AMW_PORT`：启动端口
- `AMW_HOST`：绑定主机

这些变量可以在系统环境变量中设置，或者在项目根目录创建 `.env` 文件。 
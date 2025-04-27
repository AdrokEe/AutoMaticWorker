# AutoMaticWorker 开发者文档

## 项目概述

AutoMaticWorker是一个通用的Web流程自动化脚本管理和运行工具。它允许用户通过可视化界面创建、编辑和管理自动化工作流，并将其导出为可执行的Python脚本。

技术栈：
- 后端：Flask (Python)
- 前端：Vue.js
- 桌面集成：PyWebview

## 项目结构

```
AutoMaticWorker/
│
├── flask_backend/           # Flask后端应用
│   ├── demo.py              # 主Flask应用入口点
│   └── ...
│
├── flow_editor/             # 流程编辑器模块
│   ├── models/              # 数据模型
│   │   ├── __init__.py
│   │   └── flow.py          # 流程、节点、连接模型
│   ├── routes.py            # API路由
│   ├── templates/           # HTML模板
│   │   └── flow_editor/     # 流程编辑器模板
│   │       ├── index.html   # 流程列表页面
│   │       └── editor.html  # 流程编辑页面
│   └── static/              # 静态资源
│
├── process/                 # 流程存储和执行
│   └── flows/               # 流程JSON文件存储
│
├── vue_frontend/            # Vue前端应用
│   ├── src/                 # 源代码
│   └── ...                  # Vue配置文件
│
├── main.py                  # 应用主入口
├── requirements.txt         # 依赖列表
├── README.md                # 英文说明文档
└── README_ZH.md             # 中文说明文档
```

## 核心模块说明

### 1. Flask后端 (flask_backend)

Flask后端负责提供API接口，包括流程管理、执行流程和数据服务。

主要文件:
- `demo.py` - Flask应用主入口点，注册Blueprint和路由

### 2. 流程编辑器 (flow_editor)

流程编辑器模块提供可视化流程设计功能。

主要组件:
- **模型 (models)**: 定义流程、节点和连接的数据结构
  - `flow.py` - 定义Flow、FlowNode和FlowConnection类
- **路由 (routes.py)**: 提供流程CRUD的API接口
- **模板 (templates)**: 包含流程编辑器的HTML页面
  - `index.html` - 流程列表页面
  - `editor.html` - 流程编辑页面

#### 2.1 流程数据模型

流程数据模型由三个主要类组成：

**Flow (流程)**:
- 属性: id, name, description, nodes, connections, created_at, updated_at
- 方法: 
  - `save()`: 保存流程到JSON文件
  - `get_flow_by_id()`: 通过ID获取流程
  - `get_all_flows()`: 获取所有流程
  - `create_flow()`: 创建新流程
  - `update_flow()`: 更新流程
  - `delete_flow()`: 删除流程
  - `export_to_script()`: 导出为Python脚本

**FlowNode (节点)**:
- 属性: id, type, position, data
- 节点类型: start, action, condition, end

**FlowConnection (连接)**:
- 属性: id, source_id, target_id, label, condition

### 3. 前端 (vue_frontend)

前端使用Vue.js构建，提供用户界面。

### 4. 主入口 (main.py)

`main.py`是应用的主入口点，负责:
- 启动Flask后端
- 创建PyWebview窗口
- 集成Flask和Vue前端

## 开发指南

### 环境设置

1. 克隆仓库:
   ```
   git clone <仓库URL>
   cd AutoMaticWorker
   ```

2. 创建虚拟环境:
   ```
   python -m venv venv
   venv\Scripts\activate  # Windows
   source venv/bin/activate  # Linux/Mac
   ```

3. 安装依赖:
   ```
   pip install -r requirements.txt
   ```

4. 安装前端依赖:
   ```
   cd vue_frontend
   npm install
   ```

### 运行开发服务器

1. 启动Vue开发服务器:
   ```
   cd vue_frontend
   npm run dev
   ```

2. 启动应用:
   ```
   cd AutoMaticWorker
   python main.py
   ```

### 添加新功能

#### 添加新的节点类型

1. 在`flow_editor/models/flow.py`中更新`FlowNode`类
2. 在`flow_editor/templates/flow_editor/editor.html`中添加新节点类型的UI元素
3. 更新`export_to_script`方法以支持新节点类型的代码生成

#### 添加新的API端点

1. 在`flow_editor/routes.py`中添加新的路由函数
2. 实现相应的处理逻辑

### 测试

#### 手动测试流程

1. 创建新流程
2. 添加节点和连接
3. 保存流程
4. 导出为Python脚本并验证脚本内容

## API参考

### 流程编辑器API

| 端点 | 方法 | 描述 | 参数 | 返回 |
|------|------|------|------|------|
| `/flow-editor/flows` | GET | 获取所有流程 | 无 | 流程列表 |
| `/flow-editor/flows` | POST | 创建新流程 | name, description | 新流程详情 |
| `/flow-editor/flows/<flow_id>` | GET | 获取特定流程 | flow_id | 流程详情 |
| `/flow-editor/flows/<flow_id>` | PUT | 更新流程 | flow_id, nodes, connections | 更新后的流程 |
| `/flow-editor/flows/<flow_id>` | DELETE | 删除流程 | flow_id | 成功/失败状态 |
| `/flow-editor/flows/<flow_id>/export` | GET | 导出流程为Python脚本 | flow_id | 生成的脚本 |

#### 请求/响应示例

##### 获取所有流程

请求:
```
GET /flow-editor/flows
```

响应:
```json
[
  {
    "id": "a1b2c3d4",
    "name": "示例流程",
    "description": "这是一个示例流程",
    "created_at": "2023-01-01T12:00:00",
    "updated_at": "2023-01-02T12:00:00",
    "nodes_count": 4,
    "connections_count": 3
  }
]
```

##### 创建新流程

请求:
```
POST /flow-editor/flows
Content-Type: application/json

{
  "name": "新流程",
  "description": "流程描述"
}
```

响应:
```json
{
  "id": "e5f6g7h8",
  "name": "新流程",
  "description": "流程描述",
  "nodes": [...],
  "connections": [...],
  "created_at": "2023-02-01T12:00:00",
  "updated_at": "2023-02-01T12:00:00"
}
```

## 常见问题和解决方案

### 问题: 导入错误

**问题**: 运行`main.py`时出现模块导入错误。

**解决方案**: 
- 确保当前目录是项目根目录
- 检查Python路径是否包含项目目录
- 验证所有依赖是否正确安装

### 问题: 流程编辑器不显示

**问题**: 启动应用后，流程编辑器界面不显示。

**解决方案**:
- 确保Flask服务器正在运行（检查控制台输出）
- 验证URL是否正确（默认为`http://localhost:5000/flow-editor/`）
- 检查浏览器控制台是否有错误

## 贡献指南

1. Fork仓库
2. 创建功能分支 (`git checkout -b feature/your-feature`)
3. 提交更改 (`git commit -am 'Add some feature'`)
4. 推送到分支 (`git push origin feature/your-feature`)
5. 创建Pull Request

## 代码规范

- 使用PEP 8风格指南
- 添加文档字符串到所有函数和类
- 保持代码模块化和可测试
- 遵循单一职责原则 
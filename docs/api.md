# AutoMaticWorker API 文档

本文档详细说明了AutoMaticWorker应用程序提供的所有API端点。这些API允许开发者以编程方式与流程编辑器和流程执行系统交互。

## 基本信息

- **基础URL**: `http://localhost:5000`
- **内容类型**: 除非特别说明，所有请求和响应的内容类型均为`application/json`
- **认证**: 当前版本不需要认证

## 流程编辑器 API

流程编辑器API提供了创建、读取、更新和删除流程的功能，以及导出流程为Python脚本的能力。

### 获取所有流程

获取系统中所有可用的流程列表。

**请求**:
```
GET /flow-editor/flows
```

**响应**:
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
  },
  {
    "id": "e5f6g7h8",
    "name": "另一个流程",
    "description": "流程描述",
    "created_at": "2023-02-01T12:00:00",
    "updated_at": "2023-02-01T12:00:00",
    "nodes_count": 2,
    "connections_count": 1
  }
]
```

**状态码**:
- `200 OK`: 请求成功

### 创建新流程

创建一个新的流程。

**请求**:
```
POST /flow-editor/flows
Content-Type: application/json

{
  "name": "新流程",
  "description": "流程描述"
}
```

**参数**:
- `name` (必填): 流程名称
- `description` (可选): 流程描述

**响应**:
```json
{
  "id": "i9j0k1l2",
  "name": "新流程",
  "description": "流程描述",
  "nodes": [
    {
      "id": "node-start",
      "type": "start",
      "position": {"x": 100, "y": 150},
      "data": {"label": "开始"}
    },
    {
      "id": "node-end",
      "type": "end",
      "position": {"x": 500, "y": 150},
      "data": {"label": "结束"}
    }
  ],
  "connections": [],
  "created_at": "2023-03-01T12:00:00",
  "updated_at": "2023-03-01T12:00:00"
}
```

**状态码**:
- `201 Created`: 创建成功
- `400 Bad Request`: 请求参数不正确

### 获取单个流程

获取特定流程的详细信息。

**请求**:
```
GET /flow-editor/flows/{flow_id}
```

**路径参数**:
- `flow_id`: 流程的唯一标识符

**响应**:
```json
{
  "id": "a1b2c3d4",
  "name": "示例流程",
  "description": "这是一个示例流程",
  "nodes": [
    {
      "id": "node-1",
      "type": "start",
      "position": {"x": 100, "y": 150},
      "data": {"label": "开始"}
    },
    {
      "id": "node-2",
      "type": "action",
      "position": {"x": 300, "y": 150},
      "data": {
        "label": "执行动作",
        "code": "print('执行动作')\nresult = 42"
      }
    },
    {
      "id": "node-3",
      "type": "condition",
      "position": {"x": 500, "y": 150},
      "data": {
        "label": "条件判断",
        "condition": "result > 40"
      }
    },
    {
      "id": "node-4",
      "type": "end",
      "position": {"x": 700, "y": 150},
      "data": {"label": "结束"}
    }
  ],
  "connections": [
    {
      "id": "conn-1",
      "source": "node-1",
      "target": "node-2",
      "label": ""
    },
    {
      "id": "conn-2",
      "source": "node-2",
      "target": "node-3",
      "label": ""
    },
    {
      "id": "conn-3",
      "source": "node-3",
      "target": "node-4",
      "label": "是",
      "condition": "true"
    }
  ],
  "created_at": "2023-01-01T12:00:00",
  "updated_at": "2023-01-02T12:00:00"
}
```

**状态码**:
- `200 OK`: 请求成功
- `404 Not Found`: 指定的流程不存在

### 更新流程

更新现有流程的内容。

**请求**:
```
PUT /flow-editor/flows/{flow_id}
Content-Type: application/json

{
  "nodes": [...],
  "connections": [...]
}
```

**路径参数**:
- `flow_id`: 流程的唯一标识符

**请求体参数**:
- `name` (可选): 流程名称
- `description` (可选): 流程描述
- `nodes` (可选): 节点数组
- `connections` (可选): 连接数组

**响应**:
```json
{
  "id": "a1b2c3d4",
  "name": "示例流程",
  "description": "更新后的描述",
  "nodes": [...],
  "connections": [...],
  "created_at": "2023-01-01T12:00:00",
  "updated_at": "2023-03-15T12:00:00"
}
```

**状态码**:
- `200 OK`: 更新成功
- `404 Not Found`: 指定的流程不存在
- `400 Bad Request`: 请求参数不正确

### 删除流程

删除特定流程。

**请求**:
```
DELETE /flow-editor/flows/{flow_id}
```

**路径参数**:
- `flow_id`: 流程的唯一标识符

**响应**:
```json
{
  "success": true
}
```

**状态码**:
- `200 OK`: 删除成功
- `404 Not Found`: 指定的流程不存在

### 导出流程为Python脚本

将流程导出为可执行的Python脚本。

**请求**:
```
GET /flow-editor/flows/{flow_id}/export
```

**路径参数**:
- `flow_id`: 流程的唯一标识符

**响应**:
```json
{
  "script": "#!/usr/bin/env python\n# -*- coding: utf-8 -*-\n\n# 自动生成的流程脚本: 示例流程\n# 创建时间: 2023-03-15 12:00:00\n\nimport time\nimport logging\n\n..."
}
```

**状态码**:
- `200 OK`: 导出成功
- `404 Not Found`: 指定的流程不存在

## 数据模型

### Flow (流程)

流程是工作流的主要容器，包含节点和连接。

**属性**:
- `id`: 流程的唯一标识符 (UUID)
- `name`: 流程名称
- `description`: 流程描述
- `nodes`: 节点数组
- `connections`: 连接数组
- `created_at`: 创建时间 (ISO 8601 格式)
- `updated_at`: 最后更新时间 (ISO 8601 格式)

### FlowNode (节点)

节点代表流程中的一个步骤或决策点。

**属性**:
- `id`: 节点的唯一标识符
- `type`: 节点类型，可以是 `start`, `action`, `condition`, 或 `end`
- `position`: 节点在画布上的位置，包含 `x` 和 `y` 坐标
- `data`: 节点数据，包含以下字段:
  - `label`: 节点标签
  - `code` (仅用于 `action` 节点): 要执行的Python代码
  - `condition` (仅用于 `condition` 节点): 条件表达式

### FlowConnection (连接)

连接代表节点之间的关系和流程流向。

**属性**:
- `id`: 连接的唯一标识符
- `source`: 源节点ID
- `target`: 目标节点ID
- `label`: 连接标签
- `condition`: 条件表达式 (用于条件连接)

## 错误处理

API遵循标准HTTP状态码进行错误报告。常见错误包括:

- `400 Bad Request`: 请求参数不正确
- `404 Not Found`: 请求的资源不存在
- `500 Internal Server Error`: 服务器内部错误

错误响应的格式如下:

```json
{
  "error": "错误描述"
}
```

## 示例使用场景

### 场景1: 创建并导出简单流程

1. 创建新流程:
   ```
   POST /flow-editor/flows
   {
     "name": "简单流程",
     "description": "简单的示例流程"
   }
   ```

2. 添加动作节点:
   ```
   PUT /flow-editor/flows/{flow_id}
   {
     "nodes": [
       {
         "id": "node-start",
         "type": "start",
         "position": {"x": 100, "y": 150},
         "data": {"label": "开始"}
       },
       {
         "id": "node-action",
         "type": "action",
         "position": {"x": 300, "y": 150},
         "data": {
           "label": "打印消息",
           "code": "print('Hello, World!')"
         }
       },
       {
         "id": "node-end",
         "type": "end",
         "position": {"x": 500, "y": 150},
         "data": {"label": "结束"}
       }
     ],
     "connections": [
       {
         "id": "conn-1",
         "source": "node-start",
         "target": "node-action",
         "label": ""
       },
       {
         "id": "conn-2",
         "source": "node-action",
         "target": "node-end",
         "label": ""
       }
     ]
   }
   ```

3. 导出流程为Python脚本:
   ```
   GET /flow-editor/flows/{flow_id}/export
   ```

## 更多资源

- [开发者文档](developers.md): 完整的开发者指南
- [用户手册](user_manual.md): 用户操作指南 
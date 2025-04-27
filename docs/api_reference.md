# AutoMaticWorker API 参考

本文档提供了 AutoMaticWorker 的 API 接口说明，方便开发者集成和扩展功能。

## API 概述

AutoMaticWorker 提供了 RESTful API，允许您：

- 管理自动化流程
- 执行流程
- 查询执行结果和日志
- 管理节点类型和模板

所有 API 默认使用 JSON 格式进行数据交换。

## 认证

### 获取令牌

```
POST /api/auth/token
```

**请求参数**:

```json
{
  "username": "your_username",
  "password": "your_password"
}
```

**响应**:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

### 使用令牌

所有需要认证的 API 调用，需要在 HTTP 头中包含令牌：

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## 流程管理 API

### 获取所有流程

```
GET /api/flows
```

**响应**:

```json
{
  "flows": [
    {
      "id": 1,
      "name": "数据处理流程",
      "description": "处理CSV数据并发送邮件",
      "created_at": "2023-05-15T10:30:00Z",
      "updated_at": "2023-05-16T08:45:12Z"
    },
    ...
  ]
}
```

### 获取单个流程

```
GET /api/flows/{flow_id}
```

**响应**:

```json
{
  "id": 1,
  "name": "数据处理流程",
  "description": "处理CSV数据并发送邮件",
  "nodes": [
    {
      "id": "node1",
      "type": "start",
      "position": {"x": 100, "y": 100},
      "data": {...}
    },
    ...
  ],
  "edges": [
    {
      "id": "edge1",
      "source": "node1",
      "target": "node2",
      "type": "default"
    },
    ...
  ],
  "created_at": "2023-05-15T10:30:00Z",
  "updated_at": "2023-05-16T08:45:12Z"
}
```

### 创建流程

```
POST /api/flows
```

**请求参数**:

```json
{
  "name": "新流程",
  "description": "流程描述",
  "nodes": [...],
  "edges": [...]
}
```

**响应**:

```json
{
  "id": 2,
  "name": "新流程",
  "description": "流程描述",
  "created_at": "2023-06-01T14:22:36Z",
  "updated_at": "2023-06-01T14:22:36Z"
}
```

### 更新流程

```
PUT /api/flows/{flow_id}
```

**请求参数**:

```json
{
  "name": "更新后的流程名称",
  "description": "更新后的描述",
  "nodes": [...],
  "edges": [...]
}
```

**响应**:

```json
{
  "id": 1,
  "name": "更新后的流程名称",
  "description": "更新后的描述",
  "updated_at": "2023-06-02T09:15:42Z"
}
```

### 删除流程

```
DELETE /api/flows/{flow_id}
```

**响应**:

```json
{
  "message": "流程已成功删除"
}
```

### 导出流程为 Python 代码

```
GET /api/flows/{flow_id}/export
```

**查询参数**:
- `format`: 导出格式，可选值 `python` (默认) 或 `json`

**响应** (当 format=python):

```
Content-Type: application/octet-stream
Content-Disposition: attachment; filename="flow_1.py"

# 生成的 Python 代码
def main():
    # 流程逻辑
    ...
```

## 流程执行 API

### 执行流程

```
POST /api/flows/{flow_id}/execute
```

**请求参数** (可选):

```json
{
  "input_data": {
    "param1": "value1",
    "param2": 123
  },
  "async": true
}
```

**响应** (异步执行):

```json
{
  "execution_id": "exec_123456",
  "status": "queued",
  "message": "流程执行已加入队列"
}
```

**响应** (同步执行):

```json
{
  "execution_id": "exec_123456",
  "status": "completed",
  "result": {
    "output": {...},
    "execution_time": 1.45
  }
}
```

### 获取执行状态

```
GET /api/executions/{execution_id}
```

**响应**:

```json
{
  "execution_id": "exec_123456",
  "flow_id": 1,
  "status": "completed",
  "start_time": "2023-06-05T10:15:30Z",
  "end_time": "2023-06-05T10:15:32Z",
  "execution_time": 1.45,
  "result": {...},
  "logs": [...]
}
```

### 获取执行历史

```
GET /api/flows/{flow_id}/executions
```

**查询参数**:
- `page`: 页码 (默认 1)
- `per_page`: 每页结果数 (默认 20)
- `status`: 过滤特定状态 (可选)

**响应**:

```json
{
  "executions": [
    {
      "execution_id": "exec_123456",
      "status": "completed",
      "start_time": "2023-06-05T10:15:30Z",
      "end_time": "2023-06-05T10:15:32Z",
      "execution_time": 1.45
    },
    ...
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 45,
    "pages": 3
  }
}
```

## 节点类型 API

### 获取所有节点类型

```
GET /api/node-types
```

**响应**:

```json
{
  "node_types": [
    {
      "id": "http_request",
      "name": "HTTP 请求",
      "category": "网络",
      "description": "发送 HTTP 请求并获取响应",
      "input_schema": {...},
      "output_schema": {...}
    },
    ...
  ]
}
```

### 获取单个节点类型详情

```
GET /api/node-types/{type_id}
```

**响应**:

```json
{
  "id": "http_request",
  "name": "HTTP 请求",
  "category": "网络",
  "description": "发送 HTTP 请求并获取响应",
  "input_schema": {
    "type": "object",
    "properties": {
      "url": {
        "type": "string",
        "format": "uri",
        "description": "请求URL"
      },
      "method": {
        "type": "string",
        "enum": ["GET", "POST", "PUT", "DELETE"],
        "default": "GET"
      },
      "headers": {
        "type": "object"
      },
      "body": {
        "type": "object"
      }
    },
    "required": ["url"]
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "status_code": {
        "type": "integer"
      },
      "headers": {
        "type": "object"
      },
      "body": {
        "type": "object"
      }
    }
  },
  "example_usage": {
    "input": {
      "url": "https://api.example.com/data",
      "method": "GET",
      "headers": {
        "Authorization": "Bearer token123"
      }
    },
    "output": {
      "status_code": 200,
      "headers": {
        "Content-Type": "application/json"
      },
      "body": {
        "data": [1, 2, 3]
      }
    }
  }
}
```

## 错误处理

所有 API 遵循标准 HTTP 状态码：

- 200: 请求成功
- 201: 资源创建成功
- 400: 请求参数错误
- 401: 未授权
- 403: 权限不足
- 404: 资源不存在
- 500: 服务器内部错误

错误响应格式：

```json
{
  "error": {
    "code": "invalid_input",
    "message": "提供的输入数据无效",
    "details": {
      "name": "名称不能为空",
      "nodes": "至少需要一个开始节点和一个结束节点"
    }
  }
}
```

## 分页

支持分页的 API 使用以下查询参数：

- `page`: 页码 (从 1 开始)
- `per_page`: 每页项目数，最大 100

分页响应格式：

```json
{
  "items": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 45,
    "pages": 3
  }
}
```

## 限流

API 有请求限制以保护服务器资源。HTTP 响应头中包含限流信息：

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1623042000
```

超过限制时，服务器返回 HTTP 429 状态码。

## Webhook 集成

### 注册 Webhook

```
POST /api/webhooks
```

**请求参数**:

```json
{
  "url": "https://your-server.com/callback",
  "events": ["flow.executed", "flow.failed"],
  "secret": "your_secret_key"
}
```

**响应**:

```json
{
  "id": "webhook_123",
  "url": "https://your-server.com/callback",
  "events": ["flow.executed", "flow.failed"],
  "created_at": "2023-06-10T12:00:00Z"
}
```

### Webhook 通知格式

```json
{
  "event": "flow.executed",
  "timestamp": "2023-06-10T12:30:45Z",
  "data": {
    "flow_id": 1,
    "execution_id": "exec_123456",
    "status": "completed",
    "result": {...}
  },
  "signature": "sha256=..."
}
```

## 版本控制

API URL 中包含版本号，当前版本为 v1：

```
/api/v1/flows
```

如果请求中未指定版本，默认使用最新版本。

## 更新日志

### v1.1 (2023-06-15)
- 添加了流程执行的异步支持
- 新增 Webhook 集成

### v1.0 (2023-05-01)
- 初始 API 发布 
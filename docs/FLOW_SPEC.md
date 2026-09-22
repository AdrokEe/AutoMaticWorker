# 流程包规范 1.0 · 平台 0.2

本规范对应仓库中已实现的 `awm` 运行时。字段以 [JSON Schema](../schemas/manifest.schema.json) 为机器校验依据，执行行为以本文和自动化测试为依据。

## 包结构与导入

ZIP 根目录必须直接包含 `manifest.json` 和 `flow.py`，不能额外套一层目录。其他代码或资源可按需放入子目录。最大解压内容 20 MB、最多 500 个归档条目；路径穿越、Windows 保留名称、大小写重复路径、符号链接和加密包被拒绝。

导入只做静态校验，不导入或运行包内 Python。流程 ID 用小写字母开头，由小写字母、数字、连字符构成。使用清晰且独特的 ID。相同 ID 默认拒绝重复导入；选择更新后，只接受更高的三段数字版本，清空旧参数配置以避免参数语义变化。卸载保留运行记录和结果。

## 清单

参照 [报告示例](../examples/report/manifest.json)。所有顶层字段必填，未知字段被拒绝：

| 字段 | 约定 |
| --- | --- |
| `schema_version` | 固定为 `1.0` |
| `id` / `name` / `description` / `author` | 稳定 ID、显示名称、用途说明、作者 |
| `version` | 例如 `1.0.0`；不接受预发布后缀 |
| `platform` | PEP 440 版本约束；本版建议 `>=0.2.0,<0.3.0` |
| `entry` | 固定为 `flow.py:run` |
| `parameters` | 参数数组；无参数时使用空数组 |
| `dependencies` | 本版只能是 `[]`；仅支持 Python 标准库与 `awm.sdk` |
| `capabilities` | 从 `file-read`、`file-write`、`network`、`browser`、`external-write` 选择实际用到的能力 |
| `dry_run` | `simulation`（模拟执行）、`preview`（预览操作）或 `unsupported` |

依赖策略：本版不会静默执行 pip、不会修改宿主环境，也不接受第三方依赖声明。未来添加第三方依赖时需实现单包环境隔离和安装反馈，再变更契约。独立进程隔离生命周期，不隔离操作系统权限；能力声明是说明信息，不是权限沙箱。

## 参数

每个参数必须包含 `key`、`label`、`type`；`key` 由小写字母、数字和下划线组成且以字母开头，不能重复。

| 类型 | 配置值 | 可选约束 |
| --- | --- | --- |
| `text` | 字符串 | `required`、`default`、`secret` |
| `number` | 有限数字，不接受布尔值 | `minimum`、`maximum`、`required`、`default` |
| `boolean` | true 或 false | `default` |
| `enum` | 字符串 | 必须有非空 `options`，默认值必须在选项内 |
| `file` | 本机现有文件绝对路径 | 运行前验证存在；界面可上传副本 |
| `directory` | 本机现有目录绝对路径 | 桌面可选目录；浏览器可直接填写路径 |

共同可选字段：`description`、`required`、`default`。空字符串和缺失值视为空；缺失时应用默认值，必填缺失时报错。未声明的参数被拒绝。业务语义（例如数字必须是整数、CSV 应有哪些列）由流程代码检查并给出明确错误。

`secret: true` 仅允许 `text` 类型且禁止默认值。秘密值通过子进程标准输入传入，不进入命令行参数、普通配置、运行配置记录。平台隐藏日志、错误和摘要中与已声明秘密值相同的文字；作者仍须避免输出变形凭据或把秘密写入结果文件。平台不扫描并清洗任意输出文件内容。

## 执行入口与上下文

```python
def run(ctx, config):
    ctx.log("开始处理")
    ctx.check_cancelled()
    ctx.output_path("result.txt").write_text("完成", encoding="utf-8")
    ctx.progress(1, 1, "完成")
    return ctx.result("已生成结果", ["result.txt"])
```

`run` 必须是同步函数，接收上下文和经过校验的配置字典。平台通过 importlib 加载 `flow.py`，所以模块顶层也会在运行时执行：将业务操作放在入口内部。相对资源路径请基于 `Path(__file__).parent`；工作目录是该次运行的独立目录。

| 接口 | 行为 |
| --- | --- |
| `ctx.run_id` | 当前运行 ID |
| `ctx.output_dir` | 本次结果目录，`pathlib.Path` |
| `ctx.dry_run` | 试运行标记，布尔值 |
| `ctx.log(message, level='info')` | 结构化日志，级别为 info / warning / error |
| `ctx.progress(current, total, message='')` | `total > 0`，`0 <= current <= total`；显示百分比 |
| `ctx.check_cancelled()` | 已请求取消时抛出 `awm.sdk.Cancelled`；不要吞掉该异常 |
| `ctx.output_path(name)` | 返回结果目录内路径并建立父目录，拒绝越界路径 |
| `ctx.result(summary, files=())` | 校验输出文件存在，返回标准结果；`files` 是相对结果目录的文件名列表 |

每个流程在独立进程运行，同一数据目录最多一个任务。长循环逐次检查取消，网络请求必须有超时。请求取消后留 2 秒协作退出时间，再终止任务进程树。流程自己创建的服务、线程与资源应在 `finally` 中释放。

未捕获异常会产生失败状态和错误日志；平台不自动重试。退出成功但未返回合格结果也视为失败。普通 print 输出作为日志处理，保留最近 500 条，每条最多 8000 字符。输出列表是成功返回时登记的文件列表，失败和取消不将部分文件当作成功结果。

## 试运行

- `simulation`：替换真实系统调用为合成数据或本地模拟；允许产生明确标记的本地输出。
- `preview`：返回拟执行步骤或变更预览，不执行对应外部写入。
- `unsupported`：平台禁用试运行并拒绝相关请求。

必须在代码中实现 `ctx.dry_run` 的对应语义。这个标记不拦截 Python 的网络与文件操作。不要把一次试运行成功当作真实系统已验证。

## 状态、持久化与兼容

正常状态为 `running → succeeded / failed`，取消为 `running → cancelling → cancelled`。重启发现中断记录时标记失败并说明中断，不自动继续。

每次运行保留包 ID、包版本、模式、时间、非敏感配置、状态、进度、日志、摘要与输出列表。数据保存在本机；当前不提供自动清理上传输入和历史结果。可在应用关闭后备份或清理数据目录。

平台不支持的规范版本、平台范围或第三方依赖在导入前拒绝。本版 API 是 Alpha 契约；跨平台版本升级前应重新运行包测试。SDK、Schema、模板和 Skill 一起维护。

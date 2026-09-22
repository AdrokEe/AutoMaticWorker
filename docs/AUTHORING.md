# 制作流程包

先按 [快速开始](QUICKSTART.md) 安装开发环境，以下命令在仓库根目录执行。Windows 可将 `python` 替换为 `.venv\Scripts\python.exe`，或激活虚拟环境。

```powershell
python -m awm init output/my-flow --id my-flow
python -m awm validate output/my-flow
python -m awm run output/my-flow --dry-run --data-dir output/author-runs
python -m awm pack output/my-flow output/my-flow.zip
python -m awm validate output/my-flow.zip
```

`init` 复制可运行的合成报告模板；目标目录存在时拒绝覆盖。修改 `manifest.json` 和 `flow.py` 实现所需流程。`validate` 检查契约和入口，不执行代码；`pack` 先校验再打包；`run` 执行并返回记录，成功退出码为 0，失败为非 0。

`run --data-dir` 用于专用制作工作区：相同 ID 会被当前源码替换，即使包版本不变。不要把作者工作区指向桌面正在使用的数据目录。生产导入只接受更高版本的更新。

传入参数使用 JSON 配置文件：

```json
{"title": "验收报告", "rows": 3, "currency": "CNY", "include_csv": true, "delay": 0}
```

```powershell
python -m awm run output/my-flow --config output/config.json --data-dir output/author-runs
```

该示例应产生 3 条明细和总额 72。应查看输出文件内容，不能只根据命令退出码判断业务正确。配置文件不要保存真实凭据到仓库或流程包。真实秘密优先通过桌面参数输入。

## AI 制作

将 [流程制作 Skill](../skills/automaticworker-flow-author/SKILL.md) 提供给支持读取本地文件的 AI 开发工具，明确仓库根目录及所需工作。例如：

> 使用仓库内的 automaticworker-flow-author Skill，制作一个 CSV 汇总流程包。输入包含 product 和 amount 两列，输出每个 product 的金额汇总。使用合成数据测试，交付 ZIP、使用说明和实际验证结果。

Skill 为项目随附 Alpha，需要这个仓库中的规范、CLI 和模板。暂不提供脱离仓库的独立安装包，也不声称所有 AI 工具均已兼容。

制作的入口文档为 [规范](FLOW_SPEC.md)。可复用 [报告示例](../examples/report) 和 [本地网页示例](../examples/local-web)。本版不包含浏览器自动化库；本地网页示例通过标准库 HTTP 请求与 HTML 解析演示网页流程。

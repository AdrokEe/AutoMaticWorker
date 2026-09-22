import csv
import json
import time


def run(ctx, config):
    rows = config["rows"]
    if int(rows) != rows:
        raise ValueError("数据条数必须是整数")
    rows = int(rows)
    ctx.log("开始生成合成数据（不连接外部系统）")
    values = []
    for index in range(rows):
        ctx.check_cancelled()
        values.append({"item": f"示例商品 {index + 1}", "amount": (index + 1) * 12})
        time.sleep(config.get("delay", 0))
        ctx.progress(index + 1, rows, f"已处理 {index + 1} / {rows} 条")
    report = {"title": config["title"], "mode": "simulation" if ctx.dry_run else "normal",
              "rows": rows, "total": sum(v["amount"] for v in values), "currency": config.get("currency", "CNY")}
    ctx.output_path("report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    files = ["report.json"]
    if config.get("include_csv", True):
        with ctx.output_path("details.csv").open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["item", "amount"])
            writer.writeheader()
            writer.writerows(values)
        files.append("details.csv")
    return ctx.result(f"已生成 {rows} 条合成数据，合计 {report['total']} {report['currency']}", files)

"""Compute exception KPIs per cashier so the model ranks patterns from exact numbers."""
import csv
import io
from collections import defaultdict


def prepare(ctx):
    rows = list(csv.DictReader(io.StringIO(ctx.inputs["export"])))
    if not rows:
        return {"kpis": ""}
    per = defaultdict(lambda: {"void": 0, "refund": 0, "no_sale": 0, "no_receipt": 0, "refund_total": 0.0})
    for r in rows:
        k = per[r["cashier"]]
        k[r["type"]] = k.get(r["type"], 0) + 1
        if r["type"] == "refund":
            k["refund_total"] += float(r["amount"] or 0)
            if r["note"] == "no_receipt":
                k["no_receipt"] += 1
    lines = [f"{len(rows)} exceptions from {rows[0]['time']} to {rows[-1]['time']}."]
    for cashier, k in sorted(per.items(), key=lambda kv: -kv[1]["refund_total"]):
        lines.append(f"{cashier}: {k['void']} voids, {k['refund']} refunds (${k['refund_total']:.2f}, "
                     f"{k['no_receipt']} without receipt), {k['no_sale']} no-sales")
    return {"kpis": "\n".join(lines)}

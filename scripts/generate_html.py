#!/usr/bin/env python3
"""
scripts/generate_html.py — Stage 5
Reads the CSV report and generates a self-contained HTML dashboard for customers.
"""
import argparse
import csv
import json
import os
import sys
from datetime import datetime


RESOURCE_TYPE_TO_SERVICE = {
    "AWS::EC2::Instance":       "EC2",
    "AWS::EC2::SecurityGroup":  "EC2",
    "AWS::EC2::Volume":         "EC2",
    "AWS::EC2::VPC":            "VPC",
    "AWS::EC2::Subnet":         "VPC",
    "AWS::EC2::NetworkAcl":     "VPC",
    "AWS::EC2::NetworkAclEntry":"VPC",
    "AWS::RDS::DBInstance":     "RDS",
    "AWS::S3::Bucket":          "S3",
}


def service_of(resource_type):
    return RESOURCE_TYPE_TO_SERVICE.get(resource_type, "Other")


def read_csv(csv_path):
    rows = []
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            row["Service"] = service_of(row.get("Resource Type", ""))
            rows.append(row)
    return rows


def compute_summary(rows):
    total  = len(rows)
    failed = sum(1 for r in rows if r["Status"] == "FAILED")
    passed = total - failed
    rate   = round(passed / total * 100, 1) if total else 0

    by_service = {}
    for r in rows:
        svc = r["Service"]
        if svc not in by_service:
            by_service[svc] = {"PASSED": 0, "FAILED": 0}
        by_service[svc][r["Status"]] += 1

    by_type = {}
    for r in rows:
        rt = r["Resource Type"]
        if rt not in by_type:
            by_type[rt] = {"PASSED": 0, "FAILED": 0}
        by_type[rt][r["Status"]] += 1

    return {
        "total": total, "failed": failed, "passed": passed, "rate": rate,
        "by_service": by_service, "by_type": by_type,
    }


def generate_html(rows, summary, report_date, csv_name):
    services   = sorted(summary["by_service"].keys())
    svc_passed = [summary["by_service"][s]["PASSED"] for s in services]
    svc_failed = [summary["by_service"][s]["FAILED"] for s in services]

    rows_json = json.dumps(rows, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>AWS Security Assessment Report</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:'Segoe UI',Arial,sans-serif;background:#f0f2f5;color:#1a202c}}
  header{{background:#1a202c;color:#fff;padding:28px 40px;display:flex;justify-content:space-between;align-items:center}}
  header h1{{font-size:1.5rem;font-weight:700;letter-spacing:.5px}}
  header p{{font-size:.85rem;color:#a0aec0;margin-top:4px}}
  .badge{{background:#2d3748;padding:6px 14px;border-radius:20px;font-size:.8rem;color:#e2e8f0}}
  main{{max-width:1300px;margin:0 auto;padding:32px 24px}}
  h2{{font-size:1.1rem;font-weight:600;color:#2d3748;margin-bottom:16px;padding-bottom:8px;border-bottom:2px solid #e2e8f0}}
  .cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:32px}}
  .card{{background:#fff;border-radius:12px;padding:24px;box-shadow:0 1px 4px rgba(0,0,0,.08)}}
  .card .label{{font-size:.78rem;font-weight:600;text-transform:uppercase;letter-spacing:.8px;color:#718096}}
  .card .value{{font-size:2.4rem;font-weight:700;margin:8px 0 4px}}
  .card .sub{{font-size:.82rem;color:#a0aec0}}
  .card.fail .value{{color:#e53e3e}}
  .card.pass .value{{color:#38a169}}
  .card.rate .value{{color:#3182ce}}
  .charts{{display:grid;grid-template-columns:280px 1fr;gap:24px;margin-bottom:32px}}
  .chart-box{{background:#fff;border-radius:12px;padding:24px;box-shadow:0 1px 4px rgba(0,0,0,.08)}}
  .controls{{display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap}}
  .controls input,.controls select{{padding:8px 12px;border:1px solid #e2e8f0;border-radius:8px;font-size:.88rem;outline:none;background:#fff}}
  .controls input:focus,.controls select:focus{{border-color:#3182ce}}
  .controls input{{flex:1;min-width:200px}}
  table{{width:100%;border-collapse:collapse;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.08)}}
  thead{{background:#2d3748;color:#fff}}
  th{{padding:12px 14px;font-size:.8rem;font-weight:600;text-align:left;letter-spacing:.4px;white-space:nowrap}}
  td{{padding:11px 14px;font-size:.83rem;border-bottom:1px solid #f0f2f5;vertical-align:top}}
  tr:last-child td{{border-bottom:none}}
  tr:hover td{{background:#f7fafc}}
  .pill{{display:inline-block;padding:3px 10px;border-radius:20px;font-size:.75rem;font-weight:600;letter-spacing:.3px}}
  .pill.FAILED{{background:#fff5f5;color:#c53030;border:1px solid #fed7d7}}
  .pill.PASSED{{background:#f0fff4;color:#276749;border:1px solid #c6f6d5}}
  .pill.HIGH{{background:#fff5f5;color:#c53030}}
  .pill.MEDIUM{{background:#fffaf0;color:#c05621}}
  .pill.LOW{{background:#ebf8ff;color:#2c5282}}
  .resource-name{{font-family:monospace;font-size:.8rem;color:#4a5568;word-break:break-all}}
  .summary-table{{width:100%;border-collapse:collapse;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.08);margin-bottom:32px}}
  .summary-table th{{background:#2d3748;color:#fff;padding:10px 16px;font-size:.82rem;text-align:left}}
  .summary-table td{{padding:10px 16px;font-size:.85rem;border-bottom:1px solid #f0f2f5}}
  .summary-table tr:last-child td{{border-bottom:none}}
  .bar-wrap{{width:100%;background:#e2e8f0;border-radius:4px;height:10px;display:flex;overflow:hidden}}
  .bar-fail{{background:#fc8181;height:100%}}
  .bar-pass{{background:#68d391;height:100%}}
  footer{{text-align:center;padding:24px;color:#a0aec0;font-size:.8rem}}
  @media(max-width:900px){{.cards{{grid-template-columns:repeat(2,1fr)}}.charts{{grid-template-columns:1fr}}}}
  @media(max-width:600px){{.cards{{grid-template-columns:1fr}}}}
</style>
</head>
<body>

<header>
  <div>
    <h1>AWS Security Assessment Report</h1>
    <p>Generated: {report_date} &nbsp;|&nbsp; Source: {csv_name}</p>
  </div>
  <div class="badge">Powered by Checkov</div>
</header>

<main>

<!-- ── Summary Cards ── -->
<div class="cards">
  <div class="card">
    <div class="label">Total Checks</div>
    <div class="value">{summary['total']}</div>
    <div class="sub">across all resources</div>
  </div>
  <div class="card fail">
    <div class="label">Failed</div>
    <div class="value">{summary['failed']}</div>
    <div class="sub">require remediation</div>
  </div>
  <div class="card pass">
    <div class="label">Passed</div>
    <div class="value">{summary['passed']}</div>
    <div class="sub">controls satisfied</div>
  </div>
  <div class="card rate">
    <div class="label">Pass Rate</div>
    <div class="value">{summary['rate']}%</div>
    <div class="sub">overall compliance</div>
  </div>
</div>

<!-- ── Charts ── -->
<div class="charts">
  <div class="chart-box">
    <h2>Pass / Fail</h2>
    <canvas id="donutChart" height="220"></canvas>
  </div>
  <div class="chart-box">
    <h2>Checks by Service</h2>
    <canvas id="barChart" height="220"></canvas>
  </div>
</div>

<!-- ── By Resource Type ── -->
<h2>Summary by Resource Type</h2>
<table class="summary-table" style="margin-bottom:32px">
  <thead><tr><th>Resource Type</th><th>Service</th><th>Failed</th><th>Passed</th><th>Total</th><th>Pass Rate</th><th style="width:180px">Bar</th></tr></thead>
  <tbody>
    {"".join(
      f'<tr>'
      f'<td><code>{rt}</code></td>'
      f'<td>{service_of(rt)}</td>'
      f'<td style="color:#c53030;font-weight:600">{v["FAILED"]}</td>'
      f'<td style="color:#276749;font-weight:600">{v["PASSED"]}</td>'
      f'<td>{v["FAILED"]+v["PASSED"]}</td>'
      f'<td>{round(v["PASSED"]/(v["FAILED"]+v["PASSED"])*100,1) if (v["FAILED"]+v["PASSED"]) else 0}%</td>'
      f'<td><div class="bar-wrap"><div class="bar-fail" style="width:{round(v["FAILED"]/(v["FAILED"]+v["PASSED"])*100) if (v["FAILED"]+v["PASSED"]) else 0}%"></div>'
      f'<div class="bar-pass" style="width:{round(v["PASSED"]/(v["FAILED"]+v["PASSED"])*100) if (v["FAILED"]+v["PASSED"]) else 0}%"></div></div></td>'
      f'</tr>'
      for rt, v in sorted(summary["by_type"].items())
    )}
  </tbody>
</table>

<!-- ── Detail Table ── -->
<h2>Detailed Findings</h2>
<div class="controls">
  <input type="text" id="search" placeholder="Search check name or resource..."/>
  <select id="filterStatus">
    <option value="">All Status</option>
    <option value="FAILED">FAILED</option>
    <option value="PASSED">PASSED</option>
  </select>
  <select id="filterService">
    <option value="">All Services</option>
    {"".join(f'<option value="{s}">{s}</option>' for s in sorted(set(service_of(r["Resource Type"]) for r in rows)))}
  </select>
  <select id="filterSeverity">
    <option value="">All Severity</option>
    <option value="HIGH">HIGH</option>
    <option value="MEDIUM">MEDIUM</option>
    <option value="LOW">LOW</option>
  </select>
</div>
<div style="overflow-x:auto">
<table id="detailTable">
  <thead>
    <tr>
      <th>Status</th>
      <th>Check ID</th>
      <th>Check Name</th>
      <th>Service</th>
      <th>Resource Type</th>
      <th>Resource Name</th>
      <th>Severity</th>
    </tr>
  </thead>
  <tbody id="tableBody"></tbody>
</table>
</div>
<p id="rowCount" style="margin-top:10px;font-size:.82rem;color:#718096"></p>

</main>
<footer>AWS Security Assessment &mdash; Confidential &mdash; {report_date}</footer>

<script>
const ALL_ROWS = {rows_json};

// Charts
new Chart(document.getElementById('donutChart'), {{
  type: 'doughnut',
  data: {{
    labels: ['Passed', 'Failed'],
    datasets: [{{
      data: [{summary['passed']}, {summary['failed']}],
      backgroundColor: ['#68d391','#fc8181'],
      borderWidth: 0,
    }}]
  }},
  options: {{ plugins: {{ legend: {{ position: 'bottom' }} }}, cutout: '68%' }}
}});

new Chart(document.getElementById('barChart'), {{
  type: 'bar',
  data: {{
    labels: {json.dumps(services)},
    datasets: [
      {{ label: 'Passed', data: {json.dumps(svc_passed)}, backgroundColor: '#68d391', borderRadius: 4 }},
      {{ label: 'Failed', data: {json.dumps(svc_failed)}, backgroundColor: '#fc8181', borderRadius: 4 }},
    ]
  }},
  options: {{
    responsive: true,
    plugins: {{ legend: {{ position: 'bottom' }} }},
    scales: {{ x: {{ stacked: true }}, y: {{ stacked: true, ticks: {{ precision: 0 }} }} }}
  }}
}});

// Table rendering
function pill(val, type) {{
  if (!val) return '';
  return `<span class="pill ${{val}}">${{val}}</span>`;
}}

function render(rows) {{
  const tbody = document.getElementById('tableBody');
  tbody.innerHTML = rows.map(r => `
    <tr>
      <td>${{pill(r.Status)}}</td>
      <td><code>${{r['Check ID']}}</code></td>
      <td>${{r['Check Name']}}</td>
      <td>${{r.Service}}</td>
      <td style="font-size:.78rem;color:#4a5568">${{r['Resource Type']}}</td>
      <td class="resource-name">${{r['Resource Name']}}</td>
      <td>${{r.Severity ? pill(r.Severity) : ''}}</td>
    </tr>`).join('');
  document.getElementById('rowCount').textContent = `Showing ${{rows.length}} of ${{ALL_ROWS.length}} checks`;
}}

function filter() {{
  const q   = document.getElementById('search').value.toLowerCase();
  const st  = document.getElementById('filterStatus').value;
  const svc = document.getElementById('filterService').value;
  const sev = document.getElementById('filterSeverity').value;
  const out = ALL_ROWS.filter(r =>
    (!q   || r['Check Name'].toLowerCase().includes(q) || r['Resource Name'].toLowerCase().includes(q)) &&
    (!st  || r.Status   === st)  &&
    (!svc || r.Service  === svc) &&
    (!sev || r.Severity === sev)
  );
  render(out);
}}

document.getElementById('search').addEventListener('input', filter);
document.getElementById('filterStatus').addEventListener('change', filter);
document.getElementById('filterService').addEventListener('change', filter);
document.getElementById('filterSeverity').addEventListener('change', filter);

render(ALL_ROWS);
</script>
</body>
</html>"""
    return html


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, help="Path to the CSV report")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    if not os.path.exists(args.csv):
        print(f"[ERROR] CSV not found: {args.csv}", file=sys.stderr)
        sys.exit(1)

    rows    = read_csv(args.csv)
    summary = compute_summary(rows)

    report_date = datetime.now().strftime("%Y-%m-%d %H:%M")
    csv_name    = os.path.basename(args.csv)

    html = generate_html(rows, summary, report_date, csv_name)

    stem = csv_name.replace(".csv", "")
    out_path = os.path.join(args.output_dir, f"{stem}.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[html] Dashboard written: {out_path}", file=sys.stderr)
    print(out_path)


if __name__ == "__main__":
    main()

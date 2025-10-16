from typing import List
from pathlib import Path
from jinja2 import Template
from models import Quote, Candidate

TEMPLATE = Template("""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>AI Procurement Agent — Quotation</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; }
    h1 { margin-bottom: 0; }
    .muted { color: #666; }
    table { border-collapse: collapse; width: 100%; margin-top: 12px; }
    th, td { border: 1px solid #ccc; padding: 8px; font-size: 14px; vertical-align: top; }
    th { background: #f5f5f5; text-align: left; }
    .tag { display: inline-block; padding: 2px 6px; border-radius: 6px; background: #eef; margin-right: 4px; }
    .score { font-weight: bold; }
  </style>
</head>
<body>
  <h1>AI Procurement Agent — Quotation</h1>
  <p class="muted">Query: <b>{{ quote.user.query }}</b> · Budget: {{ quote.user.budget }} {{ quote.user.currency }} · Deadline: {{ quote.user.deadline_days }} days</p>

  <h2>Top Recommendation</h2>
  {% if quote.selected %}
  <p><b>{{ quote.selected.item.vendor }}</b> — {{ quote.selected.item.name }} ({{ quote.selected.item.sku }})</p>
  <ul>
    <li>Price: {{ quote.selected.item.price }} {{ quote.user.currency }}</li>
    <li>Availability: stock {{ quote.selected.item.stock }}, ETA {{ quote.selected.item.eta_days }} days</li>
    <li>Scores → Cost: {{ quote.selected.cost_fitness }}, Evidence: {{ quote.selected.evidence_score }}, Availability: {{ quote.selected.availability_score }}, <span class="score">Total: {{ quote.selected.total_score }}</span></li>
  </ul>
  {% else %}
  <p>No suitable candidate selected.</p>
  {% endif %}

  <h2>All Candidates (ranked)</h2>
  <table>
    <thead>
      <tr>
        <th>#</th>
        <th>Vendor / SKU</th>
        <th>Name</th>
        <th>Price</th>
        <th>Stock / ETA</th>
        <th>Scores</th>
        <th>Flags</th>
        <th>Rationales</th>
      </tr>
    </thead>
   <tbody>
  {% for c in quote.candidates %}
  <tr>
    <td>{{ loop.index }}</td>

        <td><b>{{ c.item.vendor }}</b><br/>{{ c.item.sku }}</td>
        <td>{{ c.item.name }}<br/><span class="muted">{{ c.item.spec_text }}</span></td>
        <td>{{ c.item.price }} {{ quote.user.currency }}</td>
        <td>{{ c.item.stock }} / {{ c.item.eta_days }}d</td>
        <td>Cost {{ c.cost_fitness }} · Ev {{ c.evidence_score }} · Av {{ c.availability_score }} <br/><span class="score">Total {{ c.total_score }}</span></td>
        <td>{% for f in c.flags %}<span class="tag">{{ f }}</span>{% endfor %}</td>
        <td>{% for r in c.rationales %}• {{ r }}<br/>{% endfor %}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</body>
</html>
""")

def save_html_report(quote: Quote, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    html = TEMPLATE.render(quote=quote)
    path = out_dir / "quotation_report.html"
    path.write_text(html, encoding="utf-8")
    return path

def save_html_report(quote: Quote, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    # Evita petadas si falta algo raro
    try:
        html = TEMPLATE.render(quote=quote)
    except Exception as e:
        html = f"<html><body><h1>Quotation</h1><p>Render error: {e}</p></body></html>"
    path = out_dir / "quotation_report.html"
    path.write_text(html, encoding="utf-8")
    return path


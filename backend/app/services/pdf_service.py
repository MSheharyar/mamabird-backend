from datetime import datetime

BRAND_RED = "#CC2929"
BRAND_BLUE = "#6EB4D4"
BRAND_YELLOW = "#F5C200"
BRAND_DARK = "#2C2C2C"
BRAND_LIGHT = "#F9F9F9"


def generate_progress_pdf(child_data: dict, progress_data: dict, badges: list) -> bytes:
    html = _build_report_html(child_data, progress_data, badges)
    try:
        from weasyprint import HTML
        return HTML(string=html).write_pdf()
    except Exception as e:
        raise RuntimeError(f"PDF generation failed: {e}")


def _build_report_html(child_data: dict, progress_data: dict, badges: list) -> str:
    child_name = child_data.get("child_name", "Student")
    age = child_data.get("age")
    grade = child_data.get("grade")
    report_date = datetime.utcnow().strftime("%B %d, %Y")

    age_grade_parts = []
    if age:
        age_grade_parts.append(f"Age {age}")
    if grade:
        age_grade_parts.append(f"Grade {grade}")
    age_grade_str = " · ".join(age_grade_parts) if age_grade_parts else ""

    subject_rows = _build_subject_rows(progress_data)
    badge_items = _build_badge_items(badges)
    total_sessions = child_data.get("total_sessions", 0)
    streak_days = child_data.get("streak_days", 0)

    total_correct = sum(v.get("correct", 0) for v in progress_data.values())
    total_questions = sum(v.get("total", 0) for v in progress_data.values())
    overall_accuracy = round(total_correct / total_questions * 100, 1) if total_questions else 0.0

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: Georgia, 'Times New Roman', serif;
    color: {BRAND_DARK};
    background: white;
    font-size: 13px;
    line-height: 1.5;
  }}
  .header {{
    background: {BRAND_RED};
    color: white;
    padding: 32px 40px 24px;
    border-bottom: 6px solid {BRAND_YELLOW};
  }}
  .header h1 {{
    font-size: 26px;
    font-weight: bold;
    letter-spacing: 0.5px;
  }}
  .header .subtitle {{
    font-size: 13px;
    opacity: 0.88;
    margin-top: 4px;
  }}
  .header .report-meta {{
    margin-top: 14px;
    font-size: 13px;
    opacity: 0.85;
  }}
  .body {{
    padding: 32px 40px;
  }}
  .section-title {{
    font-size: 15px;
    font-weight: bold;
    color: {BRAND_RED};
    border-bottom: 2px solid {BRAND_YELLOW};
    padding-bottom: 5px;
    margin: 24px 0 14px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}
  .stats-row {{
    display: flex;
    gap: 16px;
    margin-bottom: 8px;
  }}
  .stat-card {{
    flex: 1;
    background: {BRAND_LIGHT};
    border-left: 4px solid {BRAND_BLUE};
    padding: 14px 16px;
    border-radius: 4px;
  }}
  .stat-card .value {{
    font-size: 26px;
    font-weight: bold;
    color: {BRAND_RED};
  }}
  .stat-card .label {{
    font-size: 11px;
    color: #666;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    margin-top: 3px;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin-top: 8px;
  }}
  th {{
    background: {BRAND_BLUE};
    color: white;
    padding: 9px 12px;
    text-align: left;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }}
  td {{
    padding: 9px 12px;
    border-bottom: 1px solid #eee;
    font-size: 13px;
  }}
  tr:nth-child(even) td {{ background: {BRAND_LIGHT}; }}
  .progress-bar-wrap {{
    width: 100%;
    background: #e0e0e0;
    border-radius: 10px;
    height: 10px;
    overflow: hidden;
  }}
  .progress-bar-fill {{
    height: 10px;
    border-radius: 10px;
    background: {BRAND_BLUE};
  }}
  .accuracy-high {{ color: #2e7d32; font-weight: bold; }}
  .accuracy-mid  {{ color: {BRAND_YELLOW}; font-weight: bold; }}
  .accuracy-low  {{ color: {BRAND_RED}; font-weight: bold; }}
  .badges-grid {{
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 8px;
  }}
  .badge-item {{
    background: {BRAND_LIGHT};
    border: 1px solid {BRAND_YELLOW};
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 13px;
    display: flex;
    align-items: center;
    gap: 7px;
  }}
  .badge-emoji {{ font-size: 18px; }}
  .no-badges {{ color: #999; font-style: italic; font-size: 13px; }}
  .footer {{
    margin-top: 40px;
    padding: 18px 40px;
    background: {BRAND_LIGHT};
    border-top: 2px solid {BRAND_YELLOW};
    font-size: 11px;
    color: #888;
    text-align: center;
  }}
</style>
</head>
<body>

<div class="header">
  <h1>🐦 MamaBird &amp; Chirpy — Progress Report</h1>
  <div class="subtitle">AI Educational Chatbot · threebabybirdies.com</div>
  <div class="report-meta">
    <strong>{child_name}</strong>{f' · {age_grade_str}' if age_grade_str else ''} &nbsp;|&nbsp;
    Report Date: {report_date}
  </div>
</div>

<div class="body">

  <div class="section-title">Overall Summary</div>
  <div class="stats-row">
    <div class="stat-card">
      <div class="value">{overall_accuracy}%</div>
      <div class="label">Overall Accuracy</div>
    </div>
    <div class="stat-card">
      <div class="value">{total_sessions}</div>
      <div class="label">Total Sessions</div>
    </div>
    <div class="stat-card">
      <div class="value">{total_questions}</div>
      <div class="label">Questions Answered</div>
    </div>
    <div class="stat-card">
      <div class="value">{streak_days}</div>
      <div class="label">Day Streak</div>
    </div>
  </div>

  <div class="section-title">Progress by Subject</div>
  {subject_rows}

  <div class="section-title">Badges Earned</div>
  {badge_items}

</div>

<div class="footer">
  Generated by MamaBird &amp; Chirpy AI Educational Chatbot · {report_date} ·
  This report is confidential and intended for the parent/guardian of {child_name}.
</div>

</body>
</html>"""


def _build_subject_rows(progress_data: dict) -> str:
    if not progress_data:
        return '<p style="color:#999;font-style:italic;">No subject data recorded yet.</p>'

    rows = ""
    for subject, vals in sorted(progress_data.items()):
        correct = vals.get("correct", 0)
        total = vals.get("total", 0)
        acc = vals.get("accuracy_pct", 0.0)

        if acc >= 80:
            acc_class = "accuracy-high"
        elif acc >= 50:
            acc_class = "accuracy-mid"
        else:
            acc_class = "accuracy-low"

        bar_width = min(int(acc), 100)
        rows += f"""
        <tr>
          <td><strong>{subject.title()}</strong></td>
          <td>{correct} / {total}</td>
          <td class="{acc_class}">{acc}%</td>
          <td style="width:160px;">
            <div class="progress-bar-wrap">
              <div class="progress-bar-fill" style="width:{bar_width}%;"></div>
            </div>
          </td>
        </tr>"""

    return f"""<table>
      <thead>
        <tr>
          <th>Subject</th>
          <th>Correct / Total</th>
          <th>Accuracy</th>
          <th>Progress</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>"""


def _build_badge_items(badges: list) -> str:
    if not badges:
        return '<p class="no-badges">No badges earned yet — keep learning! 🐦</p>'

    items = ""
    for b in badges:
        emoji = b.get("badge_emoji", "🏅")
        name = b.get("badge_name", "Badge")
        earned = b.get("earned_at", "")
        date_str = earned[:10] if earned else ""
        items += f"""
        <div class="badge-item">
          <span class="badge-emoji">{emoji}</span>
          <div>
            <div style="font-weight:bold;">{name}</div>
            {f'<div style="font-size:11px;color:#888;">{date_str}</div>' if date_str else ''}
          </div>
        </div>"""

    return f'<div class="badges-grid">{items}</div>'

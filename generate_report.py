#!/usr/bin/env python3
"""
generate_report.py â€” Fills the HTML report template and converts to PDF via Playwright.

Usage:
    python generate_report.py <lead_json_path> [--agency-name "Your Agency"] [--agency-contact "email@example.com"] [--output report.pdf]
"""

import json
import sys
import os
import re
from datetime import date
from pathlib import Path

from dollar_value import estimate_impact, _parse_load_time


def _score_color(score):
    if score >= 80:
        return '#22c55e'
    if score >= 50:
        return '#f59e0b'
    return '#ef4444'


def _score_angle(score):
    return 180 - (score / 100 * 180)


def _status_items_html(items, is_ok):
    tag_class = 'ok' if is_ok else 'fix'
    tag_text = 'OK' if is_ok else 'FIX'
    html = ''
    for item in items:
        html += f'<div class="status-item"><span class="status-tag {tag_class}">{tag_text}</span><span>{item}</span></div>'
    return html


def _pagespeed_bars_html(pagespeed):
    metrics = []
    lcp = pagespeed.get('lcp', 'N/A')
    if lcp != 'N/A':
        try:
            val = float(str(lcp).replace('s', '').strip())
            color = 'green' if val <= 2.5 else ('amber' if val <= 4.0 else 'red')
            pct = min(val / 6.0 * 100, 100)
            metrics.append(f'<div class="bar-row"><div class="bar-label">Largest Contentful Paint</div><div class="bar-track"><div class="bar-fill {color}" style="width: {pct}%"></div></div><div class="bar-value">{lcp}</div></div>')
        except: pass

    fcp = pagespeed.get('fcp', 'N/A')
    if fcp != 'N/A':
        try:
            val = float(str(fcp).replace('s', '').strip())
            color = 'green' if val <= 1.8 else ('amber' if val <= 3.0 else 'red')
            pct = min(val / 5.0 * 100, 100)
            metrics.append(f'<div class="bar-row"><div class="bar-label">First Contentful Paint</div><div class="bar-track"><div class="bar-fill {color}" style="width: {pct}%"></div></div><div class="bar-value">{fcp}</div></div>')
        except: pass

    cls = pagespeed.get('cls', 'N/A')
    if cls != 'N/A':
        try:
            val = float(str(cls).strip())
            color = 'green' if val <= 0.1 else ('amber' if val <= 0.25 else 'red')
            pct = min(val / 0.4 * 100, 100)
            metrics.append(f'<div class="bar-row"><div class="bar-label">Cumulative Layout Shift</div><div class="bar-track"><div class="bar-fill {color}" style="width: {pct}%"></div></div><div class="bar-value">{cls}</div></div>')
        except: pass

    tti = pagespeed.get('tti', 'N/A')
    if tti != 'N/A':
        try:
            val = float(str(tti).replace('s', '').strip())
            color = 'green' if val <= 3.8 else ('amber' if val <= 7.3 else 'red')
            pct = min(val / 10.0 * 100, 100)
            metrics.append(f'<div class="bar-row"><div class="bar-label">Time to Interactive</div><div class="bar-track"><div class="bar-fill {color}" style="width: {pct}%"></div></div><div class="bar-value">{tti}</div></div>')
        except: pass

    if not metrics:
        return '<p style="font-size: 17px; color: var(--text-muted);">Performance data unavailable for this scan.</p>'
    return '\n'.join(metrics)


def _technical_checklist_html(technical):
    checks = [
        ('HTTPS enabled', technical.get('https_enabled', False)),
        ('robots.txt present', technical.get('has_robots_txt', False)),
        ('Sitemap present', technical.get('has_sitemap', False)),
        ('llms.txt present (AI-readiness)', technical.get('has_llms_txt', False)),
        ('AI crawlers allowed', technical.get('ai_crawlers_allowed', False)),
        ('Clean URL structure', technical.get('url_structure_clean', False)),
    ]
    html = ''
    for label, ok in checks:
        tag_class = 'ok' if ok else 'fix'
        tag_text = 'OK' if ok else 'FIX'
        html += f'<div class="check-item"><div class="check-icon {tag_class}">{tag_text}</div><span>{label}</span></div>'
    return html


def _recommendations_html(recommendations):
    html = ''
    for i, rec in enumerate(recommendations[:6], 1):
        html += f'<div class="rec-item"><div class="rec-num">{i}</div><div class="rec-text">{rec}</div></div>'
    return html


def _market_opportunity_html(opportunity, impact, related_queries):
    if impact.tier == 3:
        return f'<p style="font-size: 20px; color: var(--text-secondary);">{impact.notes[0] if impact.notes else "Search volume data unavailable."}</p>'

    html = ''

    # Search volume card
    if impact.monthly_lost_leads:
        html += f'<div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 24px; margin-bottom: 32px;">'
        html += f'<div class="card" style="text-align: center;"><div class="card-title">Monthly Searches</div><div style="font-size: 48px; font-weight: 700;">{opportunity.get("total_monthly_searches", "N/A")}</div></div>'
        html += f'<div class="card" style="text-align: center;"><div class="card-title">Missed Leads/Month</div><div style="font-size: 48px; font-weight: 700; color: var(--amber);">{impact.monthly_lost_leads:.0f}</div></div>'
        if impact.tier == 1 and impact.dollar_low:
            html += f'<div class="card" style="text-align: center;"><div class="card-title">Revenue Opportunity</div><div style="font-size: 48px; font-weight: 700; color: var(--green);">${impact.dollar_low:,.0f}â€“${impact.dollar_high:,.0f}</div></div>'
        else:
            html += f'<div class="card" style="text-align: center;"><div class="card-title">Opportunity Score</div><div style="font-size: 48px; font-weight: 700;">{opportunity.get("opportunity_score", "N/A")}/100</div></div>'
        html += '</div>'

    # Related queries
    if related_queries:
        html += '<div style="font-size: 22px; font-weight: 600; margin-bottom: 16px;">Related Searches You\'re Not Capturing</div>'
        html += '<div class="query-list">'
        for q in related_queries[:8]:
            html += f'<div class="query-tag">{q}</div>'
        html += '</div>'

    # Sources
    if impact.sources:
        html += f'<div style="margin-top: 32px; font-size: 13px; color: var(--text-muted);">Sources: {"; ".join(sorted(set(impact.sources)))}</div>'

    return html


def generate_report(lead, agency_name='Mena Nath Media', agency_contact='hello@menanathmedia.com', out_path=None):
    """
    Generate a branded audit PDF from a lead's pipeline data.

    lead: dict with keys matching the pipeline export schema
    """
    analysis = lead.get('analysis', {})
    opportunity = lead.get('opportunity', {})
    pagespeed = analysis.get('pagespeed', {})
    technical = analysis.get('technical_seo', {})
    contacts = analysis.get('contact_info', {})
    score = analysis.get('seo_score', 0)
    business_name = lead.get('title', lead.get('business_name', 'Unknown Business'))
    url = lead.get('url', '')

    # Compute dollar impact
    load_time = _parse_load_time(pagespeed)
    impact = estimate_impact(
        total_monthly_searches=opportunity.get('total_monthly_searches'),
        has_real_trend_data=opportunity.get('has_real_trend_data', False),
        ranking_position=lead.get('ranking_position'),
        business_type=lead.get('type', ''),
        load_time_seconds=load_time,
    )

    # Verdict
    if impact.tier == 1:
        verdict = f'Your site is costing an estimated <span class="highlight">{impact.monthly_lost_leads:.0f} leads/month</span> â€” roughly <span class="highlight">${impact.dollar_low:,.0f}â€“${impact.dollar_high:,.0f}</span> in monthly revenue.'
    elif impact.tier == 2:
        verdict = f'Estimated <span class="highlight">{impact.monthly_lost_leads:.0f} missed leads/month</span> based on current ranking and search volume.'
    else:
        verdict = '<span class="muted">This audit covers verified site issues. Market data wasn\'t available for this estimate.</span>'

    # Related queries
    related = opportunity.get('related_queries', {})
    top_queries = [q.get('query', '') for q in related.get('top', []) if q.get('query')]

    # Build template data
    template_data = {
        'agency_name': agency_name,
        'agency_contact': agency_contact,
        'business_name': business_name,
        'url': url,
        'date': date.today().strftime('%B %d, %Y'),
        'seo_score': score,
        'score_color': _score_color(score),
        'score_angle': _score_angle(score),
        'verdict': verdict,
        'strengths_html': _status_items_html(analysis.get('strengths', [])[:4], True),
        'issues_html': _status_items_html(analysis.get('issues', [])[:4], False),
        'competitor_chart_html': '',
        'pagespeed_bars_html': _pagespeed_bars_html(pagespeed),
        'technical_checklist_html': _technical_checklist_html(technical),
        'market_opportunity_html': _market_opportunity_html(opportunity, impact, top_queries),
        'recommendations_html': _recommendations_html(analysis.get('recommendations', [])),
    }

    # Load template
    template_path = Path(__file__).parent / 'report_template.html'
    html = template_path.read_text(encoding='utf-8')

    # Replace placeholders
    for key, value in template_data.items():
        html = html.replace('{{' + key + '}}', str(value))

    # Write HTML
    if out_path is None:
        out_path = Path(__file__).parent / 'leads_output' / f"report_{lead.get('id', 'unknown')}.html"
    else:
        out_path = Path(out_path)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    html_path = out_path.with_suffix('.html')
    html_path.write_text(html, encoding='utf-8')

    # Convert to PDF using html2pdf script
    pdf_path = out_path.with_suffix('.pdf')
    try:
        import subprocess
        script_path = Path(__file__).parent / 'html2pdf.py'
        cmd = [sys.executable, str(script_path), str(html_path), str(pdf_path)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if pdf_path.exists() and pdf_path.stat().st_size > 1000:
            print(f"PDF: {pdf_path}")
        else:
            print(f"HTML: {html_path}")
    except Exception:
        print(f"HTML: {html_path}")

    return str(html_path)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Generate audit report PDF')
    parser.add_argument('lead_json', help='Path to lead JSON file or inline JSON')
    parser.add_argument('--agency-name', default='Mena Nath Media')
    parser.add_argument('--agency-contact', default='hello@menanathmedia.com')
    parser.add_argument('--output', '-o', default=None)
    args = parser.parse_args()

    # Load lead data
    lead_path = Path(args.lead_json)
    if lead_path.exists():
        with open(lead_path) as f:
            lead = json.load(f)
    else:
        lead = json.loads(args.lead_json)

    generate_report(lead, args.agency_name, args.agency_contact, args.output)

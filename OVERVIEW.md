# Lead Gen Agent — Comprehensive Overview

## What Was Built

An AI-powered lead generation system that automates the entire sales prospecting workflow: **Search → Scrape → Analyze → Extract → Draft → Send**. The system finds local businesses, audits their websites, extracts contact info, and generates personalized cold emails — all from a single browser dashboard.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Browser)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Pipeline UI   │  │ Leads Table  │  │ Email Draft Modal    │  │
│  │ (type, loc,   │  │ (filterable, │  │ (copy-to-clipboard)  │  │
│  │  max results) │  │  clickable)  │  │                      │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
│         │                 │                      │               │
│         └─────────────────┼──────────────────────┘               │
│                           │ fetch()                              │
└───────────────────────────┼─────────────────────────────────────┘
                            │
┌───────────────────────────┼─────────────────────────────────────┐
│                     API SERVER (port 8081)                       │
│  ┌────────────────────────┴────────────────────────────────┐    │
│  │  POST /api/run  →  run_pipeline() in background thread  │    │
│  │  GET /api/status →  pipeline_status dict                 │    │
│  │  GET /api/leads  →  db.get_all_leads()                  │    │
│  │  GET /api/email-draft/<id> → db.get_email_draft()       │    │
│  └────────────────────────┬────────────────────────────────┘    │
│                           │                                      │
│  ┌────────────────────────┴────────────────────────────────┐    │
│  │              PIPELINE (per lead)                         │    │
│  │  1. search_web()        → Firecrawl API                 │    │
│  │  2. scrape_url()        → Firecrawl API                 │    │
│  │  3. analyze_website()   → SEO + HTML + Technical        │    │
│  │  4. extract_contacts()  → Regex patterns                │    │
│  │  5. analyze_opportunity() → pytrends (Google Trends)    │    │
│  │  6. generate_email_draft() → Conditional template       │    │
│  │  7. db.save_lead()      → SQLite                        │    │
│  │  8. db.export_to_json() → leads_export.json             │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                     EXTERNAL APIs                                │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │ Firecrawl    │  │ Google       │  │ PageSpeed Insights     │  │
│  │ (search +    │  │ pytrends     │  │ (performance metrics)  │  │
│  │  scrape)     │  │ (trends)     │  │                        │  │
│  └─────────────┘  └──────────────┘  └────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Components

### 1. Search & Discovery (`api_server.py`)
- Runs from frontend via "Find Leads" button
- Configurable: business type, location, max results (5-50)
- Filters out directories (Yelp, BBB, Facebook, etc.)
- Append mode: skips URLs already in database

### 2. Website Analysis (`seo_analyzer.py`)
- **PageSpeed**: Performance score, LCP, FCP, CLS, TTI
- **HTML Analysis**: Title, meta description, headings, images, links, canonical, Open Graph
- **Technical SEO**: robots.txt, sitemap, HTTPS, llms.txt, AI crawler access
- **Content Quality**: Word count, keyword stuffing, readability
- **AEO (AI Engine Optimization)**: llms.txt, AI crawler permissions, structured data
- **Score**: 0-100 weighted composite

### 3. Contact Extraction (`contact_extractor.py`)
- **Emails**: Regex with MHTML/false-positive filtering
- **Phones**: From tel: links (most reliable) + text patterns
- **Social Profiles**: Facebook, Instagram, LinkedIn, Twitter, YouTube, Yelp
- **WhatsApp**: wa.me links
- **Contact Page**: Auto-detected URL

### 4. Google Trends (`trends_analyzer.py`)
- pytrends integration for real search interest data
- Interest over time (0-100 scale)
- Related queries (top + rising)
- 24-hour cache to avoid rate limits
- Honest "Data unavailable" when rate-limited

### 5. Email Draft Generation (`lead_generation_workflow.py`)
- Personalized per lead with conditional blocks
- Subject: "Quick question about {business_name}'s website"
- Body: ranking context → specific issues → search volume → CTA
- Filters contradictions (e.g., "robots.txt present" + "AI blocked")
- P.S. mentions social profiles if no email
- Never fabricates claims

### 6. Frontend Dashboard (`leads_output/index.html`)
- Dark monochrome UI with type-specific icon colors
- Pipeline UI: run searches from the browser
- Filterable leads table (All, Has Contact, by type)
- Detail panel with SEO issues, strengths, contacts
- Email draft modal with copy-to-clipboard
- Real-time progress bar during pipeline runs

### 7. Database (`database.py`)
- SQLite with four tables: leads, analysis, outreach, search_history
- Upsert logic (updates if URL exists, inserts if new)
- Email drafts stored in outreach table
- JSON export for frontend consumption

---

## Business Types Supported

| Type | Icon | Color |
|------|------|-------|
| Solar | ☀️ Sun | Amber #f59e0b |
| Pool | 🏊 Swimmer | Blue #3b82f6 |
| Pest Control | 🐛 Bug | Green #10b981 |
| Dentist | 🦷 Tooth | Purple #8b5cf6 |
| Auto Repair | 🔧 Wrench | Red #ef4444 |
| + HVAC, Plumbing, Roofing, Electrician, Landscaping, Cleaning, Painting | Default | Gray |

---

## Key Decisions

1. **pytrends over hardcoded estimates** — Real data or "Data unavailable", never fake numbers
2. **Conditional email blocks** — Omit entire sections where data is missing
3. **Contradiction filtering** — Don't send emails that contradict themselves
4. **Append mode** — Each run adds leads, never overwrites
5. **Monochrome UI** — Professional aesthetic, not AI slop
6. **No client-side email fallback** — Avoid maintenance drift between Python and JS

---

## Bugs Found & Fixed

| Bug | Root Cause | Fix |
|-----|-----------|-----|
| `int('Data unavailable')` crash | pytrends returns string when no data | `safe_parse_leads()` wrapper |
| Leads don't persist on refresh | Browser caches JSON | Cache-busting `?t=Date.now()` |
| `get_lead()` merged into `get_email_draft()` | Edit accidentally combined methods | Separated into distinct methods |
| API writes to nested directory | Relative path resolved wrong | Absolute path `Path(__file__).parent` |
| API uses wrong database | Default path vs project path | Explicit `db_path` parameter |
| MHTML emails in contacts | Chrome bookmark artifact | Filter `mhtml.blink` domains |
| Invalid social handles | Regex too permissive | Min 5 chars, starts with letter |
| Contradictory recommendations | Always recommends llms.txt | Check if already present |
| Close button doesn't work | `closeModal()` function deleted | Re-added function |
| Social links not clickable | Rendered as plain text | Built actual URLs per platform |

---

## Running the System

```bash
# From lead-gen-agent directory
pip install pytrends requests
cp .env.example .env  # Add FIRECRAWL_API_KEY
python serve_dashboard.py

# Dashboard: http://localhost:8080
# API: http://localhost:8081
```

---

## Repository

**GitHub**: https://github.com/karyna1661/lead-gen-agent
**Visibility**: Public
**License**: MIT

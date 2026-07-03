# Mechanism Log — Lead Generation System

---

## [1. Search & Discovery Pipeline]
- **Trigger**: User clicks "Find Leads" on the frontend dashboard
- **Inputs**: Business type (dropdown: solar, pool, pest_control, etc.), location (text input), max_results (5-50)
- **Core transformation**: `api_server.py:run_pipeline()` calls `search_web()` which hits the Firecrawl API with a query like "pest_control company in Dallas, TX". Results are filtered against a skip-list of directories (Yelp, BBB, Facebook, etc.)
- **Decision points**: (1) Skip domains — any URL containing a directory site is dropped. (2) Duplicate check — `db.get_lead_by_url()` skips URLs already in the database (append mode). (3) Scraping success — if Firecrawl fails to scrape a URL, it's skipped with a log message
- **Output/handoff**: List of filtered site URLs passed to the analysis stage
- **Failure mode**: Firecrawl API down or rate-limited → pipeline logs error, continues with remaining sites. No crash, graceful degradation
- **One-liner**: The pipeline searches Google via Firecrawl, filters out directories, and feeds real business websites to the analysis engine

---

## [2. Website Analysis Engine]
- **Trigger**: Each URL from the search results is fed in sequentially
- **Inputs**: URL, HTML content (from Firecrawl scrape), ranking position, search query
- **Core transformation**: `seo_analyzer.py:analyze_url()` runs four parallel checks: (1) PageSpeed Insights API for performance metrics, (2) HTML parser for meta tags, headings, images, links, (3) Technical SEO checks (robots.txt, sitemap, HTTPS, llms.txt), (4) Content quality analysis (word count, keyword stuffing)
- **Decision points**: (1) PageSpeed API key present → higher rate limits. (2) `has_llms.txt` and `ai_crawlers_allowed` flags determine AEO recommendations. (3) Score calculation weights PageSpeed at 30%, issues penalize, strengths bonus
- **Output/handoff**: `analysis` dict with seo_score, issues[], strengths[], pagespeed data, technical_seo, content_quality → passed to contact extraction and email generation
- **Failure mode**: PageSpeed rate-limited (429) → returns "rate_limited" status, score falls back to base 50. HTML parsing errors caught and skipped
- **One-liner**: Each website gets a full SEO autopsy — performance, structure, content, and AI-readiness — scored 0-100

---

## [3. Contact Extraction]
- **Trigger**: Runs immediately after SEO analysis on the same HTML content
- **Inputs**: Raw HTML from Firecrawl scrape, base URL
- **Core transformation**: `contact_extractor.py:extract_from_html()` runs regex patterns for: emails (with MHTML/false-positive filtering), US phone numbers (from tel: links first, then text), social profiles (Facebook, Instagram, LinkedIn, Twitter, YouTube, Yelp), WhatsApp links, contact page URLs
- **Decision points**: (1) Email validation — rejects MHTML bookmarks, image extensions, hex-hash domains, TLDs with digits. (2) Phone validation — must be 10 or 11 digits. (3) Social handle validation — must start with letter, minimum 5 chars, no hex hashes. (4) Obfuscated email detection — handles [at], (at), {at} patterns
- **Output/handoff**: `contacts` dict with emails[], phones[], social_profiles{}, whatsapp, contact_page_url → stored in database alongside analysis
- **Failure mode**: No contacts found → empty arrays, lead still saved but marked as "no contact" in dashboard (dimmed at 50% opacity)
- **One-liner**: The extractor scrapes every contact signal from the HTML — emails, phones, social links — and filters out browser artifacts and false positives

---

## [4. Google Trends Integration]
- **Trigger**: Called during analysis to get market opportunity data
- **Inputs**: Business type, location (mapped to country code like US-CA), ranking position
- **Core transformation**: `trends_analyzer.py:analyze_opportunity()` calls pytrends `TrendReq` to fetch interest-over-time (max 5 keywords) and related queries. Computes average interest score (0-100), trend direction (rising/falling/stable), and related search terms
- **Decision points**: (1) pytrends availability — if import fails or API errors, returns error dict. (2) `has_real_trend_data` flag — determines whether to show real numbers or "Data unavailable". (3) Cache check — 24hr TTL avoids re-fetching same keywords/location
- **Output/handoff**: `opportunity` dict with total_monthly_searches, estimated_monthly_leads, trend_data, related_queries, data_source → consumed by email draft and proposal generation
- **Failure mode**: pytrends rate-limited (429) → cached data if available, otherwise returns 0 values. Never fabricates numbers
- **One-liner**: We query Google Trends for real search interest data, so every proposal shows actual market signal or honestly says "data unavailable"

---

## [5. Email Draft Generation]
- **Trigger**: Called after analysis completes, stored in database
- **Inputs**: Complete analysis dict (business name, location, ranking, issues, opportunity, contacts)
- **Core transformation**: `lead_generation_workflow.py:generate_email_draft()` builds a personalized email with conditional blocks: ranking block (only if real ranking), issues block (top 2-3 real issues, filtered for contradictions), search volume block (only if real numbers), P.S. (mentions social profiles if no email)
- **Decision points**: (1) Contradiction filtering — skips "AI crawlers blocked" if "robots.txt present" is a strength, skips "Missing llms.txt" if already present. (2) Data availability — omits entire blocks where data is "Data unavailable". (3) Social fallback — P.S. mentions Facebook/Instagram if no email found
- **Output/handoff**: `{subject, body, plain_text}` dict → stored in `outreach.email_draft` column, rendered in frontend modal
- **Failure mode**: No real data → email only includes what's verifiable. Never makes claims without evidence
- **One-liner**: Each lead gets a personalized cold email that only states facts we actually found — no fabricated claims, no filler

---

## [6. Frontend Dashboard]
- **Trigger**: User opens `http://localhost:8080/index.html` in browser
- **Inputs**: JSON export file (`leads_export.json`) loaded via fetch with cache-busting
- **Core transformation**: `index.html` renders stats row, filterable leads table, detail panel, and email draft modal. Pipeline UI allows running new searches from the browser
- **Decision points**: (1) Filter system — All, Has Contact, or by business type. (2) Contact visibility — leads without email/phone are dimmed at 50% opacity. (3) Social links — rendered as clickable URLs to actual profiles
- **Output/handoff**: User views leads, clicks to see details, copies email drafts to clipboard
- **Failure mode**: API server down → shows "Could not load email draft" message. JSON load fails → shows empty state with "Select a lead to view details"
- **One-liner**: The dashboard is the command center — search, analyze, and draft outreach emails without touching the terminal

---

## [7. Database & Persistence]
- **Trigger**: Every pipeline run writes to SQLite database
- **Inputs**: Lead data, analysis results, email drafts, outreach status
- **Core transformation**: `database.py:LeadDatabase` manages four tables: leads (url, title, type, location, ranking), analysis (seo_score, issues, strengths, contacts, pagespeed), outreach (status, email_draft, contact_email), search_history
- **Decision points**: (1) Upsert logic — `add_lead()` updates if URL exists, inserts if new. (2) Email draft storage — `save_email_draft()` creates or updates outreach record. (3) JSON export — `export_to_json()` rebuilds the full export after each pipeline run
- **Output/handoff**: SQLite database → JSON export → frontend dashboard
- **Failure mode**: Database locked → SQLite handles with WAL mode. Export fails → stale JSON served, pipeline continues
- **One-liner**: SQLite is the single source of truth — every lead, analysis, and email draft persists across sessions

---

## [8. API Server]
- **Trigger**: Frontend makes HTTP requests to `localhost:8081`
- **Inputs**: POST `/api/run` with business_type, location, max_results. GET `/api/status`, `/api/leads`, `/api/email-draft/<id>`
- **Core transformation**: `api_server.py` runs the full pipeline in a background thread, polls status every 2 seconds from frontend, exports JSON on completion
- **Decision points**: (1) Pipeline already running → reject new request. (2) Background thread → non-blocking, frontend shows progress bar. (3) JSON export path → absolute path prevents nested directory bugs
- **Output/handoff**: Pipeline status JSON → frontend progress bar. Email draft JSON → modal renderer
- **Failure mode**: Pipeline error → status reflects error, frontend shows error message. API server crash → frontend shows connection error
- **One-liner**: The API server bridges the Python backend to the browser frontend, running heavy analysis in the background while the UI stays responsive

---

## Decision Log

### D1: pytrends over hardcoded estimates
**Decision**: Replace fake search volume numbers with real Google Trends data via pytrends
**Rationale**: Hardcoded numbers (12,000 for solar, 18,000 for pool) were fabrication. Cold emails with made-up stats destroy credibility. pytrends gives real relative interest scores.
**Tradeoff**: pytrends rate-limits aggressively (429 errors). We cache for 24hrs and show "Data unavailable" when rate-limited rather than fake numbers.

### D2: Conditional email blocks
**Decision**: Email draft omits entire sections where data is unavailable
**Rationale**: A cold email that says "search volume: Data unavailable" is worse than one that doesn't mention search volume at all. Conditional blocks keep the email honest.
**Tradeoff**: Some emails will be shorter than others. But every email that sends will be truthful.

### D3: Contradiction filtering in emails
**Decision**: Filter out issues that contradict strengths (e.g., "robots.txt present" + "AI crawlers blocked")
**Rationale**: An email that says both "you have robots.txt" and "you don't have robots.txt" undermines credibility. The other agent flagged this explicitly.
**Tradeoff**: We lose some detail, but gain trust.

### D4: Social profile fallback in P.S.
**Decision**: When no email is found but Facebook/Instagram exists, P.S. says "happy to connect there"
**Rationale**: A lead with a clickable social profile is still reachable. The email should acknowledge this channel.
**Tradeoff**: DMs on social are less formal than email, but they're better than nothing.

### D5: MHTML email filtering
**Decision**: Reject emails matching `mhtml.blink`, `@mhtml`, hex-hash domains
**Rationale**: Chrome's "Save as MHTML" creates fake email-like strings that the regex was matching. These can't receive mail.
**Tradeoff**: Very aggressive filtering might reject some obscure but real domains. The false positive rate was higher than the false negative risk.

### D6: Social handle validation
**Decision**: Minimum 5 chars, must start with letter, no hex hashes
**Rationale**: The extractor was pulling "2008" as a Facebook handle and `cd952b49-e959-4c1d-aac1-3ad5a8...` as a YouTube channel. These are URL artifacts, not real profiles.
**Tradeoff**: Some legitimate short handles (e.g., "go") might be filtered. But the common case is better.

### D7: Append mode over overwrite
**Decision**: Pipeline skips URLs already in database, never deletes existing leads
**Rationale**: Lead gen is a numbers game. Each run should add to the pile, not replace it. Running 10 searches across different cities should accumulate 100+ leads.
**Tradeoff**: Database grows over time. But SQLite handles this fine for thousands of leads.

### D8: No client-side email fallback
**Decision**: Frontend doesn't duplicate Python email logic in JavaScript
**Rationale**: Two implementations of the same template will drift. If we tweak tone in Python, the JS version stays stale.
**Tradeoff**: If API is down, email draft shows "Could not load" instead of a fallback. But we avoid maintenance bugs.

### D9: Monochrome UI over rainbow
**Decision**: Remove multicolor accents (amber, blue, violet, green) in favor of grays with subtle type-specific icon colors
**Rationale**: The multicolor dashboard screamed "AI slop" to the user. A monochrome base with only status colors (green=success, red=issue) feels more professional.
**Tradeoff**: Less visual differentiation between sections, but cleaner overall aesthetic.

### D10: Absolute paths for API server
**Decision**: Use `Path(__file__).parent / "leads_output"` instead of relative `"leads_output"`
**Rationale**: The API server's working directory differed from the project root, causing it to write to `leads_output/leads_output/` (nested). Absolute paths prevent this class of bug.
**Tradeoff**: Less portable if the project moves, but the absolute path is derived from the script location, so it moves with the code.

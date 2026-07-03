# Lead Gen Agent

AI-powered lead generation system that searches, scrapes, analyzes, and generates personalized outreach emails for local businesses.

## Features

- **Multi-industry support**: Solar, Pool, Pest Control, HVAC, Plumbing, Roofing, Dentist, Electrician, and more
- **Real-time pipeline**: Run from the frontend dashboard with configurable business type and location
- **SEO analysis**: PageSpeed, meta tags, heading hierarchy, technical SEO checks
- **Contact extraction**: Emails, phone numbers, social profiles from websites
- **Google Trends integration**: Real search interest data via pytrends
- **Email draft generation**: Personalized, copy-paste ready outreach emails
- **Append mode**: Each run adds new leads without duplicates

## Quick Start

```bash
# Install dependencies
pip install pytrends requests

# Set up environment
cp .env.example .env
# Add your Google PageSpeed API key to .env (optional, improves rate limits)

# Start the dashboard
python serve_dashboard.py
```

Dashboard opens at `http://localhost:8080`, API runs at `http://localhost:8081`.

## Usage

1. Open the dashboard in your browser
2. Select business type and location
3. Click "Find Leads"
4. Watch real-time progress as leads are discovered and analyzed
5. Click any lead to view details and email draft
6. Copy email to clipboard and send

## Architecture

```
lead-gen-agent/
├── api_server.py              # REST API for frontend
├── contact_extractor.py       # Email/phone/social extraction
├── database.py                # SQLite storage
├── lead_generation_workflow.py # Core pipeline logic
├── seo_analyzer.py            # PageSpeed + HTML analysis
├── serve_dashboard.py         # Static file server
├── trends_analyzer.py         # Google Trends via pytrends
├── leads_output/              # Dashboard frontend (index.html)
├── .env.example               # Environment template
└── test_pytrends.py           # pytrends integration test
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/run` | POST | Start pipeline with `{business_type, location, max_results}` |
| `/api/status` | GET | Pipeline progress |
| `/api/leads` | GET | All leads |
| `/api/stats` | GET | Database statistics |
| `/api/email-draft/<id>` | GET | Email draft for a lead |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_PAGESPEED_API_KEY` | No | Higher rate limits for PageSpeed API |
| `FIRECRAWL_API_KEY` | Yes | Web scraping API key |

## License

MIT

"""
Lead Generation Workflow - Complete Pipeline
Search → Scrape → Analyze → Extract Contacts → Generate Proposals
"""
import requests
import json
import os
from datetime import datetime
from urllib.parse import urlparse
from pathlib import Path


def safe_parse_leads(value):
    """Safely parse lead count from string, returning 0 if invalid"""
    if isinstance(value, (int, float)):
        return int(value * 0.3)
    if not value or value == 'Data unavailable':
        return 0
    try:
        cleaned = str(value).replace(',', '').replace('+', '').strip()
        return int(float(cleaned) * 0.3) if cleaned else 0
    except (ValueError, TypeError):
        return 0

# Load environment variables from .env file if it exists
env_file = Path('.env')
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                if value:  # Only set if value is not empty
                    os.environ[key.strip()] = value.strip()

# Import new modules
from seo_analyzer import SEOAnalyzer
from contact_extractor import ContactExtractor
from trends_analyzer import TrendsAnalyzer
from database import LeadDatabase

FIRECRAWL_API_KEY = os.environ.get('FIRECRAWL_API_KEY')
if not FIRECRAWL_API_KEY:
    raise RuntimeError("Set FIRECRAWL_API_KEY environment variable or create a .env file")
BASE_URL = "https://api.firecrawl.dev/v2"
OUTPUT_DIR = "leads_output"

headers = {
    "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
    "Content-Type": "application/json"
}

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Initialize modules
seo_analyzer = SEOAnalyzer()
contact_extractor = ContactExtractor()
trends_analyzer = TrendsAnalyzer()
db = LeadDatabase()


def search_web(query, limit=10):
    """Search the web using Firecrawl"""
    response = requests.post(
        f"{BASE_URL}/search",
        headers=headers,
        json={"query": query, "limit": limit}
    )
    return response.json()


def scrape_url(url, formats=["markdown", "html"]):
    """Scrape a single URL"""
    response = requests.post(
        f"{BASE_URL}/scrape",
        headers=headers,
        json={"url": url, "formats": formats}
    )
    return response.json()


def analyze_website(url, html_content, markdown_content, ranking_position, search_query):
    """Perform comprehensive website analysis"""
    
    # Run SEO analysis
    seo_results = seo_analyzer.analyze(url, html_content)
    
    # Extract contacts
    contacts = contact_extractor.extract_from_html(html_content, url)
    
    # Get trending data
    location = extract_location_from_query(search_query)
    business_type = extract_business_type_from_query(search_query)
    opportunity = trends_analyzer.analyze_opportunity(business_type, location, ranking_position)
    
    # Combine results
    analysis = {
        'url': url,
        'title': extract_title_from_html(html_content),
        'type': business_type,
        'location': location,
        'ranking_position': ranking_position,
        'search_query': search_query,
        'seo_score': seo_results.get('score', 0),
        'pagespeed': seo_results.get('pagespeed', {}),
        'html_analysis': seo_results.get('html_analysis', {}),
        'technical_seo': seo_results.get('technical_seo', {}),
        'content_quality': seo_results.get('content_quality', {}),
        'issues': seo_results.get('issues', []),
        'strengths': seo_results.get('strengths', []),
        'contacts': contacts,
        'opportunity': opportunity,
        'recommendations': generate_recommendations(seo_results, contacts, opportunity)
    }
    
    return analysis


def extract_location_from_query(query):
    """Extract location from search query"""
    locations = {
        'los angeles': 'Los Angeles, CA',
        'la': 'Los Angeles, CA',
        'austin': 'Austin, TX',
        'texas': 'Texas',
        'california': 'California'
    }
    
    query_lower = query.lower()
    for key, value in locations.items():
        if key in query_lower:
            return value
    return 'Unknown Location'


def extract_business_type_from_query(query):
    """Extract business type from search query"""
    types = {
        'solar': 'solar installation',
        'pool': 'swimming pool services',
        'plumbing': 'plumbing services',
        'hvac': 'hvac services',
        'roofing': 'roofing services',
        'electrician': 'electrical services',
        'dentist': 'dental services',
        'chiropractor': 'chiropractic services'
    }
    
    query_lower = query.lower()
    for key, value in types.items():
        if key in query_lower:
            return value
    return 'general services'


def extract_title_from_html(html):
    """Extract title from HTML"""
    import re
    match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return 'Unknown'


def generate_recommendations(seo_results, contacts, opportunity):
    """Generate personalized recommendations based on actual analysis"""
    recommendations = []
    
    # SEO-based recommendations
    issues = seo_results.get('issues', [])
    
    if any('Missing page title' in i for i in issues):
        recommendations.append("Add a descriptive, keyword-rich page title (50-60 characters)")
    
    if any('Missing meta description' in i for i in issues):
        recommendations.append("Create compelling meta descriptions for all pages (150-160 characters)")
    
    if any('H1' in i for i in issues):
        recommendations.append("Fix heading hierarchy - use single H1 per page with primary keyword")
    
    if any('performance' in i.lower() for i in issues):
        recommendations.append("Optimize page speed - compress images, enable caching, minimize CSS/JS")
    
    if any('mobile' in i.lower() or 'viewport' in i.lower() for i in issues):
        recommendations.append("Ensure mobile-responsive design with proper viewport meta tag")
    
    if any('alt text' in i.lower() for i in issues):
        recommendations.append("Add descriptive alt text to all images for accessibility and SEO")
    
    if any('HTTPS' in i for i in issues):
        recommendations.append("Enable HTTPS for security and SEO ranking boost")
    
    if any('robots.txt' in i for i in issues):
        recommendations.append("Add robots.txt to guide search engine crawlers")
    
    if any('sitemap' in i.lower() for i in issues):
        recommendations.append("Create and submit XML sitemap to Google Search Console")
    
    if any('Open Graph' in i for i in issues):
        recommendations.append("Add Open Graph tags for better social media sharing")
    
    # Contact-based recommendations
    if not contacts.get('emails'):
        recommendations.append("Add visible email contact information")
    
    if not contacts.get('phones'):
        recommendations.append("Add click-to-call phone number prominently")
    
    if not contacts.get('social_profiles'):
        recommendations.append("Add social media profile links")
    
    # Opportunity-based recommendations
    if opportunity.get('opportunity_score', 0) < 50:
        recommendations.append("Focus on local SEO - optimize Google Business Profile")
        recommendations.append("Build location-specific landing pages")
        recommendations.append("Implement LocalBusiness schema markup")
    
    # AI SEO recommendations
    recommendations.append("Add structured data (FAQ, LocalBusiness, Service schemas)")
    
    # Only recommend llms.txt if not already present
    if not any('llms.txt present' in s for s in seo_results.get('strengths', [])):
        recommendations.append("Create llms.txt file for AI assistant visibility")
    
    recommendations.append("Optimize for voice search with natural language content")
    
    return recommendations[:10]  # Top 10 recommendations


def generate_proposal(analysis):
    """Generate personalized proposal based on analysis"""
    proposal = f"""
# Website Redesign Proposal
## {analysis.get('title', 'Unknown Business')}
## {analysis.get('url', '')}

---

## Current SEO Analysis

**Overall Score:** {analysis.get('seo_score', 0)}/100

### Performance Metrics
- Performance Score: {analysis.get('pagespeed', {}).get('performance_score', 'N/A')}/100
- Largest Contentful Paint (LCP): {analysis.get('pagespeed', {}).get('lcp', 'N/A')}
- First Contentful Paint (FCP): {analysis.get('pagespeed', {}).get('fcp', 'N/A')}
- Cumulative Layout Shift (CLS): {analysis.get('pagespeed', {}).get('cls', 'N/A')}

### Issues Found ({len(analysis.get('issues', []))})
"""
    for issue in analysis.get('issues', []):
        proposal += f"- {issue}\n"
    
    proposal += "\n### Strengths\n"
    for strength in analysis.get('strengths', []):
        proposal += f"- {strength}\n"
    
    proposal += f"""
---

## Market Opportunity

**Location:** {analysis.get('location', 'Unknown')}
**Your Ranking:** #{analysis.get('ranking_position', 'N/A')}
**Monthly Searches:** {analysis.get('opportunity', {}).get('total_monthly_searches', 'N/A')}
**Estimated Monthly Leads:** {analysis.get('opportunity', {}).get('estimated_monthly_leads', 'N/A')}

### Trending Services in Your Area
"""
    # Use pytrends data instead of hardcoded trending_services
    trend_data = analysis.get('opportunity', {}).get('trend_data', {})
    if 'summary' in trend_data and not trend_data.get('error'):
        for keyword, summary in trend_data['summary'].items():
            trend = summary.get('trend', 'stable')
            avg = summary.get('avg_interest', 0)
            proposal += f"- {keyword}: Interest score {avg}/100 ({trend})\n"
    else:
        proposal += "- Trend data requires pytrends API access\n"
    
    proposal += f"""
---

## Recommended Improvements

"""
    for i, rec in enumerate(analysis.get('recommendations', []), 1):
        proposal += f"{i}. {rec}\n"
    
    proposal += f"""
---

## Proposed Website Structure

### 1. Hero Section
- Clear value proposition with primary CTA
- Trust badges (Licensed, Insured, 5-Star Rated)
- Location-specific messaging

### 2. Services Section
- Card-based layout with icons
- Service descriptions optimized for SEO
- Pricing or quote request integration

### 3. Social Proof
- Customer testimonials with photos
- Star ratings and review highlights
- Before/after project gallery

### 4. Service Areas
- Interactive Google Map
- Location-specific landing pages
- Local schema markup

### 5. Contact Section
- Multi-step quote form
- Click-to-call phone number
- Business hours and address
- Live chat integration

### 6. AI Integration
- Voice AI for 24/7 customer service
- Chatbot for instant responses
- Automated quote generation

---

## AI SEO Optimization (AEO)

1. **Structured Data** - LocalBusiness, Service, FAQ schemas
2. **llms.txt** - Help AI assistants understand your business
3. **Voice Search** - Natural language content for voice queries
4. **Entity Optimization** - Consistent brand information across web

---

## Value Proposition

### Beyond Rankings
- **Voice AI Integration** - Automated customer service with ElevenLabs/Deepgram
- **AI Chatbot** - 24/7 lead capture and qualification
- **Smart Quote System** - Instant, accurate quote generation

### ROI Projection
- Current estimated leads: {safe_parse_leads(analysis.get('opportunity', {}).get('estimated_monthly_leads', '0'))}/month
- Projected leads after optimization: {analysis.get('opportunity', {}).get('estimated_monthly_leads', 'N/A')}/month
- Potential increase: {analysis.get('opportunity', {}).get('estimated_monthly_leads', 'N/A')}

---

## Timeline & Investment

**Phase 1 (Weeks 1-2):** Design & Strategy
**Phase 2 (Weeks 3-4):** Development
**Phase 3 (Week 5):** Content & SEO
**Phase 4 (Week 6):** Testing & Launch

**Investment:** $2,500 - $5,000
**ROI Timeline:** 3-6 months to see significant lead increase

---

## Next Steps

1. Review this proposal
2. Schedule a 15-minute discovery call
3. Receive custom mockup of your new website
4. Begin development upon approval
"""
    return proposal


def generate_email_draft(analysis):
    """Generate a personalized email draft for outreach
    
    Returns dict with subject, body, and plain_text keys.
    Omits blocks where data is unavailable - never fabricates claims.
    """
    business_name = analysis.get('title', 'your business')
    location = analysis.get('location', 'your area')
    url = analysis.get('url', '')
    ranking = analysis.get('ranking_position', 0)
    issues = analysis.get('issues', [])
    opportunity = analysis.get('opportunity', {})
    business_type = analysis.get('business_type', 'services')
    
    # Get real numbers only
    search_volume = opportunity.get('total_monthly_searches', 'Data unavailable')
    monthly_leads = opportunity.get('estimated_monthly_leads', 'Data unavailable')
    has_search_data = (search_volume not in ['Data unavailable', 'N/A', None, 0] and 
                       monthly_leads not in ['Data unavailable', 'N/A', None, 0])
    
    # Filter issues - exclude contradictory findings
    # Don't mention "AI crawlers blocked" if we already mention robots.txt strength
    # Don't recommend llms.txt if already present
    filtered_issues = []
    has_robots_txt = any('robots.txt present' in s for s in analysis.get('strengths', []))
    has_llms_txt = any('llms.txt present' in s for s in analysis.get('strengths', []))
    
    for issue in issues[:5]:  # Check top 5 issues
        # Skip contradictory issues
        if 'AI crawlers may be blocked' in issue and has_robots_txt:
            continue
        if 'Missing llms.txt' in issue and has_llms_txt:
            continue
        # Skip generic issues
        if 'PageSpeed data unavailable' in issue:
            continue
        filtered_issues.append(issue)
    
    # Take top 2-3 specific issues
    email_issues = filtered_issues[:3]
    
    # Build subject line
    subject = f"Quick question about {business_name}'s website"
    
    # Build email body - conditional blocks
    parts = []
    
    parts.append(f"Hi there,")
    parts.append(f"")
    parts.append(f"I was looking at {business_name}'s website ({url}) and noticed a few things that might be costing you customers in {location}.")
    parts.append(f"")
    
    # Ranking block - only if we have real ranking data
    if ranking and isinstance(ranking, int) and ranking > 0:
        parts.append(f"You're currently ranking #{ranking} for \"{business_type} in {location}\" on Google.")
        parts.append(f"")
    
    # Issues block - only if we have real issues
    if email_issues:
        parts.append(f"I also noticed:")
        for issue in email_issues:
            # Clean up issue text for email
            clean_issue = issue.replace('Missing ', 'no ').replace('Missing', 'no')
            parts.append(f"- {clean_issue}")
        parts.append(f"")
    
    # Search volume block - only if we have real data
    if has_search_data:
        parts.append(f"There are {search_volume} people searching for {business_type} services monthly in your area. Right now, you're only reaching an estimated {monthly_leads} of them.")
        parts.append(f"")
    
    parts.append(f"I help {business_type} businesses fix exactly these kinds of issues. Typical turnaround is 4-6 weeks.")
    parts.append(f"")
    parts.append(f"Would you be open to a quick 15-minute call this week? I can walk you through exactly what's happening and what I'd fix first — no obligation.")
    parts.append(f"")
    parts.append(f"Best,")
    parts.append(f"[Your Name]")
    parts.append(f"")
    
    # P.S. - mention social profiles if no email available
    contacts = analysis.get('contacts', {})
    social = contacts.get('social_profiles', {})
    has_email = contacts.get('emails') and len(contacts.get('emails', [])) > 0
    
    if not has_email and social:
        platforms = list(social.keys())
        if platforms:
            platform_list = ' or '.join(platforms[:2])
            parts.append(f"P.S. I also found your {platform_list} profile — happy to connect there if that's easier.")
        else:
            parts.append(f"P.S. Happy to send over the specific list of issues I found, even if now isn't the right time to talk.")
    else:
        parts.append(f"P.S. Happy to send over the specific list of issues I found, even if now isn't the right time to talk.")
    
    body = "\n".join(parts)
    
    return {
        'subject': subject,
        'body': body,
        'plain_text': f"Subject: {subject}\n\n{body}"
    }


def main():
    """Main workflow execution"""
    print("=" * 70)
    print("LEAD GENERATION WORKFLOW - ENHANCED")
    print("=" * 70)
    
    # Search queries
    searches = [
        {"query": "solar installation company in Los Angeles", "type": "solar"},
        {"query": "swimming pool repair in Austin Texas", "type": "pool"}
    ]
    
    all_leads = []
    
    for search in searches:
        print(f"\nSearching: {search['query']}")
        results = search_web(search['query'], limit=10)
        
        if results.get("success"):
            websites = results.get("data", {}).get("web", [])
            for i, site in enumerate(websites):
                url = site.get("url", "")
                
                # Skip social media and directories
                skip_domains = ["reddit.com", "yelp.com", "facebook.com", "twitter.com", 
                              "linkedin.com", "youtube.com", "energysage.com", "solarreviews.com",
                              "statesman.com", "ladwp.com"]
                if not any(domain in url for domain in skip_domains):
                    all_leads.append({
                        "url": url,
                        "title": site.get("title", ""),
                        "description": site.get("description", ""),
                        "type": search["type"],
                        "ranking_position": i + 1,
                        "search_query": search["query"]
                    })
    
    # Remove duplicates
    seen_urls = set()
    unique_leads = []
    for lead in all_leads:
        if lead["url"] not in seen_urls:
            seen_urls.add(lead["url"])
            unique_leads.append(lead)
    
    print(f"\nFound {len(unique_leads)} unique leads")
    
    # Analyze top leads
    print("\n" + "=" * 70)
    print("ANALYZING WEBSITES")
    print("=" * 70)
    
    analyzed_leads = []
    
    for i, lead in enumerate(unique_leads[:10], 1):
        print(f"\n[{i}/10] Analyzing: {lead['url']}")
        
        # Scrape website
        scrape_result = scrape_url(lead['url'])
        
        if scrape_result.get("success"):
            data = scrape_result.get("data", {})
            markdown = data.get("markdown", "")
            html = data.get("html", "")
            
            # Run comprehensive analysis
            analysis = analyze_website(
                url=lead['url'],
                html_content=html,
                markdown_content=markdown,
                ranking_position=lead['ranking_position'],
                search_query=lead['search_query']
            )
            
            analyzed_leads.append(analysis)
            
            # Save to database
            lead_id = db.add_lead({
                'url': lead['url'],
                'title': lead['title'],
                'type': lead['type'],
                'location': analysis.get('location'),
                'ranking_position': lead['ranking_position']
            })
            
            db.save_analysis(lead_id, analysis)
            
            # Save individual analysis
            filename = f"{OUTPUT_DIR}/analysis_{i}_{lead['type']}.json"
            with open(filename, 'w') as f:
                json.dump(analysis, f, indent=2)
            
            print(f"  Score: {analysis.get('seo_score', 0)}/100")
            print(f"  Issues: {len(analysis.get('issues', []))}")
            print(f"  Strengths: {len(analysis.get('strengths', []))}")
            print(f"  Ranking: #{lead['ranking_position']}")
            
            if analysis.get('contacts', {}).get('emails'):
                print(f"  Email: {analysis['contacts']['emails'][0]}")
            
        else:
            print(f"  Failed to scrape")
    
    # Generate proposals
    print("\n" + "=" * 70)
    print("GENERATING PROPOSALS")
    print("=" * 70)
    
    for i, analysis in enumerate(analyzed_leads, 1):
        proposal = generate_proposal(analysis)
        filename = f"{OUTPUT_DIR}/proposal_{i}_{analysis.get('type', 'unknown').replace(' ', '_')}.md"
        with open(filename, 'w') as f:
            f.write(proposal)
        print(f"Generated: {filename}")
    
    # Generate summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    stats = db.get_stats()
    
    summary = f"""
# Lead Generation Summary
## Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}

### Database Statistics
- Total Leads: {stats.get('total_leads', 0)}
- Solar Leads: {stats.get('solar_leads', 0)}
- Pool Leads: {stats.get('pool_leads', 0)}
- Contacted: {stats.get('contacted', 0)}
- Responded: {stats.get('responded', 0)}
- Closed: {stats.get('closed', 0)}

### Analysis Completed
- Websites Analyzed: {len(analyzed_leads)}
- Average SEO Score: {sum(a.get('seo_score', 0) for a in analyzed_leads) / max(len(analyzed_leads), 1):.1f}/100

### Top Issues Found
"""
    
    # Count common issues
    issue_counts = {}
    for analysis in analyzed_leads:
        for issue in analysis.get('issues', []):
            issue_counts[issue] = issue_counts.get(issue, 0) + 1
    
    for issue, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
        summary += f"- {issue}: {count} sites\n"
    
    summary += f"""
### Files Generated
- Analysis: {OUTPUT_DIR}/analysis_*.json
- Proposals: {OUTPUT_DIR}/proposal_*.md
- Database: leads.db

### Next Steps
1. Review proposals for each lead
2. Use contact information to reach out
3. Send personalized emails using the proposal
4. Track outreach in the database
"""
    
    with open(f"{OUTPUT_DIR}/summary.md", 'w') as f:
        f.write(summary)
    
    print(summary)
    
    # Export to JSON
    db.export_to_json(f"{OUTPUT_DIR}/leads_export.json")
    print(f"\nAll data exported to {OUTPUT_DIR}/leads_export.json")


if __name__ == "__main__":
    main()

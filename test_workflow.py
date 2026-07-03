#!/usr/bin/env python3
"""Test script for the lead generation workflow"""
from lead_generation_workflow import search_web, scrape_url, analyze_website

print("Testing search...")
results = search_web("solar installation company in Los Angeles", limit=2)

if results.get("success"):
    websites = results.get("data", {}).get("web", [])
    print(f"Found {len(websites)} results")
    
    for w in websites[:1]:
        url = w.get("url", "")
        title = w.get("title", "")
        print(f"\nTesting: {title}")
        print(f"URL: {url}")
        
        # Test scrape
        print("Scraping...")
        scrape = scrape_url(url)
        
        if scrape.get("success"):
            data = scrape.get("data", {})
            html = data.get("html", "")
            print(f"Got {len(html)} chars of HTML")
            
            # Test analysis
            analysis = analyze_website(
                url=url,
                html_content=html,
                markdown_content="",
                ranking_position=1,
                search_query="solar installation company in Los Angeles"
            )
            
            print(f"\nSEO Score: {analysis.get('seo_score', 0)}/100")
            print(f"Issues ({len(analysis.get('issues', []))}):")
            for issue in analysis.get("issues", [])[:5]:
                print(f"  - {issue}")
            print(f"Strengths ({len(analysis.get('strengths', []))}):")
            for strength in analysis.get("strengths", [])[:3]:
                print(f"  - {strength}")
            print(f"Contacts:")
            contacts = analysis.get("contacts", {})
            if contacts.get("emails"):
                print(f"  Email: {contacts['emails'][0]}")
            if contacts.get("phones"):
                print(f"  Phone: {contacts['phones'][0]}")
        else:
            print("Scrape failed")
else:
    print("Search failed")

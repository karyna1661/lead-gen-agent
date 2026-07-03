#!/usr/bin/env python3
"""
Lead Generation API Server
Runs the pipeline from the frontend with configurable parameters
"""
import json
import os
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from lead_generation_workflow import (
    search_web, scrape_url, analyze_website, generate_proposal, generate_email_draft,
    extract_location_from_query, extract_business_type_from_query
)
from database import LeadDatabase
from trends_analyzer import TrendsAnalyzer

# Use absolute path for output directory
OUTPUT_DIR = str(Path(__file__).parent / "leads_output")

# Use absolute path for database
db = LeadDatabase(db_path=str(Path(__file__).parent / "leads_output" / "leads.db"))
trends = TrendsAnalyzer()

# Track pipeline status
pipeline_status = {
    'running': False,
    'progress': 0,
    'total': 0,
    'current_url': '',
    'leads_found': 0,
    'error': None
}

BUSINESS_TYPES = [
    'solar', 'pool', 'plumbing', 'hvac', 'roofing', 
    'dentist', 'electrician', 'chiropractor', 'landscaping',
    'pest_control', 'cleaning', 'painting', 'flooring',
    'moving', 'storage', 'auto_repair', 'tire_shop',
    'car_wash', 'detailing', 'glass_repair'
]

SKIP_DOMAINS = [
    "reddit.com", "yelp.com", "facebook.com", "twitter.com",
    "linkedin.com", "youtube.com", "energysage.com", "solarreviews.com",
    "statesman.com", "ladwp.com", "google.com", "bing.com", "yahoo.com",
    "apple.com", "microsoft.com", "amazon.com", "wikipedia.org",
    "bbb.org", "angieslist.com", "homeadvisor.com", "thumbtack.com",
    "thumbtack.com", "angi.com", "porch.com", "nextdoor.com",
    "mapquest.com", "yellowpages.com", "superpages.com", "manta.com"
]


def run_pipeline(business_type, location, max_results=20):
    """Run the lead generation pipeline with configurable parameters"""
    global pipeline_status
    
    if pipeline_status['running']:
        return {'error': 'Pipeline already running'}
    
    pipeline_status = {
        'running': True,
        'progress': 0,
        'total': 0,
        'current_url': '',
        'leads_found': 0,
        'error': None
    }
    
    try:
        # Build search query based on business type and location
        query = f"{business_type} company in {location}"
        
        print(f"\n{'='*70}")
        print(f"RUNNING PIPELINE: {query}")
        print(f"{'='*70}")
        
        # Search for leads
        search_results = search_web(query, limit=max_results)
        
        if not search_results.get('success'):
            pipeline_status['error'] = f"Search failed: {search_results.get('error', 'Unknown error')}"
            pipeline_status['running'] = False
            return pipeline_status
        
        websites = search_results.get('data', {}).get('web', [])
        pipeline_status['total'] = len(websites)
        
        # Filter out directories and social media
        filtered_sites = []
        for site in websites:
            url = site.get('url', '')
            if not any(domain in url for domain in SKIP_DOMAINS):
                filtered_sites.append(site)
        
        print(f"Found {len(filtered_sites)} potential leads (filtered from {len(websites)})")
        
        analyzed_leads = []
        
        for i, site in enumerate(filtered_sites):
            url = site.get('url', '')
            pipeline_status['progress'] = i + 1
            pipeline_status['current_url'] = url
            
            print(f"\n[{i+1}/{len(filtered_sites)}] Analyzing: {url}")
            
            # Skip if already analyzed (append mode - skip duplicates)
            existing = db.get_lead_by_url(url)
            if existing:
                print(f"  Skipping - already in database")
                continue
            
            # Scrape website
            scrape_result = scrape_url(url)
            
            if scrape_result.get('success'):
                data = scrape_result.get('data', {})
                html = data.get('html', '')
                markdown = data.get('markdown', '')
                
                # Analyze website
                analysis = analyze_website(
                    url=url,
                    html_content=html,
                    markdown_content=markdown,
                    ranking_position=i + 1,
                    search_query=query
                )
                
                # Add business type and location to analysis
                analysis['business_type'] = business_type
                analysis['location'] = location
                
                # Get trend data
                opportunity = trends.analyze_opportunity(
                    business_type, 
                    location, 
                    i + 1
                )
                analysis['opportunity'] = opportunity
                
                # Save to database
                lead_id = db.add_lead({
                    'url': url,
                    'title': site.get('title', ''),
                    'type': business_type,
                    'location': location,
                    'ranking_position': i + 1
                })
                
                db.save_analysis(lead_id, analysis)
                
                # Generate proposal
                proposal = generate_proposal(analysis)
                filename = f"{OUTPUT_DIR}/proposal_{lead_id}_{business_type}.md"
                with open(filename, 'w') as f:
                    f.write(proposal)
                
                # Generate and save email draft
                email_draft = generate_email_draft(analysis)
                db.save_email_draft(lead_id, email_draft)
                
                analyzed_leads.append(analysis)
                pipeline_status['leads_found'] += 1
                
                print(f"  Score: {analysis.get('seo_score', 0)}/100")
                print(f"  Issues: {len(analysis.get('issues', []))}")
                print(f"  Contacts: {len(analysis.get('contacts', {}).get('emails', []))} emails")
            else:
                print(f"  Failed to scrape")
        
        # Export updated leads
        db.export_to_json(f"{OUTPUT_DIR}/leads_export.json")
        
        pipeline_status['running'] = False
        pipeline_status['current_url'] = ''
        
        print(f"\n{'='*70}")
        print(f"PIPELINE COMPLETE: {pipeline_status['leads_found']} new leads added")
        print(f"{'='*70}")
        
        return {
            'success': True,
            'leads_added': pipeline_status['leads_found'],
            'total_leads': db.get_stats()['total_leads']
        }
        
    except Exception as e:
        pipeline_status['error'] = str(e)
        pipeline_status['running'] = False
        print(f"Pipeline error: {e}")
        return {'error': str(e)}


class APIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the API"""
    
    def log_message(self, format, *args):
        pass  # Suppress default logging
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests"""
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path == '/api/status':
            self.send_json(pipeline_status)
        elif path == '/api/stats':
            stats = db.get_stats()
            self.send_json(stats)
        elif path == '/api/leads':
            leads = db.get_all_leads()
            self.send_json(leads)
        elif path == '/api/business-types':
            self.send_json(BUSINESS_TYPES)
        elif path.startswith('/api/email-draft/'):
            lead_id = path.split('/')[-1]
            try:
                lead_id = int(lead_id)
                draft = db.get_email_draft(lead_id)
                if draft:
                    self.send_json(draft)
                else:
                    self.send_json({'error': 'No email draft found'})
            except ValueError:
                self.send_error(400)
        else:
            self.send_error(404)
    
    def do_POST(self):
        """Handle POST requests"""
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path == '/api/run':
            # Get request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else b'{}'
            
            try:
                params = json.loads(body)
            except json.JSONDecodeError:
                params = {}
            
            business_type = params.get('business_type', 'solar')
            location = params.get('location', 'Los Angeles, CA')
            max_results = params.get('max_results', 20)
            
            # Run pipeline in background thread
            if not pipeline_status['running']:
                thread = threading.Thread(
                    target=run_pipeline,
                    args=(business_type, location, max_results),
                    daemon=True
                )
                thread.start()
                self.send_json({'message': 'Pipeline started', 'query': f"{business_type} in {location}"})
            else:
                self.send_json({'error': 'Pipeline already running'})
        elif path == '/api/mark-contacted':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else b'{}'
            
            try:
                params = json.loads(body)
                lead_id = params.get('lead_id')
                if lead_id:
                    db.update_outreach(lead_id, 'contacted')
                    self.send_json({'success': True})
                else:
                    self.send_json({'error': 'Missing lead_id'})
            except Exception as e:
                self.send_json({'error': str(e)})
        else:
            self.send_error(404)
    
    def send_json(self, data):
        """Send JSON response"""
        response = json.dumps(data)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(response.encode())


def run_server(port=8081):
    """Start the API server"""
    server = HTTPServer(('0.0.0.0', port), APIHandler)
    print(f"LeadGen API running on http://localhost:{port}")
    server.serve_forever()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8081)
    args = parser.parse_args()
    run_server(args.port)

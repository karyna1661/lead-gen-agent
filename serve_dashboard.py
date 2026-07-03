#!/usr/bin/env python3
"""Simple HTTP server to serve the lead gen dashboard with proper CORS"""
import http.server
import socketserver
import os
import webbrowser
import threading
from pathlib import Path

PORT = 8080
DIRECTORY = Path(__file__).parent / "leads_output"

class CORSHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)
    
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

def start_api_server():
    """Start the API server in a background thread"""
    try:
        from api_server import run_server
        run_server(8081)
    except Exception as e:
        print(f"API server error: {e}")

if __name__ == "__main__":
    os.chdir(DIRECTORY)
    
    # Start API server in background
    api_thread = threading.Thread(target=start_api_server, daemon=True)
    api_thread.start()
    
    # Start dashboard server
    with socketserver.TCPServer(("", PORT), CORSHandler) as httpd:
        print(f"Serving dashboard at http://localhost:{PORT}")
        print(f"API server running at http://localhost:8081")
        print(f"Opening browser...")
        webbrowser.open(f"http://localhost:{PORT}/index.html")
        httpd.serve_forever()

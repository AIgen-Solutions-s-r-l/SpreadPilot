"""
Mock service for testing watchdog functionality.
Can be made unhealthy by creating a file /tmp/unhealthy.
"""

import os
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            # Check if unhealthy flag exists
            if os.path.exists('/tmp/unhealthy'):
                self.send_response(503)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "unhealthy"}).encode())
                logger.info("Returning unhealthy status")
            else:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "healthy"}).encode())
                logger.info("Returning healthy status")
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress default logging
        pass

def main():
    server_address = ('', 8080)
    httpd = HTTPServer(server_address, HealthHandler)
    logger.info("Mock service started on port 8080")
    
    # Remove unhealthy flag on startup
    if os.path.exists('/tmp/unhealthy'):
        os.remove('/tmp/unhealthy')
    
    httpd.serve_forever()

if __name__ == '__main__':
    main()
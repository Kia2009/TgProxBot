from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import json

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "healthy"}).encode())
    
    def log_message(self, format, *args):
        pass  # Suppress HTTP logs

def start_health_server():
    import os
    port = int(os.environ.get('PORT', 8080))
    try:
        server = HTTPServer(('0.0.0.0', port), HealthHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        print(f"Health server started on 0.0.0.0:{port}")
        return server
    except Exception as e:
        print(f"Failed to start health server: {e}")
        return None
#!/usr/bin/env python3
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class MockBackendHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()

        response = {
            'service': 'mock-backend',
            'path': self.path,
            'method': 'GET',
            'headers': dict(self.headers)
        }
        self.wfile.write(json.dumps(response, indent=2).encode())

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()

        response = {
            'service': 'mock-backend',
            'path': self.path,
            'method': 'POST',
            'headers': dict(self.headers),
            'body': body
        }
        self.wfile.write(json.dumps(response, indent=2).encode())

    def log_message(self, format, *args):
        print(f"[BACKEND] {format % args}")

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', 8080), MockBackendHandler)
    print('[BACKEND] Mock backend server running on port 8080')
    server.serve_forever()

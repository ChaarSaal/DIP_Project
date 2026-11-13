"""
PixelSpec Standalone Local Web Application Server
Built using Python standard library http.server (ThreadingHTTPServer) with zero extra dependencies.
Provides RESTful APIs for real-time DIP inspection and interactive browser UI.
"""

import argparse
from email.parser import BytesParser
from email.policy import default
import io
import json
import os
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import numpy as np

from pixelspec.config import PROFILES
from pixelspec.pipeline.baseline import run_baseline_pipeline
from pixelspec.pipeline.advanced import run_advanced_pipeline
from pixelspec.pipeline.comparison import compare_pipelines
from pixelspec.utils.image_io import load_image_bytes, resize_keep_aspect
from pixelspec.utils.report_gen import generate_html_audit_report

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


class PixelSpecRequestHandler(BaseHTTPRequestHandler):
    server_version = "PixelSpec-Server/1.0"

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html_text: str, status: int = 200):
        body = html_text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            index_path = os.path.join(STATIC_DIR, "index.html")
            if os.path.exists(index_path):
                with open(index_path, "r", encoding="utf-8") as f:
                    self._send_html(f.read())
            else:
                self._send_html("<h1>PixelSpec Web UI not found</h1>", 404)
            return

        if path == "/api/profiles":
            profiles_data = {k: v.to_dict() for k, v in PROFILES.items()}
            self._send_json(profiles_data)
            return

        # Serve static assets (CSS, JS, images)
        rel_path = path.lstrip("/")
        file_path = os.path.join(STATIC_DIR, rel_path)
        if os.path.isfile(file_path):
            content_type = "text/plain"
            if file_path.endswith(".css"):
                content_type = "text/css"
            elif file_path.endswith(".js"):
                content_type = "application/javascript"
            elif file_path.endswith(".png"):
                content_type = "image/png"
            elif file_path.endswith(".jpg") or file_path.endswith(".jpeg"):
                content_type = "image/jpeg"
            elif file_path.endswith(".svg"):
                content_type = "image/svg+xml"

            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        self._send_json({"error": "Resource not found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/inspect":
            content_type = self.headers.get("Content-Type", "")
            content_length = int(self.headers.get("Content-Length", 0))

            if content_length == 0 or content_length > 25 * 1024 * 1024:
                self._send_json({"error": "Invalid payload size (Max 25MB allowed)."}, 400)
                return

            # Parse query params
            params = parse_qs(parsed.query)
            profile_key = params.get("profile", ["standard"])[0]
            mode = params.get("mode", ["advanced"])[0]

            profile = PROFILES.get(profile_key, PROFILES["standard"])

            # Read request body
            raw_body = self.rfile.read(content_length)

            # Handle multipart/form-data or raw octet-stream
            image_bytes = None
            filename = "upload.jpg"

            if "multipart/form-data" in content_type:
                try:
                    envelope = (
                        f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("latin1")
                        + raw_body
                    )
                    msg = BytesParser(policy=default).parsebytes(envelope)
                    for part in msg.iter_parts():
                        cd = part.get("Content-Disposition", "")
                        if 'name="file"' in cd or part.get_filename():
                            image_bytes = part.get_payload(decode=True)
                            filename = part.get_filename() or "upload.jpg"
                            break
                    if not image_bytes:
                        self._send_json({"error": "No 'file' field found in multipart upload."}, 400)
                        return
                except Exception as e:
                    self._send_json({"error": f"Failed to parse multipart upload: {str(e)}"}, 400)
                    return
            else:
                image_bytes = raw_body

            if not image_bytes:
                self._send_json({"error": "Empty image payload."}, 400)
                return

            try:
                rgb_img, notes = load_image_bytes(image_bytes)
                # Keep max dimension 1600 for high resolution inspection without excessive memory
                rgb_img = resize_keep_aspect(rgb_img, max_dimension=1600)
            except Exception as e:
                self._send_json({"error": f"Failed to parse image: {str(e)}"}, 400)
                return

            # Execute requested inspection mode
            try:
                if mode == "baseline":
                    res = run_baseline_pipeline(rgb_img, profile)
                elif mode == "comparison":
                    res = compare_pipelines(rgb_img, profile)
                else:
                    # Default is proposed advanced pipeline
                    res = run_advanced_pipeline(rgb_img, profile)

                res["filename"] = filename
                res["input_notes"] = notes
                res["dimensions"] = [int(rgb_img.shape[1]), int(rgb_img.shape[0])]

                self._send_json(res)
            except Exception as e:
                self._send_json({"error": f"Inspection processing failed: {str(e)}"}, 500)
            return

        if path == "/api/export-report":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(body)
                html_report = generate_html_audit_report(data, data.get("filename", "product_image.jpg"))
                self._send_html(html_report)
            except Exception as e:
                self._send_json({"error": f"Report generation failed: {str(e)}"}, 400)
            return

        self._send_json({"error": "Endpoint not recognized."}, 404)


def run_server(host: str = "127.0.0.1", port: int = 8500):
    server = ThreadingHTTPServer((host, port), PixelSpecRequestHandler)
    print("=" * 65)
    print(f" PixelSpec Inspector Server running at: http://{host}:{port}/")
    print(" Press Ctrl+C to stop the server.")
    print("=" * 65)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping PixelSpec Server...")
        server.server_close()


def main():
    parser = argparse.ArgumentParser(description="PixelSpec E-Commerce Image Quality Inspector")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind")
    parser.add_argument("--port", type=int, default=8500, help="Port to listen on (default: 8500)")
    args = parser.parse_args()
    run_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()

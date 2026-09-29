#!/usr/bin/env python3
# share.py — run on the Mac to send main.py to a Windows PC on the same network
import os
import signal
import socket
import subprocess
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8000
FILE_NAME = "main.py"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_PATH = os.path.join(BASE_DIR, FILE_NAME)


def lan_ip():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def free_port(port):
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return

    current_pid = os.getpid()
    pids = []
    for value in result.stdout.split():
        if value.isdigit() and int(value) != current_pid:
            pids.append(int(value))

    for pid in pids:
        print(f"Port {port} is in use by PID {pid}; stopping it.", flush=True)
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    if pids:
        time.sleep(0.5)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?", 1)[0]

        if path in ("/", "/index.html", f"/{FILE_NAME}"):
            self.send_file()
            return

        self.send_error(404, "File not found")

    def send_file(self):
        if not os.path.isfile(FILE_PATH):
            self.send_error(404, f"{FILE_NAME} was not found")
            return

        size = os.path.getsize(FILE_PATH)
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header(
            "Content-Disposition",
            f'attachment; filename="{FILE_NAME}"',
        )
        self.send_header("Content-Length", str(size))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

        with open(FILE_PATH, "rb") as handle:
            while True:
                chunk = handle.read(64 * 1024)
                if not chunk:
                    break
                self.wfile.write(chunk)

        print(f"[DOWNLOAD] {self.client_address[0]} downloaded {FILE_NAME}", flush=True)

    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {args[0]}", flush=True)


def main():
    if not os.path.isfile(FILE_PATH):
        print(f"ERROR: {FILE_PATH} was not found.")
        return

    free_port(PORT)
    try:
        server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    except OSError as error:
        print(f"Could not start server: {error}")
        return

    ip = lan_ip()
    print("=" * 55, flush=True)
    print(f"  Sharing:  {FILE_PATH}", flush=True)
    print(f"  On Windows, open:  http://{ip}:{PORT}/", flush=True)
    print("  The file downloads as soon as that link opens.", flush=True)
    print("=" * 55, flush=True)
    print("  Press Ctrl+C to stop", flush=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

import os
import signal
import socket
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8000
SETUP_FILE = "setup.exe"

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Download</title>
  <style>
    body {
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      font-family: system-ui, sans-serif;
      background: #f4f4f5;
    }

    .container {
      text-align: center;
      background: white;
      padding: 40px;
      border-radius: 16px;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
    }

    a {
      display: inline-block;
      margin-top: 15px;
      padding: 12px 20px;
      color: white;
      background: #2563eb;
      border-radius: 8px;
      text-decoration: none;
      font-size: 1.1rem;
    }

    a:hover {
      background: #1d4ed8;
    }
  </style>
</head>

<body>
  <div class="container">
    <h2>Setup Download</h2>
    <p>Click the button below to download the setup file.</p>

    <a href="/setup.exe" download>
      Download setup.exe
    </a>
  </div>
</body>
</html>
"""


def lan_ip():
    """Find the computer's LAN IP address."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def free_port(port):
    """Kill processes currently using the port."""
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True,
            text=True,
            check=False,
        )

        pids = []

        for value in result.stdout.split():
            if value.isdigit():
                pids.append(int(value))

        current_pid = os.getpid()

        for pid in pids:
            if pid == current_pid:
                continue

            print(
                f"Port {port} is being used by PID {pid}; stopping it...",
                flush=True,
            )

            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass

        if pids:
            time.sleep(0.5)

    except FileNotFoundError:
        # lsof isn't available; that's okay.
        pass


class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        path = self.path.split("?", 1)[0]

        # -----------------------------
        # Serve setup.exe
        # -----------------------------
        if path == "/setup.exe":

            if not os.path.isfile(SETUP_FILE):
                self.send_error(
                    404,
                    "setup.exe was not found on the server."
                )
                return

            try:
                file_size = os.path.getsize(SETUP_FILE)

                self.send_response(200)

                self.send_header(
                    "Content-Type",
                    "application/octet-stream"
                )

                self.send_header(
                    "Content-Disposition",
                    'attachment; filename="setup.exe"'
                )

                self.send_header(
                    "Content-Length",
                    str(file_size)
                )

                self.send_header(
                    "Cache-Control",
                    "no-cache"
                )

                self.end_headers()

                with open(SETUP_FILE, "rb") as file:
                    while True:
                        chunk = file.read(1024 * 1024)

                        if not chunk:
                            break

                        self.wfile.write(chunk)

                print(
                    f"[DOWNLOAD] {self.client_address[0]} downloaded "
                    f"{SETUP_FILE}",
                    flush=True,
                )

            except (BrokenPipeError, ConnectionResetError):
                print(
                    f"[DOWNLOAD] Client disconnected: "
                    f"{self.client_address[0]}",
                    flush=True,
                )

            return

        # -----------------------------
        # Serve the webpage
        # -----------------------------
        if path == "/" or path == "/index.html":

            body = PAGE.encode("utf-8")

            self.send_response(200)

            self.send_header(
                "Content-Type",
                "text/html; charset=utf-8"
            )

            self.send_header(
                "Content-Length",
                str(len(body))
            )

            self.send_header(
                "Cache-Control",
                "no-cache"
            )

            self.end_headers()

            self.wfile.write(body)

            return

        # -----------------------------
        # 404
        # -----------------------------
        self.send_error(404, "Page not found")

    def log_message(self, format, *args):
        print(
            f"[{self.log_date_time_string()}] {args[0]}",
            flush=True,
        )


def main():

    # Check setup.exe before starting.
    if not os.path.isfile(SETUP_FILE):
        print()
        print("ERROR: setup.exe was not found.")
        print()
        print("Put setup.exe in the same folder as this Python file.")
        print()
        return

    print()
    print("========================================")
    print("       Setup Download Server")
    print("========================================")
    print()

    free_port(PORT)

    server_address = ("0.0.0.0", PORT)

    try:
        server = ThreadingHTTPServer(
            server_address,
            Handler
        )
    except OSError as error:
        print(f"Could not start server: {error}")
        return

    ip = lan_ip()

    print("Server started successfully.")
    print()
    print(f"On this computer:")
    print(f"  http://127.0.0.1:{PORT}/")
    print()
    print("On another PC on the same Wi-Fi/LAN:")
    print(f"  http://{ip}:{PORT}/")
    print()
    print(f"Download URL:")
    print(f"  http://{ip}:{PORT}/setup.exe")
    print()
    print("Press Ctrl+C to stop the server.")
    print()

    try:
        server.serve_forever()

    except KeyboardInterrupt:
        print()
        print("Stopping server...")

    finally:
        server.shutdown()
        server.server_close()

        print("Server stopped.")


if __name__ == "__main__":
    main()

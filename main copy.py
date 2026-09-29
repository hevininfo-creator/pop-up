import os
import signal
import socket
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8000
PASSWORD = "Naitik"

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Notice</title>
  <style>
    body {
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      font-family: system-ui, sans-serif;
      background: #f4f4f5;
    }
    a {
      color: #1d4ed8;
      font-size: 1.25rem;
    }
  </style>
</head>
<body>
  <a id="open-link" href="#">Click here</a>
  <script>
    document.getElementById("open-link").addEventListener("click", (event) => {
      event.preventDefault();
      fetch("/alert");
    });
  </script>
</body>
</html>
"""

_alert_lock = threading.Lock()


def show_system_alert():
    if not _alert_lock.acquire(blocking=False):
        return

    try:
        while True:
            # CHANGED: two buttons — "Close" and "OK".
            # AppleScript returns the name of the clicked button
            # in `button returned of dlg`. We wrap the whole thing
            # so we can read both the button and the typed text.
            script = (
                'try\n'
                '  set dlg to display dialog "An unexpected error occurred. '
                'Please check your connection.\\n\\nEnter password to dismiss:" '
                'default answer "" with hidden answer with title "System Warning" '
                'buttons {"Close", "OK"} default button "OK" cancel button "Close"\n'
                '  set btn to button returned of dlg\n'
                '  set txt to text returned of dlg\n'
                '  return btn & "|" & txt\n'
                'on error number -128\n'
                '  return "Close|"\n'
                'end try'
            )

            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                check=False,
            )

            # CHANGED: parse the "button|text" output.
            output = result.stdout.strip()
            if "|" in output:
                button, typed = output.split("|", 1)
            else:
                button, typed = output, ""

            # CHANGED: only exit when the correct password is entered.
            # Clicking Close or OK (with wrong/empty text) → loop again.
            if typed.strip() == PASSWORD:
                break
            # else: loop and show the dialog again

    finally:
        _alert_lock.release()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.split("?", 1)[0] == "/alert":
            threading.Thread(target=show_system_alert, daemon=True).start()
            self.send_response(204)
            self.end_headers()
            return

        body = PAGE.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {args[0]}")


def lan_ip():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def free_port(port: int) -> None:
    """Kill any process currently holding the given port (macOS/Linux)."""
    try:
        out = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True, text=True, check=False,
        )
        pids = [int(p) for p in out.stdout.split() if p.strip().isdigit()]
        me = os.getpid()
        for pid in pids:
            if pid == me:
                continue
            print(f"Port {port} held by PID {pid}; killing it...", flush=True)
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        if pids:
            time.sleep(0.5)
    except FileNotFoundError:
        pass


def main():
    free_port(PORT)
    ThreadingHTTPServer.allow_reuse_address = True
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)

    print("Open this link on the other PC (same Wi-Fi):", flush=True)
    print(f"http://{lan_ip()}:{PORT}/", flush=True)
    print(f'Popup keeps reappearing until password "{PASSWORD}" is entered.', flush=True)
    print("Press Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
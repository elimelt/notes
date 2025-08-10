import http.server
import socketserver
import os
import socket
import sys
from pathlib import Path


PORT = 8000
DIRECTORY = "site"
DEFAULT_PAGE = "index.html"


class CustomHTTPHandler(http.server.SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.abspath(DIRECTORY), **kwargs)

    def log_message(self, format, *args):
        sys.stderr.write(f"{self.client_address[0]} - {format % args}\n")

    def handle(self):
        try:
            super().handle()
        except (socket.error, ConnectionResetError, BrokenPipeError) as e:
            self.log_message("Connection error: %s", str(e))

    def handle_one_request(self):
        try:
            super().handle_one_request()
        except (socket.error, ConnectionResetError, BrokenPipeError) as e:
            self.log_message("Connection error: %s", str(e))
            self.close_connection = True
        except Exception as e:
            self.log_message("Error handling request: %s", str(e))
            self.close_connection = True

    def translate_path(self, path):
        fs_path = super().translate_path(path)

        if os.path.isdir(fs_path):
            default_page_path = os.path.join(fs_path, DEFAULT_PAGE)
            if os.path.exists(default_page_path):
                return default_page_path

        return fs_path

    def send_error(self, code, message=None, explain=None):
        try:
            if code == 404:
                root_default = os.path.join(self.directory, DEFAULT_PAGE)
                if os.path.exists(root_default):
                    self.path = f"/{DEFAULT_PAGE}"
                    return self.do_GET()

            super().send_error(code, message, explain)
        except (socket.error, ConnectionResetError, BrokenPipeError) as e:
            self.log_message("Connection error during error response: %s", str(e))
            self.close_connection = True
        except Exception as e:
            self.log_message("Error sending error response: %s", str(e))
            self.close_connection = True


def run_server():
    absolute_directory = os.path.abspath(DIRECTORY)

    os.makedirs(absolute_directory, exist_ok=True)

    print(f"Current working directory: {os.getcwd()}")
    print(f"Serving directory: {absolute_directory}")

    print("\nFiles in the directory:")
    for item in os.listdir(absolute_directory):
        file_path = os.path.join(absolute_directory, item)
        file_type = "Directory" if os.path.isdir(file_path) else "File"
        print(f"  - {item} ({file_type})")
    print()

    socketserver.TCPServer.allow_reuse_address = True

    with socketserver.TCPServer(("", PORT), CustomHTTPHandler) as httpd:
        print(f"Starting HTTP server at http://localhost:{PORT}")
        print(f"Serving files from: {absolute_directory}")
        print(f"Press Ctrl+C to stop the server")

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server")
            httpd.server_close()


if __name__ == "__main__":
    run_server()

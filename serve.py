#!/usr/bin/env python3
import argparse
import json
import os
import re
import ssl
import webbrowser
from datetime import datetime
from http.client import RemoteDisconnected
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    import certifi
except ImportError:
    certifi = None


def normalize_open_path(raw_path: str) -> str:
    target = raw_path.strip().strip('"').strip("'").lstrip("/")
    target = re.sub(r"[^0-9A-Za-z._/\-]+$", "", target)
    return target


def normalize_asset_name(raw_name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", raw_name.lower())


def build_ssl_context() -> ssl.SSLContext:
    allow_insecure = os.getenv("GEMINI_INSECURE_SSL", "").lower() in {"1", "true", "yes"}
    if allow_insecure:
        return ssl._create_unverified_context()
    if certifi is not None:
        return ssl.create_default_context(cafile=certifi.where())
    return ssl.create_default_context()


def load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def build_lecture_list(base_dir: Path) -> list[dict]:
    html_dir = base_dir / "html"
    pdf_dir = base_dir / "pdfs"
    if not html_dir.exists():
        return []

    def sort_key(path: Path):
        match = re.search(r"^Lec[_ ]?(\d+)", path.stem, flags=re.IGNORECASE)
        lecture_no = int(match.group(1)) if match else 9999
        return (lecture_no, path.stem.lower())

    pdf_index: dict[str, Path] = {}
    if pdf_dir.exists():
        for pdf_file in pdf_dir.glob("*.pdf"):
            pdf_index.setdefault(normalize_asset_name(pdf_file.stem), pdf_file)

    lectures = []
    for html_file in sorted(html_dir.glob("*_interactive.html"), key=sort_key):
        stem = html_file.stem.removesuffix("_interactive")
        normalized = normalize_asset_name(stem)
        pdf_file = pdf_index.get(normalized)
        if pdf_file is None:
            guessed_pdf = pdf_dir / f"{stem.replace('_', ' ')}.pdf"
            if guessed_pdf.exists():
                pdf_file = guessed_pdf
        lectures.append(
            {
                "title": stem.replace("_", " "),
                "html_path": f"./{html_file.name}",
                "pdf_path": f"../pdfs/{pdf_file.name}" if pdf_file else None,
                "updated_at": datetime.fromtimestamp(html_file.stat().st_mtime).isoformat(timespec="seconds"),
            }
        )
    return lectures


class ProxyHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        path = self.path.split("?", 1)[0]
        if path.startswith("/api/") or path.endswith((".html", ".js", ".css", ".webmanifest")):
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
        super().end_headers()

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/api/lectures":
            lectures = build_lecture_list(Path.cwd())
            self.send_json({"lectures": lectures, "count": len(lectures)}, 200)
            return
        super().do_GET()

    def do_OPTIONS(self):
        if self.path != "/api/gemini":
            self.send_error(404, "Not Found")
            return
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.end_headers()

    def do_POST(self):
        if self.path != "/api/gemini":
            self.send_error(404, "Not Found")
            return

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            self.send_json(
                {"error": "GEMINI_API_KEY missing. Put it in .env.local before starting server."},
                500,
            )
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        body_bytes = self.rfile.read(content_length)
        try:
            payload = json.loads(body_bytes or b"{}")
        except json.JSONDecodeError:
            self.send_json({"error": "Invalid JSON payload."}, 400)
            return

        prompt = payload.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            self.send_json({"error": "Request must include non-empty 'prompt'."}, 400)
            return

        generation_config = payload.get("generationConfig")
        if not isinstance(generation_config, dict):
            generation_config = {"temperature": 0.7, "maxOutputTokens": 1024}

        model = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
        request_body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": generation_config,
        }
        gemini_url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        )
        req = Request(
            gemini_url,
            data=json.dumps(request_body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(req, timeout=90, context=build_ssl_context()) as resp:
                response_bytes = resp.read()
                status_code = resp.status
        except ssl.SSLCertVerificationError as err:
            self.send_json(
                {
                    "error": (
                        "Gemini SSL verification failed. Install local Python certificates "
                        "or set GEMINI_INSECURE_SSL=1 for local testing only. "
                        f"Details: {err}"
                    )
                },
                502,
            )
            return
        except RemoteDisconnected as err:
            self.send_json({"error": f"Gemini request failed: remote server disconnected ({err})."}, 502)
            return
        except HTTPError as err:
            response_bytes = err.read()
            if not response_bytes:
                response_bytes = json.dumps({"error": f"Gemini API error {err.code}"}).encode("utf-8")
            status_code = err.code
        except URLError as err:
            if isinstance(err.reason, ssl.SSLCertVerificationError):
                self.send_json(
                    {
                        "error": (
                            "Gemini SSL verification failed. Install local Python certificates "
                            "or set GEMINI_INSECURE_SSL=1 for local testing only. "
                            f"Details: {err.reason}"
                        )
                    },
                    502,
                )
                return
            self.send_json({"error": f"Gemini request failed: {err.reason}"}, 502)
            return

        self.send_response(status_code)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

    def send_json(self, payload: dict, status_code: int) -> None:
        response_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve static files and proxy Gemini requests.")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    parser.add_argument(
        "--open",
        dest="open_path",
        default="",
        help="Open this relative path in browser after startup, e.g. html/index.html",
    )
    args = parser.parse_args()

    load_env_file(Path(".env.local"))

    server = ThreadingHTTPServer(("0.0.0.0", args.port), ProxyHandler)
    print(f"✅ Serving at http://localhost:{args.port}")
    print("   Gemini proxy endpoint: POST /api/gemini")
    if args.open_path:
        target = normalize_open_path(args.open_path) or "html/index.html"
        if not Path(target).exists():
            print(f"⚠️ Open path not found: {args.open_path} -> {target}; opening root instead.")
            target = ""
        open_url = f"http://localhost:{args.port}/" + target
        print(f"   Opening: {open_url}")
        webbrowser.open_new_tab(open_url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

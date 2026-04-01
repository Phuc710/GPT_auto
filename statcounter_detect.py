import argparse
import json
import re
from html import unescape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen


STATCOUNTER_URL = "https://gs.statcounter.com/detect"
EXPECTED_STRONG_FIELDS = 12

# These presets follow the common Chrome on Android user-agent pattern.
# Exact values can vary a bit by Android build / Chrome version.
DEVICE_PRESETS = {
    "pixel_10_pro": {
        "label": "Pixel 10 Pro",
        "ua": (
            "Mozilla/5.0 (Linux; Android 16; Pixel 10 Pro Build/BP22.250124.009) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Mobile Safari/537.36"
        ),
    },
    "pixel_10": {
        "label": "Pixel 10",
        "ua": (
            "Mozilla/5.0 (Linux; Android 16; Pixel 10 Build/BP22.250124.009) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Mobile Safari/537.36"
        ),
    },
    "pixel_9": {
        "label": "Pixel 9",
        "ua": (
            "Mozilla/5.0 (Linux; Android 15; Pixel 9 Build/AP4A.250205.002) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Mobile Safari/537.36"
        ),
    },
    "pixel_9_pro": {
        "label": "Pixel 9 Pro",
        "ua": (
            "Mozilla/5.0 (Linux; Android 15; Pixel 9 Pro Build/AP4A.250205.002) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Mobile Safari/537.36"
        ),
    },
}


class DetectError(Exception):
    def __init__(self, error_type: str, message: str) -> None:
        super().__init__(message)
        self.error_type = error_type
        self.message = message


def build_error(error_type: str, message: str) -> dict:
    return {
        "type_result": error_type,
        "message": message,
    }


def resolve_user_agent(raw_ua: str | None, device_name: str | None) -> str:
    if raw_ua:
        return raw_ua

    if device_name:
        preset = DEVICE_PRESETS.get(device_name.lower())
        if preset:
            return preset["ua"]
        supported = ", ".join(sorted(DEVICE_PRESETS))
        raise DetectError("unknown_device", f"Device not supported. Try one of: {supported}")

    raise DetectError("short_data", "Please send enough data!")


def fetch_detection_html(user_agent: str, timeout: int = 20) -> str:
    query = urlencode({"useragent": user_agent})
    url = f"{STATCOUNTER_URL}?{query}"
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
        method="GET",
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace")
    except Exception as exc:
        raise DetectError("error", f"Can not connect to server: {exc}") from exc


def parse_detection_html(html: str) -> dict:
    strong_values = [
        unescape(match.strip())
        for match in re.findall(r"<strong>(.*?)</strong", html, flags=re.IGNORECASE | re.DOTALL)
    ]

    if len(strong_values) < EXPECTED_STRONG_FIELDS:
        raise DetectError("parse_error", "Unexpected response format from Statcounter")

    data = strong_values[:EXPECTED_STRONG_FIELDS]
    return {
        "type_result": "success",
        "data": {
            "browser_name": data[0],
            "browser_visit": data[1],
            "os_device": data[2],
            "vendor_device": data[3],
            "model_device": data[4],
            "screen_width_height": f"{data[5]}/{data[6]}",
            "desktop_view": data[7],
            "mobile_view": data[8],
            "table_view": data[9],
            "crawler/robot_view": data[10],
            "console_view": data[11],
        },
    }


def detect_user_agent(raw_ua: str | None = None, device_name: str | None = None) -> dict:
    user_agent = resolve_user_agent(raw_ua, device_name)
    html = fetch_detection_html(user_agent)
    result = parse_detection_html(html)
    preset = DEVICE_PRESETS.get(device_name.lower()) if device_name else None
    result["request"] = {
        "device": device_name,
        "device_label": preset["label"] if preset else None,
        "ua": user_agent,
    }
    if (
        preset
        and result["data"]["vendor_device"] == "Unknown"
        and result["data"]["model_device"] == "Unknown"
    ):
        result["note"] = (
            "Preset sent successfully, but Statcounter does not currently recognize this device model."
        )
    return result


class DetectHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path not in ("/", "/detect"):
            self.send_json(build_error("not_found", "Use /detect?ua=... or /detect?device=pixel_10_pro"), 404)
            return

        params = parse_qs(parsed.query)
        raw_ua = params.get("ua", [None])[0]
        device_name = params.get("device", [None])[0]

        try:
            payload = detect_user_agent(raw_ua=raw_ua, device_name=device_name)
            self.send_json(payload, 200)
        except DetectError as exc:
            self.send_json(build_error(exc.error_type, exc.message), 400)

    def log_message(self, format: str, *args) -> None:
        return

    def send_json(self, payload: dict, status_code: int) -> None:
        body = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Detect browser/device info from a raw user-agent using Statcounter."
    )
    parser.add_argument("--ua", help="Raw user-agent string")
    parser.add_argument(
        "--device",
        help=f"Preset device name: {', '.join(sorted(DEVICE_PRESETS))}",
    )
    parser.add_argument("--serve", action="store_true", help="Run a small local HTTP API")
    parser.add_argument("--list-devices", action="store_true", help="Print supported device presets")
    parser.add_argument("--host", default="127.0.0.1", help="Host for --serve mode")
    parser.add_argument("--port", type=int, default=8000, help="Port for --serve mode")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.list_devices:
        print(json.dumps({key: value["label"] for key, value in DEVICE_PRESETS.items()}, indent=2))
        return

    if args.serve:
        server = ThreadingHTTPServer((args.host, args.port), DetectHandler)
        print(f"Listening on http://{args.host}:{args.port}/detect")
        server.serve_forever()
        return

    try:
        payload = detect_user_agent(raw_ua=args.ua, device_name=args.device)
    except DetectError as exc:
        payload = build_error(exc.error_type, exc.message)

    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

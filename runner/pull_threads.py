#!/usr/bin/env python3
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

def http_get_json(url: str, token: str):
    req = urllib.request.Request(
        url,
        headers={
            "accept": "application/json",
            "authorization": f"Bearer {token}",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read().decode("utf-8", errors="replace")
            return resp.status, json.loads(data)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return e.code, {"error": "HTTPError", "status": e.code, "body": body}
    except Exception as e:
        return 0, {"error": "Exception", "message": str(e)}

def write_json(path: str, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://api-dev.ai.inhabit.work", help="API base URL")
    ap.add_argument("--product", required=True, help="Product UUID")
    ap.add_argument("--assistant", required=True, help="Assistant UUID")
    ap.add_argument("--outdir", default="reports", help="Output directory")
    args = ap.parse_args()

    token = os.getenv("INHABIT_TOKEN", "").strip()
    if not token:
        print("❌ Missing INHABIT_TOKEN env var.\nRun: export INHABIT_TOKEN='...'\n", file=sys.stderr)
        sys.exit(1)

    threads_url = f"{args.base}/products/{args.product}/assistants/{args.assistant}/threads"

    status, data = http_get_json(threads_url, token)

    if status in (401, 403):
        print(f"❌ Auth failed ({status}). Your token is missing/expired.", file=sys.stderr)
        write_json(os.path.join(args.outdir, "threads_error.json"), data)
        sys.exit(2)

    if status == 0:
        print("❌ Network/other error:", data, file=sys.stderr)
      e_json(os.path.join(args.outdir, "threads_error.json"), data)
        sys.exit(3)

    if status >= 400:
        print(f"❌ API error ({status}). Saved error json.", file=sys.stderr)
        write_json(os.path.join(args.outdir, "threads_error.json"), data)
        sys.exit(4)

    out_path = os.path.join(args.outdir, "threads.json")
    write_json(out_path, data)
    print(f"✅ Wrote {out_path}")

if __name__ == "__main__":
    main()

"""Validate the future public Caddyfile on the pinned VPS without activating it."""

from __future__ import annotations

import argparse
from pathlib import Path

from provision_vps_access import connect, run_script


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("host")
    parser.add_argument("fingerprint")
    parser.add_argument("private_key_file", type=Path)
    parser.add_argument("domain")
    args = parser.parse_args()
    if args.domain != "eglitisonline.com":
        raise SystemExit("Unexpected domain for this project")
    template = (Path(__file__).resolve().parents[1] / "deploy" / "Caddyfile.template").read_text(encoding="utf-8")
    caddyfile = template.replace("SITE_DOMAIN", args.domain)
    if "SITE_DOMAIN" in caddyfile:
        raise SystemExit("Unreplaced Caddyfile placeholder")
    client = connect(args.host, "deploy", args.private_key_file, args.fingerprint)
    try:
        print(run_script(client, caddyfile, command="sudo -n caddy validate --config /dev/stdin --adapter caddyfile"))
    finally:
        client.close()


if __name__ == "__main__":
    main()

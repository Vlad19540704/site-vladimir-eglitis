"""Run a reviewed local shell script on the project's pinned VPS as root."""

from __future__ import annotations

import argparse
from pathlib import Path

from provision_vps_access import connect, run_script


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("host")
    parser.add_argument("fingerprint")
    parser.add_argument("private_key_file", type=Path)
    parser.add_argument("script_file", type=Path)
    args = parser.parse_args()

    script = args.script_file.read_text(encoding="utf-8")
    client = connect(args.host, "deploy", args.private_key_file, args.fingerprint)
    print(run_script(client, script, command="sudo -n bash -s", timeout=900))
    client.close()


if __name__ == "__main__":
    main()

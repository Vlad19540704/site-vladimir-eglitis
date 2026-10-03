"""Upload the closed-index staging site to a loopback-only Caddy preview."""

from __future__ import annotations

import argparse
import hashlib
import posixpath
import subprocess
from pathlib import Path

from provision_vps_access import connect, run


ALLOWED_SUFFIXES = {".html", ".css", ".js", ".svg", ".webp", ".png", ".jpg", ".jpeg"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("host")
    parser.add_argument("fingerprint")
    parser.add_argument("private_key_file", type=Path)
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[1]
    site = repo / "site"
    dirty = subprocess.check_output(["git", "status", "--porcelain"], cwd=repo, text=True)
    if dirty.strip():
        raise SystemExit("Commit and verify changes before staging deployment")
    revision = subprocess.check_output(["git", "rev-parse", "--short=12", "HEAD"], cwd=repo, text=True).strip()
    files = sorted(
        path for path in site.rglob("*")
        if path.is_file() and (path.suffix.lower() in ALLOWED_SUFFIXES or path.name == "robots.txt")
    )
    if len([path for path in files if path.suffix == ".html"]) != 8:
        raise SystemExit("Unexpected HTML page count")
    root = "/srv/site/staging"
    release = posixpath.join(root, "releases", revision)
    temporary = release + ".tmp"

    client = connect(args.host, "deploy", args.private_key_file, args.fingerprint)
    sftp = client.open_sftp()
    sftp.mkdir(temporary)
    directories = sorted({posixpath.dirname(str(path.relative_to(site)).replace("\\", "/")) for path in files})
    for directory in directories:
        if directory and directory != ".":
            parts = directory.split("/")
            for index in range(1, len(parts) + 1):
                target = posixpath.join(temporary, *parts[:index])
                try:
                    sftp.mkdir(target)
                except OSError:
                    pass
    total = 0
    for path in files:
        relative = str(path.relative_to(site)).replace("\\", "/")
        destination = posixpath.join(temporary, relative)
        data = path.read_bytes()
        sftp.put(str(path), destination)
        with sftp.open(destination, "rb") as remote:
            remote_hash = hashlib.sha256(remote.read()).digest()
        if remote_hash != hashlib.sha256(data).digest():
            raise SystemExit(f"Upload checksum mismatch: {relative}")
        total += len(data)
    sftp.close()
    run(client, f"mv -T {temporary} {release} && ln -sfn {release} {root}/current.next && mv -Tf {root}/current.next {root}/current")
    print(f"Staging release {revision}: {len(files)} files, {total} bytes, upload hashes verified")
    print(run(client, "curl -fsSI http://127.0.0.1:8081/ | head -n 12"))
    client.close()


if __name__ == "__main__":
    main()

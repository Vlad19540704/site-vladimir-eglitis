"""Encrypt an off-server staging backup and verify a full test restore.

The backup contains only public site assets, the active Caddyfile, and the
deployment runbook. Its AES-256 key stays outside Git and OneDrive.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import secrets
import subprocess
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from provision_vps_access import connect, run


MAGIC = b"SITEBACKUP1"
AAD = b"eglitisonline-staging-v1"
ALLOWED_SUFFIXES = {".html", ".css", ".js", ".svg", ".webp", ".png", ".jpg", ".jpeg"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("host")
    parser.add_argument("fingerprint")
    parser.add_argument("private_key_file", type=Path)
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[1]
    revision = subprocess.check_output(["git", "rev-parse", "--short=12", "HEAD"], cwd=repo, text=True).strip()
    site = repo / "site"
    files = {
        "site/" + path.relative_to(site).as_posix(): path.read_bytes()
        for path in site.rglob("*")
        if path.is_file() and (path.suffix.lower() in ALLOWED_SUFFIXES or path.name == "robots.txt")
    }
    client = connect(args.host, "deploy", args.private_key_file, args.fingerprint)
    files["server/Caddyfile"] = run(client, "sudo -n cat /etc/caddy/Caddyfile").encode("utf-8") + b"\n"
    client.close()
    files["docs/RUNBOOK.md"] = (repo / "deploy" / "RUNBOOK.md").read_bytes()
    manifest = {
        "revision": revision,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "files": {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())},
    }
    files["manifest.json"] = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")

    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode="w:gz") as tar:
        for name, data in sorted(files.items()):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o644
            tar.addfile(info, io.BytesIO(data))

    key_file = Path.home() / ".ssh" / "site_eglitisonline_backup_aesgcm.key"
    if key_file.exists():
        key = key_file.read_bytes()
    else:
        key = secrets.token_bytes(32)
        key_file.write_bytes(key)
    if len(key) != 32:
        raise SystemExit("Invalid local backup key")

    backup_dir = repo.parent / "backups"
    backup_dir.mkdir(exist_ok=True)
    nonce = secrets.token_bytes(12)
    encrypted = MAGIC + nonce + AESGCM(key).encrypt(nonce, archive.getvalue(), AAD)
    backup_path = backup_dir / f"staging-{revision}-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.sitebak"
    backup_path.write_bytes(encrypted)

    # Read the saved artifact, decrypt it, restore to an isolated directory,
    # and compare every restored file with the manifest before cleanup.
    saved = backup_path.read_bytes()
    if not saved.startswith(MAGIC):
        raise SystemExit("Invalid backup header")
    offset = len(MAGIC)
    plaintext = AESGCM(key).decrypt(saved[offset:offset + 12], saved[offset + 12:], AAD)
    with tempfile.TemporaryDirectory(prefix="restore-check-", dir=backup_dir) as temp:
        restore_root = Path(temp).resolve()
        if not restore_root.is_relative_to(backup_dir.resolve()):
            raise SystemExit("Restore path escaped backup directory")
        with tarfile.open(fileobj=io.BytesIO(plaintext), mode="r:gz") as tar:
            for member in tar.getmembers():
                parts = PurePosixPath(member.name).parts
                if member.isdir() or not parts or any(part in ("", ".", "..") for part in parts):
                    raise SystemExit("Unsafe archive member")
                target = restore_root.joinpath(*parts)
                if not target.resolve().is_relative_to(restore_root):
                    raise SystemExit("Restore path escaped temporary directory")
                target.parent.mkdir(parents=True, exist_ok=True)
                source = tar.extractfile(member)
                if source is None:
                    raise SystemExit("Missing archive file content")
                target.write_bytes(source.read())
        restored_manifest = json.loads((restore_root / "manifest.json").read_text(encoding="utf-8"))
        for name, expected in restored_manifest["files"].items():
            actual = hashlib.sha256((restore_root / name).read_bytes()).hexdigest()
            if actual != expected:
                raise SystemExit(f"Restore checksum mismatch: {name}")
    print(f"PASS: encrypted backup and test restore, {len(manifest['files'])} files, {backup_path}")


if __name__ == "__main__":
    main()

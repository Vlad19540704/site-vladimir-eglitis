"""Encrypt an off-server backup of the active server files and test restoration.

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
import sys
import tarfile
import tempfile
import re
import stat
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from provision_vps_access import connect, run

sys.stdout.reconfigure(encoding='utf-8')


MAGIC = b"SITEBACKUP1"
AAD = b"eglitisonline-staging-v1"
ALLOWED_SUFFIXES = {".html", ".css", ".js", ".svg", ".webp", ".png", ".jpg", ".jpeg"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("host")
    parser.add_argument("fingerprint")
    parser.add_argument("private_key_file", type=Path)
    parser.add_argument("--production", action="store_true")
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[1]
    client = connect(args.host, "deploy", args.private_key_file, args.fingerprint)
    active = '/srv/site/current' if args.production else '/srv/site/staging/current'
    revision = PurePosixPath(run(client, 'readlink ' + active).strip()).name
    if not re.fullmatch(r'[0-9a-f]{12}', revision):
        raise SystemExit('Unexpected active server revision')
    files = {}
    sftp = client.open_sftp()
    try:
        def download(directory, relative=''):
            for item in sftp.listdir_attr(directory):
                if item.filename in ('.', '..') or '/' in item.filename:
                    raise SystemExit('Unsafe server filename')
                remote = directory + '/' + item.filename
                rel = relative + item.filename
                if stat.S_ISDIR(item.st_mode):
                    download(remote, rel + '/')
                elif stat.S_ISREG(item.st_mode):
                    with sftp.open(remote, 'rb') as source:
                        files['site/' + rel] = source.read()
                else:
                    raise SystemExit('Unexpected symlink or special file in release')
        download(active)
    finally:
        sftp.close()
    if args.production:
        remote_manifest = json.loads(files['site/release-manifest.json'])
        if not remote_manifest['revision'].startswith(revision):
            raise SystemExit('Server revision and manifest disagree')
        for rel, expected in remote_manifest['files'].items():
            if hashlib.sha256(files['site/' + rel]).hexdigest() != expected:
                raise SystemExit('Active production checksum mismatch: ' + rel)
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
    environment = 'production' if args.production else 'staging'
    backup_path = backup_dir / f"{environment}-{revision}-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.sitebak"
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

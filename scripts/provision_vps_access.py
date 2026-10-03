"""Prepare an isolated VDSina VPS for key-only access.

The expected SSH host fingerprint is pinned. No password or private key is
written to the repository or the server.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
from pathlib import Path

import paramiko


class PinnedHostKey(paramiko.MissingHostKeyPolicy):
    def __init__(self, fingerprint: str):
        self.fingerprint = fingerprint.removeprefix("SHA256:")

    def missing_host_key(self, client, hostname, key):
        actual = base64.b64encode(hashlib.sha256(key.asbytes()).digest()).decode().rstrip("=")
        if actual != self.fingerprint:
            raise paramiko.SSHException(f"Unexpected SSH host key for {hostname}")
        client.get_host_keys().add(hostname, key.get_name(), key)


def connect(host: str, user: str, key_file: Path, fingerprint: str) -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(PinnedHostKey(fingerprint))
    client.connect(
        host,
        username=user,
        pkey=paramiko.Ed25519Key.from_private_key_file(str(key_file)),
        timeout=20,
    )
    return client


def run(client: paramiko.SSHClient, command: str) -> str:
    _, stdout, stderr = client.exec_command(command, timeout=120)
    output = stdout.read().decode(errors="replace")
    error = stderr.read().decode(errors="replace")
    if stdout.channel.recv_exit_status() != 0:
        raise SystemExit(f"Remote command failed: {error[-2000:]}")
    return output.strip()


def run_script(
    client: paramiko.SSHClient,
    script: str,
    command: str = "bash -s",
    timeout: int = 120,
) -> str:
    stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
    stdin.write(script)
    stdin.channel.shutdown_write()
    output = stdout.read().decode(errors="replace")
    error = stderr.read().decode(errors="replace")
    if stdout.channel.recv_exit_status() != 0:
        raise SystemExit(f"Remote script failed: {error[-2000:]}")
    return output.strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("host")
    parser.add_argument("fingerprint")
    parser.add_argument("private_key_file", type=Path)
    parser.add_argument("public_key_file", type=Path)
    args = parser.parse_args()

    public_key = args.public_key_file.read_text(encoding="ascii").strip()
    if not public_key.startswith("ssh-ed25519 "):
        raise SystemExit("Expected Ed25519 public key")

    root = connect(args.host, "root", args.private_key_file, args.fingerprint)
    sftp = root.open_sftp()
    sftp.put(str(args.public_key_file), "/tmp/site-deploy.pub")
    sftp.close()
    setup = """set -eu
id deploy >/dev/null 2>&1 || useradd -m -s /bin/bash deploy
passwd -l deploy >/dev/null
install -d -o deploy -g deploy -m 700 /home/deploy/.ssh
install -o deploy -g deploy -m 600 /tmp/site-deploy.pub /home/deploy/.ssh/authorized_keys
usermod -aG sudo deploy
printf '%s\\n' 'deploy ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/site-deploy
chmod 440 /etc/sudoers.d/site-deploy
visudo -cf /etc/sudoers.d/site-deploy >/dev/null
rm -f /tmp/site-deploy.pub
"""
    print(run_script(root, setup))
    root.close()

    deploy = connect(args.host, "deploy", args.private_key_file, args.fingerprint)
    print(run(deploy, "id -un && sudo -n id -un"))
    deploy.close()


if __name__ == "__main__":
    main()

"""Install a local SSH public key using a one-time VDSina root password.

The password is read from a temporary file outside the repository. This script
never logs it and does not persist it on the server.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import shlex
from pathlib import Path

import paramiko


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("host")
    parser.add_argument("password_file", type=Path)
    parser.add_argument("public_key_file", type=Path)
    parser.add_argument("private_key_file", type=Path)
    args = parser.parse_args()

    password = args.password_file.read_text(encoding="utf-8").strip()
    public_key = args.public_key_file.read_text(encoding="ascii").strip()
    if not public_key.startswith("ssh-ed25519 "):
        raise SystemExit("Expected an Ed25519 public key")

    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(args.host, username="root", password=password, timeout=20)
    host_key = client.get_transport().get_remote_server_key()
    fingerprint = base64.b64encode(hashlib.sha256(host_key.asbytes()).digest()).decode().rstrip("=")
    print(f"Connected to {args.host}; host key SHA256:{fingerprint}")

    quoted = shlex.quote(public_key)
    command = (
        "umask 077; mkdir -p /root/.ssh; touch /root/.ssh/authorized_keys; "
        f"grep -qxF {quoted} /root/.ssh/authorized_keys || "
        f"printf '%s\\n' {quoted} >> /root/.ssh/authorized_keys; "
        "chmod 700 /root/.ssh; chmod 600 /root/.ssh/authorized_keys"
    )
    _, stdout, stderr = client.exec_command(command)
    if stdout.channel.recv_exit_status() != 0:
        raise SystemExit(f"Key installation failed: {stderr.read().decode()}")
    client.close()

    key = paramiko.Ed25519Key.from_private_key_file(str(args.private_key_file))
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(args.host, username="root", pkey=key, timeout=20)
    _, stdout, stderr = client.exec_command("id -un; cat /etc/os-release | head -n 2")
    output = stdout.read().decode().strip()
    if stdout.channel.recv_exit_status() != 0:
        raise SystemExit(f"Key login verification failed: {stderr.read().decode()}")
    print(output)
    client.close()


if __name__ == "__main__":
    main()

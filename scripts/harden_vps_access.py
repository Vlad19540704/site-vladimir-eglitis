"""Disable password/root SSH after verified deploy key access."""

from __future__ import annotations

import argparse
from pathlib import Path

import paramiko

from provision_vps_access import connect, run, run_script


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("host")
    parser.add_argument("fingerprint")
    parser.add_argument("private_key_file", type=Path)
    args = parser.parse_args()

    deploy = connect(args.host, "deploy", args.private_key_file, args.fingerprint)
    print(run(deploy, "sudo -n id -un"))
    setup = """set -eu
sudo tee /etc/ssh/sshd_config.d/00-site.conf >/dev/null <<'EOF'
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
PubkeyAuthentication yes
EOF
sudo sshd -t
sudo systemctl reload ssh
"""
    run_script(deploy, setup)
    deploy.close()

    check = connect(args.host, "deploy", args.private_key_file, args.fingerprint)
    print(run(check, "sudo sshd -T | grep -E '^(passwordauthentication|kbdinteractiveauthentication|permitrootlogin|pubkeyauthentication) '"))
    run_script(check, """set -eu
if sudo test -f /root/.ssh/authorized_keys; then
  sudo sh -c "grep -v 'site-eglitisonline' /root/.ssh/authorized_keys > /root/.ssh/authorized_keys.site-clean || true"
  sudo install -m 600 /root/.ssh/authorized_keys.site-clean /root/.ssh/authorized_keys
  sudo rm -f /root/.ssh/authorized_keys.site-clean
fi
""")
    check.close()

    try:
        root = connect(args.host, "root", args.private_key_file, args.fingerprint)
    except paramiko.AuthenticationException:
        print("Root SSH key login correctly denied")
    else:
        root.close()
        raise SystemExit("Root SSH key login unexpectedly allowed")


if __name__ == "__main__":
    main()

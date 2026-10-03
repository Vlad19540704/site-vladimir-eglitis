#!/usr/bin/env bash
# Run on the project's new VPS only, after key-only deploy access is verified.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a
log=/var/log/site-bootstrap.log
touch "$log"
trap 'status=$?; echo "bootstrap failed ($status)"; tail -n 50 "$log"; exit "$status"' ERR

apt-get -o DPkg::Lock::Timeout=180 update >>"$log" 2>&1
apt-get -o DPkg::Lock::Timeout=180 upgrade -y >>"$log" 2>&1
apt-get -o DPkg::Lock::Timeout=180 install -y \
  unattended-upgrades ufw debian-keyring debian-archive-keyring \
  apt-transport-https curl gnupg ca-certificates >>"$log" 2>&1

curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
  | gpg --dearmor --yes -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
  > /etc/apt/sources.list.d/caddy-stable.list
chmod o+r /usr/share/keyrings/caddy-stable-archive-keyring.gpg \
  /etc/apt/sources.list.d/caddy-stable.list
apt-get -o DPkg::Lock::Timeout=180 update >>"$log" 2>&1
apt-get -o DPkg::Lock::Timeout=180 install -y caddy >>"$log" 2>&1

# The default welcome site is not part of this project.
systemctl stop caddy
systemctl disable caddy >/dev/null

ufw default deny incoming >>"$log" 2>&1
ufw default allow outgoing >>"$log" 2>&1
ufw allow 22/tcp >>"$log" 2>&1
ufw --force enable >>"$log" 2>&1

cat >/etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
EOF
systemctl enable --now apt-daily.timer apt-daily-upgrade.timer

printf 'caddy: '; caddy version
printf 'firewall: '; ufw status | head -n 3 | tr '\n' ' '; echo
printf 'security timer: '; systemctl is-enabled apt-daily-upgrade.timer
printf 'ssh: '; sshd -T | grep -E '^(passwordauthentication|permitrootlogin) '

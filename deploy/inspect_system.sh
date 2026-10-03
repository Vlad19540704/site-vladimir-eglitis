#!/usr/bin/env bash
set +e
echo "Caddy:"; caddy version; systemctl is-enabled caddy; systemctl is-active caddy
echo "Firewall:"; ufw status verbose
echo "Security timer:"; systemctl is-enabled apt-daily-upgrade.timer
echo "Reboot required:"; if [ -e /var/run/reboot-required ]; then cat /var/run/reboot-required; else echo no; fi
echo "SSH:"; /usr/sbin/sshd -T | grep -E '^(passwordauthentication|permitrootlogin) '
echo "Preview listener:"; ss -tlnp | grep -E '(:8081|:80|:443)' || true
echo "Caddy status:"; systemctl status caddy --no-pager -l | tail -n 18
echo "Recent bootstrap log:"; tail -n 20 /var/log/site-bootstrap.log
exit 0

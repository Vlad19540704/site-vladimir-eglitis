#!/usr/bin/env bash
# Read-only health check for the private, pre-publication VPS stage.
set -euo pipefail

test "$(systemctl is-active caddy)" = active
test "$(sudo -n ufw status | sed -n '1p')" = 'Status: active'
test "$(systemctl is-enabled apt-daily-upgrade.timer)" = enabled
test "$(curl --max-time 5 --silent --output /dev/null --write-out '%{http_code}' http://127.0.0.1:8081/)" = 200
test "$(curl --max-time 5 --silent --head http://127.0.0.1:8081/ | tr -d '\r' | grep -i '^x-robots-tag:' | head -n 1)" = 'X-Robots-Tag: noindex, nofollow'
test -L /srv/site/staging/current
test -f /srv/site/staging/current/index.html

free_kib=$(df -Pk / | awk 'NR==2 {print $4}')
test "$free_kib" -ge 1048576

listeners=$(sudo -n ss -H -tln)
printf '%s\n' "$listeners" | grep -q '127.0.0.1:8081'
if printf '%s\n' "$listeners" | grep -Eq '(^|[[:space:]])([^[:space:]]+:)?(80|443)[[:space:]]'; then
    echo 'Unexpected public web listener before launch' >&2
    exit 1
fi

printf 'PASS: Caddy, UFW, automatic updates, private HTTP 200/noindex, active release; free disk %s KiB\n' "$free_kib"

#!/usr/bin/env bash
# Private preview: reachable only through an SSH tunnel, never from the public IP.
set -euo pipefail
install -d -o deploy -g deploy -m 755 /srv/site
install -d -o deploy -g deploy -m 755 /srv/site/staging
install -d -o deploy -g deploy -m 755 /srv/site/staging/releases

cat >/etc/caddy/Caddyfile <<'EOF'
http://127.0.0.1:8081 {
    bind 127.0.0.1
    root * /srv/site/staging/current
    encode zstd gzip
    header {
        X-Robots-Tag "noindex, nofollow"
        X-Content-Type-Options nosniff
        Referrer-Policy no-referrer
        X-Frame-Options DENY
        -Server
    }
    file_server
}
EOF
caddy validate --config /etc/caddy/Caddyfile
systemctl enable --now caddy
systemctl reload caddy
printf 'caddy: '; systemctl is-active caddy
printf 'listener: '; ss -tln | grep '127.0.0.1:8081'

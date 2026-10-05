"""Publish a verified GitHub release on the isolated site VPS, with rollback."""

import argparse
import hashlib
import json
from pathlib import Path
import posixpath
import re
import shlex
import subprocess

from git_release_guard import published_revision
from provision_vps_access import connect, run, run_script
from verify_release import verify


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('host')
    parser.add_argument('fingerprint')
    parser.add_argument('private_key_file', type=Path)
    parser.add_argument('artifact', type=Path)
    parser.add_argument('--activate', action='store_true', help='Open public HTTPS after checking the approved release')
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    revision = published_revision(repo)
    manifest = verify(args.artifact.resolve(), repo / 'site')
    domain = manifest['domain']
    if not re.fullmatch(r'[a-z0-9.-]+', domain):
        raise SystemExit('Invalid release domain')
    if manifest['preview'] or manifest['revision'] != revision or not manifest['published_on']:
        raise SystemExit('Production requires an approved artifact of the published GitHub HEAD')
    # Recheck the private approval even when an artifact was built earlier.
    approval = json.loads((repo / 'release_approval.json').read_text(encoding='utf-8'))
    required = ('domain_owned', 'public_launch_approved', 'contacts_verified', 'real_photo_approved',
                'ruble_terms_verified', 'education_verified', 'about_text_approved',
                'legal_terms_approved', 'privacy_policy_approved', 'article_dates_confirmed', 'visual_approved')
    if any(approval.get(key) is not True for key in required):
        raise SystemExit('Production approval is incomplete')
    if args.artifact.resolve() != (repo / 'release' / domain).resolve():
        raise SystemExit('Use the deterministic release output for this domain')
    subprocess.run(['python', str(repo / 'scripts/build_release.py'), '--domain', domain,
                    '--checklist', str(repo / 'release_approval.json'),
                    '--published-on', manifest['published_on']], cwd=repo, check=True)
    manifest = verify(args.artifact.resolve(), repo / 'site')
    client = connect(args.host, 'deploy', args.private_key_file, args.fingerprint)
    release = '/srv/site/releases/' + revision[:12]
    temporary = release + '.tmp'
    candidate = release + '-Caddyfile'
    run_script(client, 'set -eu\ninstall -d -o deploy -g deploy /srv/site/releases\n', command='sudo -n bash -s')
    sftp = client.open_sftp()
    try:
        files = {**manifest['files'], 'release-manifest.json': hashlib.sha256(
            (args.artifact / 'release-manifest.json').read_bytes()).hexdigest()}
        try:
            sftp.stat(release)
            already_prepared = True
        except FileNotFoundError:
            already_prepared = False
            sftp.mkdir(temporary)
        for rel, digest in sorted(files.items()):
            destination = posixpath.join(release if already_prepared else temporary, rel)
            parent = posixpath.dirname(destination)
            if parent != temporary and not already_prepared:
                try:
                    sftp.mkdir(parent)
                except OSError:
                    pass
            if not already_prepared:
                sftp.put(str(args.artifact / rel), destination)
            with sftp.open(destination, 'rb') as remote:
                if hashlib.sha256(remote.read()).hexdigest() != digest:
                    raise SystemExit('Remote checksum mismatch: ' + rel)
        config = (repo / 'deploy/Caddyfile.template').read_text(encoding='utf-8').replace('SITE_DOMAIN', domain)
        with sftp.open(candidate, 'w') as remote:
            remote.write(config)
    finally:
        sftp.close()
    if not already_prepared:
        run(client, f'mv -T {temporary} {release}')
    print(f'Prepared {revision[:12]}: {len(files)} uploaded files, every SHA-256 verified')
    if not args.activate:
        print('Prepared only. Public listener and current production release unchanged.')
        client.close()
        return
    activation = f'''set -eu
release={shlex.quote(release)}
candidate={shlex.quote(candidate)}
previous=$(readlink /srv/site/current || true)
backup=/etc/caddy/Caddyfile.before-{revision[:12]}
cp /etc/caddy/Caddyfile "$backup"
caddy validate --config "$candidate" --adapter caddyfile
ln -sfn "$release" /srv/site/current.next
mv -Tf /srv/site/current.next /srv/site/current
rollback() {{
    cp "$backup" /etc/caddy/Caddyfile
    if [ -n "$previous" ]; then
        ln -sfn "$previous" /srv/site/current
    else
        rm -f /srv/site/current
        ufw delete allow 80/tcp >/dev/null || true
        ufw delete allow 443/tcp >/dev/null || true
    fi
    systemctl reload caddy
}}
trap 'rollback' ERR
install -m 644 "$candidate" /etc/caddy/Caddyfile
ufw allow 80/tcp >/dev/null
ufw allow 443/tcp >/dev/null
systemctl reload caddy
curl --retry 8 --retry-delay 4 --retry-all-errors --max-time 20 -fsS https://{domain}/ -o /tmp/site-production-check.html
grep -q 'index,follow' /tmp/site-production-check.html
curl -fsS https://{domain}/sitemap.xml >/dev/null
trap - ERR
readlink /srv/site/current
'''
    active = run_script(client, activation, command='sudo -n bash -s', timeout=180)
    if release not in active.splitlines():
        raise SystemExit('Activation did not confirm the expected server release')
    # Check the served files after activation, including canonical and robots metadata.
    sftp = client.open_sftp()
    try:
        for rel, digest in manifest['files'].items():
            with sftp.open('/srv/site/current/' + rel, 'rb') as remote:
                if hashlib.sha256(remote.read()).hexdigest() != digest:
                    raise SystemExit('Post-activation parity failed: ' + rel)
    finally:
        sftp.close()
        client.close()
    print(f'Production {revision[:12]} active with valid HTTPS; GitHub/artifact/server parity verified')


if __name__ == '__main__':
    main()

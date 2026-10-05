"""Read-only production health and published GitHub/server parity verification."""

import argparse
import hashlib
import json
from pathlib import Path
import socket
import ssl
import subprocess
import time
from provision_vps_access import connect, run


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('host')
    parser.add_argument('fingerprint')
    parser.add_argument('private_key_file',type=Path)
    parser.add_argument('--branch',default='master')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    remote=subprocess.check_output(['git','ls-remote','--heads','origin','refs/heads/'+args.branch],cwd=root,text=True).split()[0]
    client=connect(args.host,'deploy',args.private_key_file,args.fingerprint)
    sftp=client.open_sftp()
    try:
        with sftp.open('/srv/site/current/release-manifest.json','rb') as f:manifest=json.loads(f.read())
        assert manifest['revision']==remote,'GitHub branch and active production differ'
        assert run(client,'readlink /srv/site/current').strip().endswith('/'+remote[:12])
        for rel,digest in manifest['files'].items():
            with sftp.open('/srv/site/current/'+rel,'rb') as f:
                assert hashlib.sha256(f.read()).hexdigest()==digest,'Server file differs: '+rel
        assert run(client,'systemctl is-active caddy').strip()=='active'
        assert run(client,'systemctl is-enabled caddy').strip()=='enabled'
        assert run(client,'systemctl is-enabled apt-daily-upgrade.timer').strip()=='enabled'
        ssh=run(client,"sudo -n /usr/sbin/sshd -T | grep -E '^(passwordauthentication|permitrootlogin) '")
        assert 'passwordauthentication no' in ssh and 'permitrootlogin no' in ssh
        firewall=run(client,'sudo -n ufw status')
        assert 'Status: active' in firewall and all(port+'/tcp' in firewall for port in ('22','80','443'))
        assert '8081' not in firewall,'Staging port is public'
        free=int(run(client,"df --output=avail / | tail -n 1").strip())
        assert free>1024*1024,'Less than 1 GiB disk free'
        reboot=run(client,'test ! -e /var/run/reboot-required && printf no || printf yes').strip()
        domain=manifest['domain']
        context=ssl.create_default_context()
        with socket.create_connection((domain,443),timeout=20) as sock:
            with context.wrap_socket(sock,server_hostname=domain) as secured:
                cert=secured.getpeercert()
        days=int((ssl.cert_time_to_seconds(cert['notAfter'])-time.time())/86400)
        assert days>=14,'TLS certificate is near expiry'
        print(json.dumps({'result':'PASS','revision':remote,'files_verified':len(manifest['files']),
              'caddy':'active/enabled','ssh':'keys only; root login disabled','firewall':'22/80/443 only; staging private',
              'automatic_security_updates':'enabled','disk_free_KiB':free,'TLS_days_remaining':days,
              'reboot_required':reboot},indent=2))
    finally:
        sftp.close();client.close()


if __name__=='__main__':main()

"""Only public embed identifiers belong in Git; approvals stay local."""

import json
import re


def service_config(repo, preview=False):
    values = json.loads((repo / 'services.public.json').read_text(encoding='utf-8'))
    ga4 = values.get('ga4_id', '')
    jivo = values.get('jivo_widget_id', '')
    tawk_property = values.get('tawk_property_id', '')
    tawk_widget = values.get('tawk_widget_id', '')
    if bool(tawk_property) != bool(tawk_widget):
        raise SystemExit('Tawk requires both public embed identifiers')
    if tawk_property and not re.fullmatch(r'[a-f0-9]{24}', tawk_property):
        raise SystemExit('Invalid public Tawk property ID')
    if tawk_widget and not re.fullmatch(r'[a-z0-9]{8,30}', tawk_widget):
        raise SystemExit('Invalid public Tawk widget ID')
    if ga4 and not re.fullmatch(r'G-[A-Z0-9]{6,20}', ga4):
        raise SystemExit('Invalid public GA4 measurement ID')
    if jivo and not re.fullmatch(r'[A-Za-z0-9]{5,40}', jivo):
        raise SystemExit('Invalid public Jivo widget ID')
    approval_file = repo / 'service_approval.json'
    approvals = json.loads(approval_file.read_text(encoding='utf-8')) if approval_file.is_file() else {}
    if not preview:
        if ga4 and approvals.get('ga4_terms_accepted') is not True:
            raise SystemExit('GA4 requires owner acceptance of service/data processing terms')
        if jivo and approvals.get('jivo_dpa_confirmed') is not True:
            raise SystemExit('Jivo requires the confirmed data processing agreement')
        if tawk_property and approvals.get('tawk_terms_accepted') is not True:
            raise SystemExit('Tawk requires owner acceptance of service/data processing terms')
        if tawk_property and approvals.get('tawk_install_approved') is not True:
            raise SystemExit('Tawk requires owner approval to install')
    return {'ga4Id': ga4, 'jivoId': jivo,
            'jivoApproved': approvals.get('jivo_dpa_confirmed') is True,
            'tawkProperty': tawk_property, 'tawkWidget': tawk_widget,
            'tawkApproved': approvals.get('tawk_terms_accepted') is True and approvals.get('tawk_install_approved') is True,
            'networkEnabled': not preview, 'consentVersion': '2026-10-05-v1'}


def embed_service_config(soup, config):
    for old in soup.select('#site-service-config'):
        old.decompose()
    node = soup.new_tag('script', type='application/json', id='site-service-config')
    node.string = json.dumps(config, ensure_ascii=False)
    soup.head.append(node)

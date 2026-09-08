"""Inspect or reset an expired Ignition 8.3 trial. Python 3.9+, no dependencies."""
import argparse
import json
import os
import ssl
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler, HTTPSHandler


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Gateway:
    def __init__(self, url, token, ca_file=None):
        parts = urlsplit(url)
        if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment:
            raise ValueError('Use a Gateway HTTP(S) URL without credentials, query, or fragment.')
        if parts.scheme == 'http' and parts.hostname not in ('localhost', '127.0.0.1', '::1'):
            raise ValueError('Use HTTPS for a remote Gateway.')
        self.url = url.rstrip('/')
        self.token = token
        self.opener = build_opener(NoRedirect(), HTTPSHandler(context=ssl.create_default_context(cafile=ca_file)))

    def request(self, method, path, body=None):
        headers = {'X-Ignition-API-Token': self.token, 'Accept': 'application/json'}
        data = None
        if body is not None:
            headers['Content-Type'] = 'application/json'
            data = json.dumps(body).encode('utf-8')
        req = Request(self.url + path, data=data, headers=headers, method=method)
        try:
            with self.opener.open(req, timeout=20) as response:
                raw = response.read()
                return json.loads(raw) if raw.strip() else None
        except HTTPError as exc:
            raise RuntimeError(f'{method} {path}: HTTP {exc.code}. Check API key permissions, HTTPS requirements, and current trial status. No automatic POST retry.') from None
        except (URLError, TimeoutError, OSError):
            raise RuntimeError(f'{method} {path}: connection or TLS failure. Read trial status before retrying a reset.') from None


def validate_status(status):
    if not isinstance(status, dict) or type(status.get('expired')) is not bool or type(status.get('trialSecondsLeft')) not in (int, float) or status['trialSecondsLeft'] < 0:
        raise ValueError('Unexpected trial response. Inspect this Gateway\'s API documentation before proceeding.')
    return status


def run(gateway, reset=False):
    path = '/data/api/v1/trial'
    status = validate_status(gateway.request('GET', path))
    if not reset:
        return {'action': 'status', 'trial': status}
    if status.get('trialState') == 'NoneInDemo':
        return {'action': 'skipped_no_trial_modules', 'trial': status}
    if status['expired'] is not True or status['trialSecondsLeft'] != 0:
        return {'action': 'skipped_not_expired', 'trial': status}
    gateway.request('POST', path, status)
    after = validate_status(gateway.request('GET', path))
    if after['expired'] or after['trialSecondsLeft'] <= 0:
        raise RuntimeError('POST completed but renewed trial was not verified. Inspect Gateway status; do not retry blindly.')
    return {'action': 'reset_verified', 'trial': after}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gateway', default='http://localhost:8088')
    parser.add_argument('--ca-file', help='Trusted CA PEM file for HTTPS')
    parser.add_argument('--reset-if-expired', action='store_true')
    args = parser.parse_args()
    try:
        token = os.environ.get('IGNITION_API_TOKEN', '').strip()
        if not token:
            raise ValueError('Set IGNITION_API_TOKEN to the complete API token, including its name prefix.')
        result = run(Gateway(args.gateway, token, args.ca_file), args.reset_if_expired)
        print(json.dumps(result))
        return 0
    except (ValueError, RuntimeError):
        # Only controlled messages are exposed; server bodies and tokens are never logged.
        exc = sys.exc_info()[1]
        message = str(exc) if not isinstance(exc, json.JSONDecodeError) else 'Gateway returned invalid JSON.'
        print(json.dumps({'action': 'error', 'message': message}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())

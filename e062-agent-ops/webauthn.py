#!/usr/bin/env python3
"""WebAuthn (passkeys) for the fleet board — stdlib + `cryptography` only.

No passwords to remember: register once per device (biometric/PIN), then
"name + touch" logs in. Passwords stay as fallback/recovery.

Threat model: tailnet-reachable board; phishing resistance via origin-bound
challenges; attestation accepted as 'none' or packed-self (we verify the
self signature, we do not chain to vendor roots).
"""
import base64
import hashlib
import json
import os
import sqlite3
import time

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes

CHAL_TTL = 300


def _b64u_decode(s):
    s = str(s or '')
    return base64.urlsafe_b64decode(s + '=' * (-len(s) % 4))


def _b64u_encode(b):
    return base64.urlsafe_b64encode(bytes(b)).decode().rstrip('=')


# ---------- minimal CBOR decoder (definite lengths; maps/arrays/str/int/bool) -
class _Cbor:
    def __init__(self, buf):
        self.b = bytes(buf)
        self.o = 0

    def _head(self):
        v = self.b[self.o]
        self.o += 1
        return v >> 5, v & 31

    def _uint(self, ai):
        if ai < 24:
            return ai
        n = {24: 1, 25: 2, 26: 4, 27: 8}[ai]
        v = int.from_bytes(self.b[self.o:self.o + n], 'big')
        self.o += n
        return v

    def val(self):
        mt, ai = self._head()
        if mt == 0:
            return self._uint(ai)
        if mt == 1:
            return -1 - self._uint(ai)
        if mt in (2, 3):
            n = self._uint(ai)
            v = self.b[self.o:self.o + n]
            self.o += n
            return v if mt == 2 else v.decode('utf-8', 'replace')
        if mt == 4:
            return [self.val() for _ in range(self._uint(ai))]
        if mt == 5:
            return {self.val(): self.val() for _ in range(self._uint(ai))}
        # mt 6: tag (skip), mt 7: simple
        if mt == 6:
            self._uint(ai)
            return self.val()
        v = self._uint(ai) if ai >= 24 else ai
        return {20: False, 21: True, 22: None}.get(v, v)


def cbor_loads(buf):
    return _Cbor(buf).val()


# ---------- storage ----------------------------------------------------------
def init_db(db):
    c = sqlite3.connect(db)
    c.execute('CREATE TABLE IF NOT EXISTS webauthn_cred(id BLOB PRIMARY KEY, uid INTEGER, name TEXT, pub_x BLOB, pub_y BLOB, sign_count INTEGER DEFAULT 0, created INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS webauthn_chal(uid INTEGER, purpose TEXT, challenge BLOB, rp_id TEXT, origin TEXT, expires INTEGER, PRIMARY KEY (uid, purpose))')
    c.commit()
    c.close()


def _db(db):
    c = sqlite3.connect(db)
    init_db(db)
    return sqlite3.connect(db)


def _chal_new(db, uid, purpose, rp_id, origin):
    import secrets as _s
    ch = _s.token_bytes(32)
    now = int(time.time())
    c = sqlite3.connect(db)
    c.execute('INSERT OR REPLACE INTO webauthn_chal VALUES (?,?,?,?,?,?)',
              (uid, purpose, ch, rp_id, origin, now + CHAL_TTL))
    c.commit()
    c.close()
    return ch


def _chal_take(db, uid, purpose):
    c = sqlite3.connect(db)
    r = c.execute('SELECT challenge, rp_id, origin, expires FROM webauthn_chal WHERE uid=? AND purpose=?',
                  (uid, purpose)).fetchone()
    if r:
        c.execute('DELETE FROM webauthn_chal WHERE uid=? AND purpose=?', (uid, purpose))
        c.commit()
    c.close()
    if not r or r[3] < int(time.time()):
        return None
    return {'challenge': r[0], 'rp_id': r[1], 'origin': r[2]}


def _origin_ok(expected_origin, rp_id, client_origin):
    if client_origin == expected_origin:
        return True
    # local dev over plain http loopback stays usable (still a Secure Context)
    if client_origin in ('http://localhost:8322', 'http://127.0.0.1:8322',
                         'https://localhost:8322', 'https://127.0.0.1:8322'):
        return True
    return False


def _check_client_data(raw, want_type, challenge, rp_id, origin):
    try:
        cd = json.loads(bytes(raw).decode('utf-8'))
    except Exception:
        return 'bad clientData'
    if cd.get('type') != want_type:
        return 'wrong ceremony'
    try:
        got = _b64u_decode(cd.get('challenge'))
    except Exception:
        return 'bad challenge encoding'
    if got != bytes(challenge):
        return 'stale challenge — retry'
    if not _origin_ok(origin, rp_id, str(cd.get('origin') or '')):
        return 'origin mismatch'
    return None


def _verify_es256(pub_x, pub_y, sig, data):
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature, encode_dss_signature
    pub = ec.EllipticCurvePublicNumbers(
        int.from_bytes(bytes(pub_x), 'big'), int.from_bytes(bytes(pub_y), 'big'),
        ec.SECP256R1()).public_key()
    # authenticators emit raw R||S; cryptography wants DER
    raw = bytes(sig)
    if len(raw) == 64:
        r, s = int.from_bytes(raw[:32], 'big'), int.from_bytes(raw[32:], 'big')
        der = encode_dss_signature(r, s)
    else:
        try:
            decode_dss_signature(raw)
            der = raw
        except Exception:
            return False
    try:
        pub.verify(der, bytes(data), ec.ECDSA(hashes.SHA256()))
        return True
    except InvalidSignature:
        return False


def _parse_auth_data(auth):
    auth = bytes(auth)
    if len(auth) < 37:
        return None
    rp_hash, flags = auth[:32], auth[32]
    sign_count = int.from_bytes(auth[33:37], 'big')
    out = {'rp_hash': rp_hash, 'flags': flags, 'sign_count': sign_count,
           'cred_id': None, 'pub_x': None, 'pub_y': None}
    if flags & 0x40:
        if len(auth) < 55:
            return None
        ln = int.from_bytes(auth[53:55], 'big')
        out['cred_id'] = auth[55:55 + ln]
        cose = cbor_loads(auth[55 + ln:])
        try:
            if cose.get(1) != 2 or cose.get(3) != -7 or cose.get(-1) != 1:
                return None
            out['pub_x'], out['pub_y'] = bytes(cose[-2]), bytes(cose[-3])
        except Exception:
            return None
    return out


# ---------- ceremonies -------------------------------------------------------
def register_options(db, uid, name, rp_id, origin):
    init_db(db)
    ch = _chal_new(db, uid, 'reg', rp_id, origin)
    c = sqlite3.connect(db)
    excl = [{'type': 'public-key', 'id': _b64u_encode(r[0])}
            for r in c.execute('SELECT id FROM webauthn_cred WHERE uid=?', (uid,))]
    c.close()
    return {'rp': {'name': 'fleet board', 'id': rp_id},
            'user': {'id': _b64u_encode(str(uid).encode()), 'name': name,
                     'displayName': name},
            'challenge': _b64u_encode(ch),
            'pubKeyCredParams': [{'type': 'public-key', 'alg': -7}],
            'timeout': 60000,
            'attestation': 'none',
            'authenticatorSelection': {'userVerification': 'preferred'},
            'excludeCredentials': excl}


def register_verify(db, uid, data):
    st = _chal_take(db, uid, 'reg')
    if not st:
        return None, 'stale challenge — retry'
    try:
        cred_id = _b64u_decode(data.get('id') or data.get('rawId'))
        resp = data.get('response') or {}
        cdata = _b64u_decode(resp.get('clientDataJSON'))
        att = cbor_loads(_b64u_decode(resp.get('attestationObject')))
    except Exception:
        return None, 'bad encoding'
    err = _check_client_data(cdata, 'webauthn.create', st['challenge'],
                             st['rp_id'], st['origin'])
    if err:
        return None, err
    if not isinstance(att, dict) or 'authData' not in att:
        return None, 'bad attestation'
    ad = _parse_auth_data(att['authData'])
    if not ad or not ad['cred_id'] or not ad['pub_x']:
        return None, 'bad authData'
    if hashlib.sha256(st['rp_id'].encode()).digest() != ad['rp_hash']:
        return None, 'rp mismatch'
    if not (ad['flags'] & 0x01):
        return None, 'no user presence'
    if (att.get('fmt') not in ('none', 'packed', None)
            and att.get('fmt') != 'packed'):
        return None, 'attestation format?'
    if att.get('fmt') == 'packed':
        stmt = att.get('attStmt') or {}
        if not stmt.get('x5c'):  # self attestation: verify with the new key
            cdh = hashlib.sha256(cdata).digest()
            if not _verify_es256(ad['pub_x'], ad['pub_y'], stmt.get('sig'),
                                 bytes(att['authData']) + cdh):
                return None, 'self-attestation invalid'
    c = sqlite3.connect(db)
    try:
        c.execute('INSERT INTO webauthn_cred VALUES (?,?,?,?,?,?,?)',
                  (bytes(cred_id), uid, str((data.get('transports') or ['internal'])[0]),
                   bytes(ad['pub_x']), bytes(ad['pub_y']), ad['sign_count'],
                   int(time.time())))
        c.commit()
    except sqlite3.IntegrityError:
        c.close()
        return None, 'this passkey is already registered'
    c.close()
    return {'cred_id': _b64u_encode(cred_id)}, None


def login_options(db, uid, rp_id, origin):
    init_db(db)
    ch = _chal_new(db, uid, 'login', rp_id, origin)
    c = sqlite3.connect(db)
    allow = [{'type': 'public-key', 'id': _b64u_encode(r[0])}
             for r in c.execute('SELECT id FROM webauthn_cred WHERE uid=?', (uid,))]
    c.close()
    if not allow:
        return None, 'no passkey on this account — use password or add one while logged in'
    return {'challenge': _b64u_encode(ch), 'rpId': rp_id,
            'allowCredentials': allow, 'userVerification': 'preferred',
            'timeout': 60000}, None


def login_verify(db, data):
    try:
        cred_id = _b64u_decode(data.get('id') or data.get('rawId'))
        resp = data.get('response') or {}
        cdata = _b64u_decode(resp.get('clientDataJSON'))
        auth = _b64u_decode(resp.get('authenticatorData'))
        sig = _b64u_decode(resp.get('signature'))
    except Exception:
        return None, 'bad encoding'
    c = sqlite3.connect(db)
    r = c.execute('SELECT uid, pub_x, pub_y, sign_count FROM webauthn_cred WHERE id=?',
                  (bytes(cred_id),)).fetchone()
    c.close()
    if not r:
        return None, 'unknown passkey'
    uid = r[0]
    st = _chal_take(db, uid, 'login')
    if not st:
        return None, 'stale challenge — retry'
    err = _check_client_data(cdata, 'webauthn.get', st['challenge'],
                             st['rp_id'], st['origin'])
    if err:
        return None, err
    ad = _parse_auth_data(auth)
    if not ad or hashlib.sha256(st['rp_id'].encode()).digest() != ad['rp_hash']:
        return None, 'rp mismatch'
    if not (ad['flags'] & 0x01):
        return None, 'no user presence'
    if not _verify_es256(r[1], r[2], sig, bytes(auth) + hashlib.sha256(cdata).digest()):
        return None, 'bad signature'
    if (ad['sign_count'] or 0) > 0 or (r[3] or 0) > 0:
        if ad['sign_count'] <= (r[3] or 0):
            return None, 'cloned passkey suspected'
    c = sqlite3.connect(db)
    c.execute('UPDATE webauthn_cred SET sign_count=? WHERE id=?',
              (ad['sign_count'], bytes(cred_id)))
    c.commit()
    c.close()
    u = sqlite3.connect(db)
    urow = u.execute('SELECT id, name, role FROM users WHERE id=?', (uid,)).fetchone()
    u.close()
    if not urow:
        return None, 'account gone'
    return {'uid': urow[0], 'name': urow[1], 'role': urow[2]}, None

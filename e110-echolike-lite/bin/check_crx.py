#!/usr/bin/env python3
"""Verify a CRX3 file the way Chrome does, without Chrome.

The update button only works if the served .crx is a valid CRX3 whose
signature matches its payload and whose crx_id matches the appid advertised
in extension_update*.json. This script checks exactly that, so a broken
release fails here instead of silently doing nothing on someone's phone.

usage: check_crx.py FILE.crx [--appid IDadg...] [--version 1.2.3]
"""
import argparse
import hashlib
import io
import json
import struct
import sys
import zipfile

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

MAGIC = b"Cr24"


def varint(buf, i):
    n = shift = 0
    while True:
        b = buf[i]
        i += 1
        n |= (b & 0x7F) << shift
        if not b & 0x80:
            return n, i
        shift += 7


def fields(buf):
    i, out = 0, []
    while i < len(buf):
        key, i = varint(buf, i)
        num, wire = key >> 3, key & 7
        if wire == 2:
            ln, i = varint(buf, i)
            out.append((num, buf[i:i + ln]))
            i += ln
        elif wire == 0:
            val, i = varint(buf, i)
            out.append((num, val))
        else:
            raise ValueError("wire type %d not handled" % wire)
    return out


def appid_from_der(der):
    return "".join(chr(97 + (b >> 4)) + chr(97 + (b & 15)) for b in hashlib.sha256(der).digest()[:16])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--appid")
    ap.add_argument("--version")
    a = ap.parse_args()

    raw = open(a.file, "rb").read()
    fail = lambda m: (print("FAIL " + m), sys.exit(1))[0]
    if raw[:4] != MAGIC:
        fail("not a crx (magic %r)" % raw[:4])
    version = struct.unpack("<I", raw[4:8])[0]
    if version != 3:
        fail("crx version %d, Chrome needs 3" % version)
    hlen = struct.unpack("<I", raw[8:12])[0]
    header, payload = raw[12:12 + hlen], raw[12 + hlen:]
    if not payload.startswith(b"PK\x03\x04"):
        fail("payload is not a zip")

    # AsymmetricKeyProof: field 1 = public_key (DER SubjectPublicKeyInfo), field 2 = signature
    proofs = []
    for num, val in fields(header):
        if num != 2:
            continue
        pk = sig = None
        for fnum, fval in fields(val):
            if fnum == 1:
                pk = fval
            elif fnum == 2:
                sig = fval
        if pk and sig:
            proofs.append((pk, sig))
    if not proofs:
        fail("no sha256_with_rsa proof in header")

    # Signed data = context + u32le(len(SignedData)) + SignedData + payload.
    # SignedData is the header's field 10000 sub-message (crx_id lives there), not the whole header.
    shd = None
    for num, val in fields(header):
        if num == 10000:
            shd = val
    if shd is None:
        fail("header has no signed_header_data (field 10000)")
    signed = b"CRX3 SignedData\x00" + struct.pack("<I", len(shd)) + shd + payload
    ok = False
    for pk, sig in proofs:
        try:
            key = serialization.load_der_public_key(pk)
            key.verify(sig, signed, padding.PKCS1v15(), hashes.SHA256())
            ok = True
        except Exception:
            continue
    if not ok:
        fail("signature does not match payload")
    pk = proofs[0][0]
    appid = appid_from_der(pk)

    # crx_id sits in the signed header data (field 10000 -> field 1)
    crx_id = None
    for fnum, fval in fields(shd):
        if fnum == 1:
            crx_id = fval
    if crx_id is not None:
        # appid (a..p letters) -> the 16 raw bytes Chrome compares against
        raw_id = bytes(((ord(appid[i]) - 97) << 4) | (ord(appid[i + 1]) - 97) for i in range(0, 32, 2))
        if crx_id != raw_id:
            fail("crx_id %s != appid %s" % (crx_id.hex(), appid))

    z = zipfile.ZipFile(io.BytesIO(payload))
    if "manifest.json" not in z.namelist():
        fail("payload has no manifest.json")
    man = json.loads(z.read("manifest.json"))
    print("ok   crx3, %d bytes, %d files" % (len(raw), len(z.namelist())))
    print("ok   signature valid")
    print("ok   appid %s" % appid)
    print("     manifest version %s, update_url %s" % (man.get("version"), man.get("update_url")))
    if a.version and man.get("version") != a.version:
        fail("manifest version %r != expected %r" % (man.get("version"), a.version))
    if a.appid and appid != a.appid:
        fail("appid %r != expected %r" % (appid, a.appid))
    print("     ALL CHECKS PASSED")


if __name__ == "__main__":
    main()

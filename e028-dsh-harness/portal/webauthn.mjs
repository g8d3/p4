// Minimal WebAuthn (passkey) relying party — dependency-free, Node stdlib only.
// Scope: attestation "none" (what iCloud Keychain / Google Password Manager
// send by default), EC P-256 (ES256) + RSA (RS256) credentials.
// Trust model is TOFU on a private tailnet: no attestation-chain validation.
// Signature + rpId + origin + counter checks are fully enforced.
import { createHash, createPublicKey, verify } from "node:crypto";

export const b64urlToBuf = (s) =>
  Buffer.from(s.replace(/-/g, "+").replace(/_/g, "/"), "base64");
export const bufToB64url = (b) => Buffer.from(b).toString("base64url");
export const sha256 = (b) => createHash("sha256").update(b).digest();

// --- minimal CBOR decoder (uint/negint/bytes/text/array/map only) ---
export function cborDecode(buf, off = 0) {
  const first = buf[off];
  const major = first >> 5;
  let val = first & 31;
  let pos = off + 1;
  const readArg = () => {
    if (val < 24) return val;
    if (val === 24) { pos += 1; return buf[pos - 1]; }
    if (val === 25) { const v = buf.readUInt16BE(pos); pos += 2; return v; }
    if (val === 26) { const v = buf.readUInt32BE(pos); pos += 4; return v; }
    throw new Error("cbor: oversized arg");
  };
  if (major === 0) return [readArg(), pos];
  if (major === 1) return [-1 - readArg(), pos];
  if (major === 2 || major === 3) {
    const len = readArg();
    const end = pos + len;
    const v = buf.subarray(pos, end);
    pos = end;
    return [major === 2 ? v : v.toString("utf8"), pos];
  }
  if (major === 4 || major === 5) {
    const len = readArg();
    if (major === 4) {
      const arr = [];
      for (let i = 0; i < len; i++) { const [v, p] = cborDecode(buf, pos); arr.push(v); pos = p; }
      return [arr, pos];
    }
    const map = new Map();
    for (let i = 0; i < len; i++) {
      const [k, p1] = cborDecode(buf, pos);
      const [v, p2] = cborDecode(buf, p1);
      map.set(k, v); pos = p2;
    }
    return [map, pos];
  }
  throw new Error("cbor: unsupported major " + major);
}

export function parseAuthData(buf) {
  if (buf.length < 37) throw new Error("authData too short");
  const rpIdHash = buf.subarray(0, 32);
  const flags = buf[32];
  const signCount = buf.readUInt32BE(33);
  const out = {
    rpIdHash,
    up: !!(flags & 0x01),
    uv: !!(flags & 0x04),
    at: !!(flags & 0x40),
    signCount,
    credId: null,
    coseKey: null,
    rest: 37,
  };
  if (out.at) {
    // layout: rpIdHash(32) flags(1) counter(4) aaguid(16) credIdLen(2) credId coseKey
    if (buf.length < 55) throw new Error("authData too short for attested data");
    const credIdLen = buf.readUInt16BE(53);
    out.credId = buf.subarray(55, 55 + credIdLen);
    const [key, end] = cborDecode(buf, 55 + credIdLen);
    if (!(key instanceof Map)) throw new Error("cose key not a map");
    out.coseKey = key;
    out.rest = end;
  }
  return out;
}

// COSE -> JWK (EC2 P-256 / ES256 = alg -7; RSA / RS256 = alg -257)
export function coseToJwk(cose) {
  const kty = cose.get(1);
  const alg = cose.get(3);
  if (kty === 2 && (alg === -7 || alg === undefined)) {
    if (cose.get(-1) !== 1) throw new Error("only P-256 supported");
    const x = cose.get(-2), y = cose.get(-3);
    if (!Buffer.isBuffer(x) || !Buffer.isBuffer(y)) throw new Error("bad EC coords");
    return { kty: "EC", crv: "P-256", x: bufToB64url(x), y: bufToB64url(y) };
  }
  if (kty === 3 && (alg === -257 || alg === undefined)) {
    const n = cose.get(-1), e = cose.get(-2);
    if (!Buffer.isBuffer(n) || !Buffer.isBuffer(e)) throw new Error("bad RSA params");
    return { kty: "RSA", n: bufToB64url(n), e: bufToB64url(e) };
  }
  throw new Error(`unsupported credential key (kty=${kty} alg=${alg})`);
}

// --- registration (attestation "none" only) ---
export function verifyRegistration(attestationB64, expectedRpId) {
  const [top] = cborDecode(b64urlToBuf(attestationB64));
  const obj = top instanceof Map ? top : new Map(Object.entries(top));
  const fmt = obj.get("fmt");
  if (fmt !== "none") throw new Error(`attestation "${fmt}" not accepted (use a passkey with attestation none)`);
  const authData = parseAuthData(Buffer.from(obj.get("authData")));
  if (!authData.up) throw new Error("user not present");
  if (!authData.at || !authData.credId || !authData.coseKey) throw new Error("no attested key");
  if (!authData.rpIdHash.equals(sha256(Buffer.from(expectedRpId)))) throw new Error("rpId mismatch");
  return {
    credId: bufToB64url(authData.credId),
    jwk: coseToJwk(authData.coseKey),
    signCount: authData.signCount,
  };
}

// --- authentication ---
export function verifyAssertion(input, expected) {
  // input: {credentialId, authenticatorData, clientDataJSON, signature}
  // expected: {rpId, origin, challengeB64, jwk, storedCounter}
  const authData = Buffer.from(b64urlToBuf(input.authenticatorData));
  const clientData = JSON.parse(Buffer.from(b64urlToBuf(input.clientDataJSON)).toString("utf8"));
  if (clientData.type !== "webauthn.get") throw new Error("bad ceremony type");
  if (clientData.origin !== expected.origin) throw new Error("origin mismatch");
  const chalOk = Buffer.from(b64urlToBuf(clientData.challenge)).equals(Buffer.from(b64urlToBuf(expected.challengeB64)));
  if (!chalOk) throw new Error("challenge mismatch");
  const parsed = parseAuthData(authData);
  if (!parsed.up) throw new Error("user not present");
  if (!parsed.rpIdHash.equals(sha256(Buffer.from(expected.rpId)))) throw new Error("rpId mismatch");
  const key = createPublicKey({ key: expected.jwk, format: "jwk" });
  const data = Buffer.concat([authData, sha256(Buffer.from(b64urlToBuf(input.clientDataJSON)))]);
  const alg = expected.jwk.kty === "RSA" ? "RSA-SHA256" : "sha256";
  if (!verify(alg, data, key, Buffer.from(b64urlToBuf(input.signature)))) throw new Error("bad signature");
  const sc = parsed.signCount, prev = expected.storedCounter ?? 0;
  if (sc !== 0 && prev !== 0 && sc <= prev) throw new Error("counter did not advance (possible clone)");
  return parsed.signCount;
}

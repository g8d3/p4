"""Extension id of the unpacked folder: manifest 'key' wins, else the path hash."""
import base64
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXT = str(ROOT / "extension")


def id_from_der(der):
    return "".join(chr(97 + (b >> 4)) + chr(97 + (b & 15)) for b in hashlib.sha256(der).digest()[:16])


def extension_id():
    man = json.loads(pathlib.Path(EXT, "manifest.json").read_text())
    if man.get("key"):
        return id_from_der(base64.b64decode(man["key"]))
    return id_from_der(EXT.encode())

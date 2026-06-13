"""Decrypt wires from test-fernet-cmds-export.ts (VibranceFlow-mobile/.test-wires.txt)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOBILE_ROOT = ROOT.parent / "VibranceFlow-mobile"

from core.remote.crypto import decrypt_json, generate_key

key = sys.argv[1] if len(sys.argv) > 1 else None
key_path = MOBILE_ROOT / ".test-key.txt"
wires_path = MOBILE_ROOT / ".test-wires.txt"

if not key:
    key = generate_key()
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_text(key, encoding="utf-8")
    print("generated key", key)

if not wires_path.is_file():
    print(
        f"Missing {wires_path}\n"
        "Run from VibranceFlow-mobile: npx tsx scripts/test-fernet-cmds-export.ts",
        file=sys.stderr,
    )
    raise SystemExit(1)

wires = wires_path.read_text(encoding="utf-8").strip().splitlines()
names = ["ping", "get_state", "set_observer", "set_sliders"]
for name, wire in zip(names, wires):
    try:
        plain = decrypt_json(key, wire)
        print(name, "OK", plain[:60])
    except ValueError as e:
        print(name, "FAIL", e)

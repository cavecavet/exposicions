#!/usr/bin/env python3
"""
Publica les dades de cards.json al full de càlcul de Google Sheets
mitjançant el Google Apps Script existent.

Ús:
  python3 scripts/push_cards.py
"""

import json
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
REPO_DIR = SCRIPT_DIR.parent
CARDS_JSON = REPO_DIR / "cards.json"

APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyTTFLIvIsA1SrEw5oppigpz-LYKiYAJFzsiqtXe_UWthwAoudTroPzCIUZbTOdCjIjaw/exec"


def main():
    with open(CARDS_JSON, encoding="utf-8") as f:
        cards = json.load(f)

    payload = json.dumps({"cards": cards}).encode("utf-8")
    req = urllib.request.Request(
        APPS_SCRIPT_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    print(f"Enviant {len(cards)} fitxes a Google Sheets...")
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    if result.get("status") == "success":
        print(f"Full actualitzat amb {result['count']} fitxes.")
    else:
        raise RuntimeError(f"Error de l'script: {result.get('message', 'desconegut')}")


if __name__ == "__main__":
    main()

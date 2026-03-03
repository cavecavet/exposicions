#!/usr/bin/env python3
"""
Genera codis QR per a totes les fitxes de cards.json que no en tinguin.

Ús:
  python3 scripts/generate_qrs.py           # Només les que falten
  python3 scripts/generate_qrs.py --all     # Regenera totes

Els QRs es guarden a images/qrs/<cardId>.png
"""

import argparse
import json
from pathlib import Path

import qrcode

SCRIPT_DIR = Path(__file__).parent
REPO_DIR = SCRIPT_DIR.parent
CARDS_JSON = REPO_DIR / "cards.json"
QRS_DIR = REPO_DIR / "images" / "qrs"
BASE_URL = "https://cavecavet.github.io/exposicions/#/fitxa/"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="Regenera tots els QRs")
    args = parser.parse_args()

    QRS_DIR.mkdir(parents=True, exist_ok=True)

    with open(CARDS_JSON, encoding="utf-8") as f:
        cards = json.load(f)

    existing = {p.stem for p in QRS_DIR.glob("*.png")}
    generated = []

    for card in cards:
        card_id = card["cardId"]
        if not args.all and card_id in existing:
            continue
        url = BASE_URL + card_id
        img = qrcode.make(url)
        img.save(QRS_DIR / f"{card_id}.png")
        generated.append(card_id)

    if generated:
        print(f"Generats {len(generated)} QRs: {generated}")
    else:
        print("Tots els QRs ja existeixen. Usa --all per regenerar-los.")


if __name__ == "__main__":
    main()

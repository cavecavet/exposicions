#!/usr/bin/env python3
"""
Actualitza cards.json amb les dades de la fulla Cards de Google Sheets.

Ús:
  python3 update_cards.py
"""

import json
import os
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CARDS_JSON = os.path.join(SCRIPT_DIR, "cards.json")

APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyge7qifH1P3rka7vwgNf5Q96gRQRS92vbvlBUJkscnBkto1_zAcNp4GaufGrfy4OGaSg/exec"

FIELDS = ["cardId", "photoId", "commonName", "scientificName", "comment", "fotoAuthor", "cardAuthor"]


def fetch_cards():
    url = f"{APPS_SCRIPT_URL}?action=getCards"
    print(f"Descarregant dades de Google Sheets...")
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())

    if data.get("status") != "success":
        raise RuntimeError(f"Error de l'API: {data.get('message', 'desconegut')}")

    return data["cards"]


def main():
    cards = fetch_cards()

    # Conservar només els camps necessaris
    cleaned = []
    for card in cards:
        cleaned.append({field: card.get(field, "") for field in FIELDS})

    # Ordenar per cardId
    cleaned.sort(key=lambda c: c["cardId"])

    with open(CARDS_JSON, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, indent=2, ensure_ascii=False)

    print(f"Actualitzat {CARDS_JSON} amb {len(cleaned)} fitxes.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Publica les dades de cards.json al full de càlcul de Google Sheets.

Prerequisits:
  1. Activa Google Sheets API a https://console.cloud.google.com/
  2. Crea un compte de servei i descarrega les credencials JSON
  3. Guarda el fitxer de credencials com a scripts/credentials.json
  4. Comparteix el full de càlcul amb l'email del compte de servei (editor)
  5. pip3 install gspread

Ús:
  python3 scripts/push_cards.py

El full de càlcul s'identifica per SPREADSHEET_ID.
La pestanya s'identifica per SHEET_NAME.
"""

import json
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

SCRIPT_DIR = Path(__file__).parent
REPO_DIR = SCRIPT_DIR.parent
CARDS_JSON = REPO_DIR / "cards.json"
CREDENTIALS_FILE = SCRIPT_DIR / "credentials.json"

SPREADSHEET_ID = "1ifslcJQbd9l0b12zMkupkK5XeSJP1ZLT"
SHEET_NAME = "Cards"

FIELDS = ["cardId", "photoId", "commonName", "scientificName", "comment", "fotoAuthor", "cardAuthor"]
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def main():
    if not CREDENTIALS_FILE.exists():
        raise FileNotFoundError(
            f"No s'ha trobat {CREDENTIALS_FILE}\n"
            "Descarrega les credencials del compte de servei des de Google Cloud Console."
        )

    with open(CARDS_JSON, encoding="utf-8") as f:
        cards = json.load(f)

    creds = Credentials.from_service_account_file(str(CREDENTIALS_FILE), scopes=SCOPES)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SPREADSHEET_ID)
    ws = sh.worksheet(SHEET_NAME)

    # Capçalera + dades
    rows = [FIELDS] + [[card.get(f, "") for f in FIELDS] for card in cards]

    # Sobreescriu des de A1
    ws.clear()
    ws.update("A1", rows)

    print(f"Full '{SHEET_NAME}' actualitzat amb {len(cards)} fitxes.")


if __name__ == "__main__":
    main()

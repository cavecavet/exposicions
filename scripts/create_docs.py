#!/usr/bin/env python3
"""
Crea un Google Doc per a cada fitxa de la fulla Cards de Google Sheets.
El nom de cada document és el cardId.

Ús:
  python3.14 scripts/create_docs.py [--folder-id FOLDER_ID]

Requisits previs:
  pip install google-api-python-client google-auth google-auth-oauthlib

  Cal crear credencials OAuth2 al GCP:
    APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID
    Application type: Desktop app
    Desa el JSON com: scripts/oauth_client.json

  La primera execució obrirà el navegador per autoritzar l'accés.
  El token es guarda a scripts/token.json per a execucions posteriors.
"""

import argparse
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCRIPT_DIR = Path(__file__).parent
REPO_DIR = SCRIPT_DIR.parent
OAUTH_CLIENT_FILE = SCRIPT_DIR / "oauth_client.json"
TOKEN_FILE = SCRIPT_DIR / "token.json"
QR_DIR = REPO_DIR / "images" / "qrs"

SPREADSHEET_ID = "11RKl2Uhu4eAJlKvcAQQajR0bGeAaHMekDOw8CtU5DiI"
SHEET_NAME = "Cards"
QR_BASE_URL = "https://cavecavet.github.io/exposicions/images/qrs"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
]

# Variants de nom de columna (català / castellà / anglès)
FIELD_VARIANTS = {
    "year":       ["any", "año", "year"],
    "technique":  ["tècnica", "técnica", "technique"],
    "dimensions": ["dimensions", "dimensiones"],
    "location":   ["lloc", "lugar", "location", "localització", "localización"],
}


def get_field(card: dict, key: str) -> str:
    for variant in FIELD_VARIANTS.get(key, [key]):
        val = card.get(variant, "").strip()
        if val:
            return val
    return ""


def get_services():
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not OAUTH_CLIENT_FILE.exists():
                raise FileNotFoundError(
                    f"No s'ha trobat {OAUTH_CLIENT_FILE}\n"
                    "Crea credencials OAuth2 (Desktop app) al GCP i desa-les en aquest fitxer."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(OAUTH_CLIENT_FILE), SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    sheets = build("sheets", "v4", credentials=creds)
    docs = build("docs", "v1", credentials=creds)
    drive = build("drive", "v3", credentials=creds)
    return sheets, docs, drive


def read_cards(sheets_svc) -> list[dict]:
    result = (
        sheets_svc.spreadsheets()
        .values()
        .get(spreadsheetId=SPREADSHEET_ID, range=f"{SHEET_NAME}!A1:Z")
        .execute()
    )
    values = result.get("values", [])
    if len(values) < 2:
        return []
    headers = values[0]
    cards = []
    for row in values[1:]:
        card = {headers[i]: (row[i] if i < len(row) else "") for i in range(len(headers))}
        if card.get("cardId", "").strip():
            cards.append(card)
    return cards


def build_content(card: dict) -> list[tuple[str, str | None]]:
    """
    Retorna una llista de (text, estil) per construir el doc.
    Estils: 'title' (H1), 'italic', None (normal).
    L'últim element és sempre "\n" i serveix com a paràgraf per al QR.
    """
    artistic_name   = card.get("Nombre artístico", "").strip()
    common_name     = card.get("commonName", "").strip()
    scientific_name = card.get("scientificName", "").strip()
    foto_author     = card.get("fotoAuthor", "").strip()
    card_author     = card.get("cardAuthor", "").strip()
    comment         = card.get("comment", "").strip()
    year            = get_field(card, "year")
    technique       = get_field(card, "technique")
    dimensions      = get_field(card, "dimensions")
    location        = get_field(card, "location")

    lines: list[tuple[str, str | None]] = []

    # Títol artístic en H1
    if artistic_name:
        lines.append((artistic_name + "\n", "title"))

    # Nom comú i científic en estil normal/italic
    if common_name:
        lines.append((common_name + "\n", None))
    if scientific_name:
        lines.append((scientific_name + "\n", "italic"))

    lines.append(("\n", None))  # línia en blanc

    # Metadades
    if foto_author:
        lines.append((foto_author + "\n", None))
    if year:
        lines.append((year + "\n", None))
    if technique:
        lines.append((technique + "\n", None))
    if dimensions:
        lines.append((dimensions + "\n", None))
    if location:
        lines.append((location + "\n", None))
    if card_author:
        lines.append((card_author + "\n", None))

    lines.append(("\n", None))  # línia en blanc

    # Comentari en cursiva
    if comment:
        lines.append((comment + "\n", "italic"))

    # Paràgraf final buit: aquí s'inserirà la imatge QR
    lines.append(("\n", None))

    return lines


def create_card_doc(docs_svc, drive_svc, card: dict, folder_id: str | None) -> str:
    card_id = card.get("cardId", "desconegut").strip()
    lines = build_content(card)
    full_text = "".join(text for text, _ in lines)

    # Crear el document
    doc = docs_svc.documents().create(body={"title": card_id}).execute()
    doc_id = doc["documentId"]

    requests = []

    # Inserir tot el text d'un cop a l'índex 1
    requests.append({
        "insertText": {
            "location": {"index": 1},
            "text": full_text,
        }
    })

    # Calcular índexs i afegir peticions de format
    idx = 1
    for text, style in lines:
        length = len(text)
        end = idx + length       # índex exclusiu del final (inclou \n)
        content_end = end - 1    # exclou el \n per a estils de text

        if style == "title":
            requests.append({
                "updateParagraphStyle": {
                    "range": {"startIndex": idx, "endIndex": end},
                    "paragraphStyle": {"namedStyleType": "HEADING_1"},
                    "fields": "namedStyleType",
                }
            })
        elif style == "italic":
            requests.append({
                "updateTextStyle": {
                    "range": {"startIndex": idx, "endIndex": content_end},
                    "textStyle": {"italic": True},
                    "fields": "italic",
                }
            })

        idx = end

    # Inserir imatge QR al paràgraf final (idx - 1 = posició del \n final)
    qr_path = QR_DIR / f"{card_id}.png"
    if qr_path.exists():
        qr_url = f"{QR_BASE_URL}/{card_id}.png"
        requests.append({
            "insertInlineImage": {
                "location": {"index": idx - 1},
                "uri": qr_url,
                "objectSize": {
                    "height": {"magnitude": 150, "unit": "PT"},
                    "width":  {"magnitude": 150, "unit": "PT"},
                },
            }
        })
    else:
        print(f"(avís: no s'ha trobat QR per {card_id})", end=" ")

    # Aplicar format i imatge
    docs_svc.documents().batchUpdate(
        documentId=doc_id, body={"requests": requests}
    ).execute()

    # Moure a la carpeta si s'ha especificat
    if folder_id:
        file_meta = drive_svc.files().get(fileId=doc_id, fields="parents").execute()
        previous_parents = ",".join(file_meta.get("parents", []))
        drive_svc.files().update(
            fileId=doc_id,
            addParents=folder_id,
            removeParents=previous_parents,
            fields="id, parents",
        ).execute()

    return doc_id


def main():
    parser = argparse.ArgumentParser(
        description="Crea un Google Doc per a cada fitxa de la fulla Cards."
    )
    parser.add_argument(
        "--folder-id",
        metavar="FOLDER_ID",
        help="ID de la carpeta de Drive on desar els docs (opcional)",
    )
    args = parser.parse_args()

    print("Connectant als serveis de Google...")
    sheets_svc, docs_svc, drive_svc = get_services()

    print(f"Llegint fitxes de '{SHEET_NAME}'...")
    cards = read_cards(sheets_svc)
    print(f"Trobades {len(cards)} fitxes.")

    for card in cards:
        card_id = card.get("cardId", "desconegut").strip()
        print(f"  Creant doc '{card_id}'... ", end="", flush=True)
        try:
            doc_id = create_card_doc(docs_svc, drive_svc, card, folder_id=args.folder_id)
            print(f"OK → https://docs.google.com/document/d/{doc_id}")
        except Exception as exc:
            print(f"ERROR: {exc}")

    print("Fet!")


if __name__ == "__main__":
    main()

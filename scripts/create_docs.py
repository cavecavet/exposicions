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
import json
import mimetypes
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCRIPT_DIR = Path(__file__).parent
REPO_DIR = SCRIPT_DIR.parent
OAUTH_CLIENT_FILE = SCRIPT_DIR / "oauth_client.json"
TOKEN_FILE = SCRIPT_DIR / "token.json"
IMAGE_CACHE_FILE = SCRIPT_DIR / "image_cache.json"   # photo_id → drive url
QR_DIR = REPO_DIR / "images" / "qrs"

SPREADSHEET_ID = "11RKl2Uhu4eAJlKvcAQQajR0bGeAaHMekDOw8CtU5DiI"
SHEET_NAME = "Cards"
QR_BASE_URL = "https://cavecavet.github.io/exposicions/images/qrs"
LOGOS_BASE_URL = "https://cavecavet.github.io/exposicions/images/logos"

# Capçalera: (url, width_pt, height_pt)
HEADER_LOGO = (f"{LOGOS_BASE_URL}/Logo0.png", 19, 19)  # logo quadrat compacte
HEADER_TEXT = "Associació Cave Cavet"
HEADER_SPACE_PT = 9   # espai inicial (abans del logo)
HEADER_TEXT_PT  = 10  # text del nom
# Peu de pàgina: 2 línies (compacte)
FOOTER_LINE1 = [
    (f"{LOGOS_BASE_URL}/Logo1.png", 41, 20),   # Ajuntament de Cambrils (+10%)
    (f"{LOGOS_BASE_URL}/Logo2.png", 39, 17),   # URV (+10%)
    (f"{LOGOS_BASE_URL}/Logo3.jpg", 36, 20),   # Institut Horticultura (+10%)
    (f"{LOGOS_BASE_URL}/Logo4.png", 26, 17),   # MINKA (+10%)
]
FOOTER_LINE2 = [
    (f"{LOGOS_BASE_URL}/Logo5.png", 36, 20),   # Institut Hoteleria (+10%)
    (f"{LOGOS_BASE_URL}/Logo6.png", 36, 20),   # Símbiosy (+10%)
    (f"{LOGOS_BASE_URL}/Logo7.png", 44, 20),   # Diputació de Tarragona (+10%)
]

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
]

# Variants de nom de columna (case-insensitive)
FIELD_VARIANTS = {
    "year":       ["any", "año", "year"],
    "technique":  ["técnica", "tècnica", "technique"],
    "dimensions": ["dimensions", "dimensiones"],
    "location":   ["lloc", "lugar", "location"],
}


def get_field(card: dict, key: str) -> str:
    """Cerca el camp de forma case-insensitive."""
    lower_card = {k.lower(): v for k, v in card.items()}
    for variant in FIELD_VARIANTS.get(key, [key]):
        val = lower_card.get(variant.lower(), "").strip()
        if val:
            return val
    return ""


def load_image_cache() -> dict:
    if IMAGE_CACHE_FILE.exists():
        return json.loads(IMAGE_CACHE_FILE.read_text())
    return {}


def save_image_cache(cache: dict) -> None:
    IMAGE_CACHE_FILE.write_text(json.dumps(cache, indent=2, ensure_ascii=False))


def get_drive_image_url(drive_svc, file_id: str, cache: dict, image_id: str) -> str:
    """Puja una imatge a Drive (si no hi és al cache) i retorna una URL pública."""
    if image_id in cache:
        return cache[image_id]

    local_path = None
    for ext in ("jpg", "JPG", "jpeg", "JPEG", "png", "PNG"):
        p = REPO_DIR / "images" / f"{image_id}.{ext}"
        if p.exists():
            local_path = p
            break

    if not local_path:
        return None

    mime = mimetypes.guess_type(str(local_path))[0] or "image/jpeg"
    media = MediaFileUpload(str(local_path), mimetype=mime)
    uploaded = drive_svc.files().create(
        body={"name": local_path.name},
        media_body=media,
        fields="id",
    ).execute()
    drive_file_id = uploaded["id"]

    # Fer el fitxer públicament accessible
    drive_svc.permissions().create(
        fileId=drive_file_id,
        body={"type": "anyone", "role": "reader"},
    ).execute()

    url = f"https://drive.google.com/uc?id={drive_file_id}"
    cache[image_id] = url
    save_image_cache(cache)
    return url


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


def delete_existing_docs(drive_svc, name: str, folder_id: str | None) -> int:
    """Elimina tots els Google Docs amb el nom indicat. Retorna el nombre eliminats."""
    q = f"name = '{name}' and mimeType = 'application/vnd.google-apps.document' and trashed = false"
    if folder_id:
        q += f" and '{folder_id}' in parents"
    result = drive_svc.files().list(q=q, fields="files(id)").execute()
    deleted = 0
    for f in result.get("files", []):
        drive_svc.files().delete(fileId=f["id"]).execute()
        deleted += 1
    return deleted


def add_header_footer(docs_svc, doc_id: str) -> None:
    """Afegeix capçalera (Logo0 + Instagram) i peu de pàgina (logos col·laboradors)."""

    def _insert_line(seg_id: str, logos: list, index: int) -> None:
        """Insereix logos en ordre a partir d'index, en ordre invers per preservar l'ordre."""
        for url, w, h in reversed(logos):
            try:
                docs_svc.documents().batchUpdate(
                    documentId=doc_id,
                    body={"requests": [{
                        "insertInlineImage": {
                            "location": {"segmentId": seg_id, "index": index},
                            "uri": url,
                            "objectSize": {
                                "height": {"magnitude": h, "unit": "PT"},
                                "width":  {"magnitude": w, "unit": "PT"},
                            },
                        }
                    }]},
                ).execute()
            except Exception as e:
                print(f"(avís logo {url.split('/')[-1]}: {e})", end=" ")

    # Capçalera: logo + text
    try:
        resp = docs_svc.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": [{"createHeader": {"type": "DEFAULT"}}]},
        ).execute()
        header_id = resp["replies"][0]["createHeader"]["headerId"]
        # Estructura: [espai][logo][text]  → alineat START
        url, w, h = HEADER_LOGO
        try:
            # 1. Espai inicial (index 0)
            docs_svc.documents().batchUpdate(
                documentId=doc_id,
                body={"requests": [{"insertText": {
                    "location": {"segmentId": header_id, "index": 0},
                    "text": " ",
                }}]},
            ).execute()
            # 2. Logo (index 1, just after space)
            docs_svc.documents().batchUpdate(
                documentId=doc_id,
                body={"requests": [{
                    "insertInlineImage": {
                        "location": {"segmentId": header_id, "index": 1},
                        "uri": url,
                        "objectSize": {
                            "height": {"magnitude": h, "unit": "PT"},
                            "width":  {"magnitude": w, "unit": "PT"},
                        },
                    }
                }]},
            ).execute()
            # 3. Text nom associació (index 2, just after logo)
            docs_svc.documents().batchUpdate(
                documentId=doc_id,
                body={"requests": [{"insertText": {
                    "location": {"segmentId": header_id, "index": 2},
                    "text": HEADER_TEXT,
                }}]},
            ).execute()
            text_end = 2 + len(HEADER_TEXT)
            # Estil espai inicial: 9pt bold
            docs_svc.documents().batchUpdate(
                documentId=doc_id,
                body={"requests": [{"updateTextStyle": {
                    "range": {"segmentId": header_id, "startIndex": 0, "endIndex": 1},
                    "textStyle": {"bold": True, "fontSize": {"magnitude": HEADER_SPACE_PT, "unit": "PT"}},
                    "fields": "bold,fontSize",
                }}]},
            ).execute()
            # Estil text nom: 10pt bold
            docs_svc.documents().batchUpdate(
                documentId=doc_id,
                body={"requests": [{"updateTextStyle": {
                    "range": {"segmentId": header_id, "startIndex": 2, "endIndex": text_end},
                    "textStyle": {"bold": True, "fontSize": {"magnitude": HEADER_TEXT_PT, "unit": "PT"}},
                    "fields": "bold,fontSize",
                }}]},
            ).execute()
            # Paràgraf: START, interlineat compacte
            docs_svc.documents().batchUpdate(
                documentId=doc_id,
                body={"requests": [{"updateParagraphStyle": {
                    "range": {"segmentId": header_id, "startIndex": 0, "endIndex": text_end + 1},
                    "paragraphStyle": {
                        "lineSpacing": 100,
                        "spaceAbove": {"magnitude": 0, "unit": "PT"},
                        "spaceBelow": {"magnitude": 0, "unit": "PT"},
                    },
                    "fields": "lineSpacing,spaceAbove,spaceBelow",
                }}]},
            ).execute()
        except Exception as e:
            print(f"(avís capçalera logo/text: {e})", end=" ")
    except Exception as e:
        print(f"(avís capçalera: {e})", end=" ")

    # Peu de pàgina: dues línies
    try:
        resp = docs_svc.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": [{"createFooter": {"type": "DEFAULT"}}]},
        ).execute()
        footer_id = resp["replies"][0]["createFooter"]["footerId"]

        # Línia 1: 4 primers logos, centrats
        _insert_line(footer_id, FOOTER_LINE1, 0)
        n1 = len(FOOTER_LINE1)

        # Salt de línia entre les dues files
        try:
            docs_svc.documents().batchUpdate(
                documentId=doc_id,
                body={"requests": [{"insertText": {
                    "location": {"segmentId": footer_id, "index": n1},
                    "text": "\n",
                }}]},
            ).execute()
        except Exception as e:
            print(f"(avís salt línia footer: {e})", end=" ")

        # Línia 2: 3 últims logos, centrats, a partir de n1+1
        line2_start = n1 + 1
        _insert_line(footer_id, FOOTER_LINE2, line2_start)

        # Estil de les dues línies del peu: centrat, interlineat simple, sense espais
        compact_style = {
            "alignment": "CENTER",
            "lineSpacing": 100,
            "spaceAbove": {"magnitude": 0, "unit": "PT"},
            "spaceBelow": {"magnitude": 0, "unit": "PT"},
        }
        for (s, e) in [(0, n1 + 1), (line2_start, line2_start + 1)]:
            try:
                docs_svc.documents().batchUpdate(
                    documentId=doc_id,
                    body={"requests": [{
                        "updateParagraphStyle": {
                            "range": {"segmentId": footer_id, "startIndex": s, "endIndex": e},
                            "paragraphStyle": compact_style,
                            "fields": "alignment,lineSpacing,spaceAbove,spaceBelow",
                        }
                    }]},
                ).execute()
            except Exception as e2:
                print(f"(avís estil peu: {e2})", end=" ")
    except Exception as e:
        print(f"(avís peu: {e})", end=" ")


def create_card_doc(docs_svc, drive_svc, card: dict, folder_id: str | None, img_cache: dict, overwrite: bool = False) -> str:
    card_id         = card.get("cardId", "desconegut").strip()
    if overwrite:
        n = delete_existing_docs(drive_svc, card_id, folder_id)
        if n:
            print(f"(esborrats {n})", end=" ")
    artistic_name   = card.get("Nombre artístico", "").strip()
    common_name     = card.get("commonName", "").strip()
    scientific_name = card.get("scientificName", "").strip()
    foto_author     = card.get("fotoAuthor", "").strip()
    card_author     = card.get("cardAuthor", "").strip()
    photo_id        = (card.get("Imatge") or card.get("photoId") or "").strip()
    year            = get_field(card, "year")
    technique       = get_field(card, "technique")
    dimensions      = get_field(card, "dimensions")
    location        = get_field(card, "location")

    # ── Chunks: (text, bold, italic, heading, marker) ────────────────────
    # marker: 'images' | None
    chunks: list[tuple[str, bool, bool, bool, str | None]] = []

    def add(text, bold=False, italic=False, heading=False, marker=None):
        chunks.append((text, bold, italic, heading, marker))

    def field(label, value, italic_val=False):
        if value:
            add(label + ": ", bold=True)
            add(value + "\n", italic=italic_val)

    if artistic_name:
        add(artistic_name + "\n", heading=True)
    add("\n", marker="images")  # paràgraf buit → foto+QR costat a costat

    field("Nom comú", common_name)
    field("Nom científic", scientific_name, italic_val=True)
    field("Autor fotografia", foto_author)
    if year:       field("Any", year)
    if technique:  field("Tècnica", technique)
    if dimensions: field("Dimensions", dimensions)
    if location:   field("Lloc", location)
    field("Autor fitxa", card_author)

    # ── Compute positions ─────────────────────────────────────────────────
    full_text = "".join(c[0] for c in chunks)
    images_idx = None
    fields_start_idx = None
    pos = 1
    for text, _, _, _, marker in chunks:
        if marker == "images":
            images_idx = pos
            fields_start_idx = pos + len(text)  # camps comencen just després
        pos += len(text)

    # ── API requests ──────────────────────────────────────────────────────
    requests = []

    # Mida 15×10 cm (alt×ample) i marges reduïts per cabre en una pàgina
    requests.append({
        "updateDocumentStyle": {
            "documentStyle": {
                "pageSize": {
                    "width":  {"magnitude": 284, "unit": "PT"},  # 10 cm
                    "height": {"magnitude": 425, "unit": "PT"},  # 15 cm
                },
                "marginTop":    {"magnitude": 18, "unit": "PT"},
                "marginBottom": {"magnitude": 18, "unit": "PT"},
                "marginLeft":   {"magnitude": 18, "unit": "PT"},
                "marginRight":  {"magnitude": 18, "unit": "PT"},
            },
            "fields": "pageSize,marginTop,marginBottom,marginLeft,marginRight",
        }
    })

    # Inserir tot el text
    requests.append({
        "insertText": {"location": {"index": 1}, "text": full_text}
    })

    # Interlineat 115 per a tot el cos (heading + imatges)
    requests.append({
        "updateParagraphStyle": {
            "range": {"startIndex": 1, "endIndex": 1 + len(full_text)},
            "paragraphStyle": {
                "lineSpacing": 115,
                "spaceAbove": {"magnitude": 0, "unit": "PT"},
                "spaceBelow": {"magnitude": 0, "unit": "PT"},
            },
            "fields": "lineSpacing,spaceAbove,spaceBelow",
        }
    })
    # Interlineat 150 per als camps (a partir del primer camp)
    if fields_start_idx and fields_start_idx < 1 + len(full_text):
        requests.append({
            "updateParagraphStyle": {
                "range": {"startIndex": fields_start_idx, "endIndex": 1 + len(full_text)},
                "paragraphStyle": {"lineSpacing": 150},
                "fields": "lineSpacing",
            }
        })

    # Formatar cada chunk
    idx = 1
    for text, bold, italic, heading, _ in chunks:
        length = len(text)
        end = idx + length
        content_end = end - 1  # exclou el \n final

        if heading:
            requests.append({
                "updateParagraphStyle": {
                    "range": {"startIndex": idx, "endIndex": end},
                    "paragraphStyle": {"namedStyleType": "HEADING_1"},
                    "fields": "namedStyleType",
                }
            })

        ts = {}
        fields_list = []
        if bold:
            ts["bold"] = True
            fields_list.append("bold")
        if italic:
            ts["italic"] = True
            fields_list.append("italic")
        if ts and content_end > idx:
            requests.append({
                "updateTextStyle": {
                    "range": {"startIndex": idx, "endIndex": content_end},
                    "textStyle": ts,
                    "fields": ",".join(fields_list),
                }
            })

        idx = end

    # Títol artístic: centrat, 22pt, amb 12pt d'espai superior
    if artistic_name:
        heading_len = len(artistic_name) + 1  # +1 per al \n
        requests.append({
            "updateParagraphStyle": {
                "range": {"startIndex": 1, "endIndex": 1 + heading_len},
                "paragraphStyle": {
                    "alignment": "CENTER",
                    "spaceAbove": {"magnitude": 12, "unit": "PT"},
                },
                "fields": "alignment,spaceAbove",
            }
        })
        requests.append({
            "updateTextStyle": {
                "range": {"startIndex": 1, "endIndex": heading_len},  # exclou \n
                "textStyle": {"fontSize": {"magnitude": 20, "unit": "PT"}},
                "fields": "fontSize",
            }
        })

    # 12pt d'espai sobre el primer camp
    if fields_start_idx and fields_start_idx < 1 + len(full_text):
        requests.append({
            "updateParagraphStyle": {
                "range": {"startIndex": fields_start_idx, "endIndex": fields_start_idx + 1},
                "paragraphStyle": {"spaceAbove": {"magnitude": 12, "unit": "PT"}},
                "fields": "spaceAbove",
            }
        })

    # Crear document i aplicar text + format
    doc = docs_svc.documents().create(body={"title": card_id}).execute()
    doc_id = doc["documentId"]

    docs_svc.documents().batchUpdate(
        documentId=doc_id, body={"requests": requests}
    ).execute()

    # Inserir imatges en crides separades (per poder capturar errors individuals)
    # Ordre: QR primer (índex major) → foto (índex menor), per no desplaçar índexs
    def insert_image(idx, url, w, h, label):
        if idx is None or not url:
            print(f"(avís: {label} no disponible)", end=" ")
            return
        try:
            docs_svc.documents().batchUpdate(
                documentId=doc_id,
                body={"requests": [{
                    "insertInlineImage": {
                        "location": {"index": idx},
                        "uri": url,
                        "objectSize": {
                            "height": {"magnitude": h, "unit": "PT"},
                            "width":  {"magnitude": w, "unit": "PT"},
                        },
                    }
                }]},
            ).execute()
        except Exception as e:
            print(f"(avís: no s'ha pogut inserir {label}: {e})", end=" ")

    # Foto (92pt ample, altura auto per ratio) i QR (63×63) costat a costat
    qr_url = f"{QR_BASE_URL}/{card_id}.png" if (QR_DIR / f"{card_id}.png").exists() else None
    insert_image(images_idx, qr_url, 63, 63, f"QR {card_id}")

    photo_url = get_drive_image_url(drive_svc, None, img_cache, photo_id)
    insert_image(images_idx, photo_url, 92, 92, f"foto {photo_id}")

    # Capçalera i peu de pàgina amb logos
    add_header_footer(docs_svc, doc_id)

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
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Elimina els docs existents amb el mateix nom abans de crear-ne de nous",
    )
    parser.add_argument(
        "--list-columns",
        action="store_true",
        help="Mostra les columnes del full de càlcul i surt",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        metavar="N",
        help="Processa només els N primers cards (0 = tots)",
    )
    parser.add_argument(
        "--cards",
        nargs="+",
        metavar="CARD_ID",
        help="Processa només els cards amb aquests IDs",
    )
    args = parser.parse_args()

    print("Connectant als serveis de Google...")
    sheets_svc, docs_svc, drive_svc = get_services()

    print(f"Llegint fitxes de '{SHEET_NAME}'...")
    cards = read_cards(sheets_svc)
    print(f"Trobades {len(cards)} fitxes.")

    if args.list_columns:
        if cards:
            print("Columnes disponibles:")
            for col in cards[0].keys():
                print(f"  · {col!r}")
        return

    img_cache = load_image_cache()

    if args.cards:
        cards = [c for c in cards if c.get("cardId", "").strip() in args.cards]
    elif args.limit:
        cards = cards[:args.limit]

    for card in cards:
        card_id = card.get("cardId", "desconegut").strip()
        print(f"  Creant doc '{card_id}'... ", end="", flush=True)
        try:
            doc_id = create_card_doc(
                docs_svc, drive_svc, card,
                folder_id=args.folder_id,
                img_cache=img_cache,
                overwrite=args.overwrite,
            )
            print(f"OK → https://docs.google.com/document/d/{doc_id}")
        except Exception as exc:
            print(f"ERROR: {exc}")

    print("Fet!")


if __name__ == "__main__":
    main()

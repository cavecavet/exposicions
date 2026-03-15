#!/usr/bin/env python3
"""
Exporta els Google Docs de la carpeta 'tarjetes' de Drive a PDF.
- Desa els PDFs localment a targetes_pdf/
- Puja els PDFs a una nova carpeta 'targetes.pdf' a Drive

Ús:
  python3.14 scripts/export_pdfs.py [--source-folder NOM] [--dest-folder NOM]
"""

import argparse
import io
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

SCRIPT_DIR = Path(__file__).parent
TOKEN_FILE  = SCRIPT_DIR / "token.json"
LOCAL_DIR   = SCRIPT_DIR.parent / "targetes_pdf"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
]


def get_drive():
    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("drive", "v3", credentials=creds)


def find_folder(drive, name: str, parent_id: str | None = None) -> str | None:
    q = f"name = '{name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    if parent_id:
        q += f" and '{parent_id}' in parents"
    res = drive.files().list(q=q, fields="files(id,name)").execute()
    files = res.get("files", [])
    return files[0]["id"] if files else None


def create_folder(drive, name: str, parent_id: str | None = None) -> str:
    meta = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        meta["parents"] = [parent_id]
    f = drive.files().create(body=meta, fields="id").execute()
    return f["id"]


def list_docs(drive, folder_id: str) -> list[dict]:
    q = (
        f"'{folder_id}' in parents"
        " and mimeType = 'application/vnd.google-apps.document'"
        " and trashed = false"
    )
    res = drive.files().list(q=q, fields="files(id,name)", orderBy="name").execute()
    return res.get("files", [])


def export_as_pdf(drive, file_id: str) -> bytes:
    req = drive.files().export_media(fileId=file_id, mimeType="application/pdf")
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, req)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buf.getvalue()


def upload_pdf(drive, name: str, data: bytes, folder_id: str) -> str:
    # Eliminar PDF existent amb el mateix nom
    q = f"name = '{name}' and '{folder_id}' in parents and trashed = false"
    existing = drive.files().list(q=q, fields="files(id)").execute().get("files", [])
    for f in existing:
        drive.files().delete(fileId=f["id"]).execute()

    media = MediaIoBaseUpload(io.BytesIO(data), mimetype="application/pdf")
    f = drive.files().create(
        body={"name": name, "parents": [folder_id]},
        media_body=media,
        fields="id",
    ).execute()
    return f["id"]


def main():
    parser = argparse.ArgumentParser(description="Exporta docs de Drive a PDF.")
    parser.add_argument("--source-folder", default="tarjetes", help="Nom carpeta origen a Drive")
    parser.add_argument("--dest-folder",   default="targetes.pdf", help="Nom carpeta destí a Drive")
    args = parser.parse_args()

    drive = get_drive()

    # Carpeta origen
    src_id = find_folder(drive, args.source_folder)
    if not src_id:
        print(f"ERROR: no s'ha trobat la carpeta '{args.source_folder}' a Drive.")
        return
    print(f"Carpeta origen: '{args.source_folder}' ({src_id})")

    # Carpeta destí a Drive (crear si no existeix)
    dst_id = find_folder(drive, args.dest_folder)
    if dst_id:
        print(f"Carpeta destí existent: '{args.dest_folder}' ({dst_id})")
    else:
        dst_id = create_folder(drive, args.dest_folder)
        print(f"Carpeta destí creada: '{args.dest_folder}' ({dst_id})")

    # Carpeta local
    LOCAL_DIR.mkdir(exist_ok=True)
    print(f"Carpeta local: {LOCAL_DIR}")

    # Llistar docs
    docs = list_docs(drive, src_id)
    print(f"Trobats {len(docs)} documents.\n")

    for doc in docs:
        name = doc["name"]
        print(f"  Exportant '{name}'... ", end="", flush=True)
        try:
            pdf_data = export_as_pdf(drive, doc["id"])

            # Desar localment
            local_path = LOCAL_DIR / f"{name}.pdf"
            local_path.write_bytes(pdf_data)

            # Pujar a Drive
            upload_pdf(drive, f"{name}.pdf", pdf_data, dst_id)

            print(f"OK ({len(pdf_data)//1024} KB)")
        except Exception as e:
            print(f"ERROR: {e}")

    print(f"\nFet! PDFs desats a {LOCAL_DIR} i a Drive '{args.dest_folder}'.")


if __name__ == "__main__":
    main()

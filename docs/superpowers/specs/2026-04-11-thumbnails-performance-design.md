---
title: Optimització de càrrega amb thumbnails
date: 2026-04-11
status: approved
---

## Problema

Les imatges de la galeria (`images/Expo*.JPG`, `images/FotosCavet*.JPG`) són fotos de càmera sense comprimir, de 5–7MB cadascuna. La galeria les carrega totes al tamany original per mostrar miniaturas de ~300px, cosa que fa que la pàgina descarregui fins a 94MB. El `loading="lazy"` ja hi és però no és suficient: quan una imatge es carrega, baixa tot el fitxer original.

## Solució: Thumbnails locals

Generar versions reduïdes de cada imatge a `images/thumbs/`, i fer servir-les a la galeria. La vista de detall continua usant el fitxer original.

## Components

### 1. `scripts/generate_thumbnails.py` (nou)

- Llegeix tots els fitxers JPG/JPEG de `images/` (no recursiu, no subcarpetes)
- Per cada imatge, genera un thumbnail a `images/thumbs/<nom>.jpg`
  - Amplada màxima: 800px (es manté la proporció)
  - Qualitat JPEG: 80%
  - Format de sortida: sempre `.jpg` (minúscules), independentment de l'extensió original
- Salta imatges que ja tenen thumbnail (no reprocessa)
- Actualitza `images.json` afegint el camp `thumb` a cada entrada
- Ha d'executar-se amb `/opt/homebrew/bin/python3`

### 2. `images.json` (modificat)

Cada entrada passa de:
```json
{ "id": "Expo00006", "url": "images/Expo00006.JPG", "titulo": "Expo00006" }
```
a:
```json
{ "id": "Expo00006", "url": "images/Expo00006.JPG", "titulo": "Expo00006", "thumb": "images/thumbs/Expo00006.jpg" }
```

El camp `thumb` el genera i actualitza el script. Si una imatge no té thumbnail (per algun error), `thumb` serà `null` o absent, i la galeria farà fallback a `url`.

### 3. `index.html` (una línia canviada)

A `renderGallery()`, la funció `getImageUrl` retorna avui `img.url`. Cal que la galeria faci servir `img.thumb || img.url`. La vista de detall (`showDetail`) continua usant `img.url` directament sense canvis.

Canvi concret a `renderGallery()`:
```js
// Abans:
const imageUrl = getImageUrl(card.photoId);

// Després:
const img = imagesData.find(i => i.id === card.photoId);
const imageUrl = img ? (img.thumb || img.url) : '';
```

## Flux d'ús

1. Afegir imatges noves a `images/` i actualitzar `images.json`
2. Executar `python3 scripts/generate_thumbnails.py` — genera thumbs i actualitza `images.json`
3. `git add . && git commit && git push`

## Resultat esperat

| | Abans | Després |
|---|---|---|
| Pes total galeria | ~94MB | ~3–4MB |
| Mida per imatge (galeria) | 5–7MB | 80–150KB |
| Vista de detall | original | original (sense canvis) |

## Fitxers afectats

- `scripts/generate_thumbnails.py` — nou
- `images.json` — camp `thumb` afegit a cada entrada
- `index.html` — una línia canviada a `renderGallery()`
- `images/thumbs/` — carpeta nova amb les imatges reduïdes

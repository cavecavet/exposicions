# Exposició FotosCavet

Web estàtica per a l'exposició **FotosCavet**. Cada fitxa d'espècie marina té la seva pròpia URL, pensada per ser accessible mitjançant codis QR.

- Hosting: **GitHub Pages**
- Dades: fitxers JSON estàtics (sense backend)
- Autenticació: no requerida

## Estructura

```
/ (arrel del repo)
├── index.html                          # Aplicació (galeria + landing + detall)
├── cards.json                          # Dades de les 15 fitxes
├── images.json                         # Manifest de les imatges
├── images/                             # Fotografies
└── .github/workflows/deploy-pages.yml  # Desplegament automàtic a GitHub Pages
```

## Funcionament

1. **Galeria** (`#/`): mostra totes les fitxes en una graella. Fent clic a qualsevol fotografia s'accedeix a la seva fitxa.
2. **Landing** (`#/fitxa/CARD_ID`): pàgina informativa del projecte amb un botó per veure la fitxa. Aquesta és la URL que s'inclou als codis QR.
3. **Detall**: mostra la fotografia, nom comú, nom científic, comentari, autor de la foto i autor de la fitxa.

## Codis QR

Cada codi QR apunta a una URL amb el format:

```
https://<el-teu-domini>/#/fitxa/CARD_ID
```

Per exemple: `https://<el-teu-domini>/#/fitxa/01FC05`

## Editar les dades

Les dades de les fitxes es troben a `cards.json`. Per actualitzar-les, edita els camps de cada entrada:

- `commonName` — Nom comú de l'espècie
- `scientificName` — Nom científic
- `comment` — Comentari descriptiu
- `fotoAuthor` — Autor de la fotografia
- `cardAuthor` — Autor de la fitxa

# CardEditor

Editor de fitxes per a **FotosCavet**. Aplicació web on els usuaris poden "adoptar" una fotografia i completar-ne la fitxa amb el nom comú, nom científic i un comentari.

- Hosting: **GitHub Pages**
- Backend: **Google Apps Script** (Google Sheets com a base de dades)
- Autenticació: usuaris gestionats al full de càlcul

## Estructura

```
/ (arrel del repo)
├── index.html                          # Aplicació (login + galeria + editor)
├── images.json                         # Manifest de les imatges
├── images/                             # Fotografies
├── google_apps_script.js               # Codi del backend (Apps Script)
└── .github/workflows/deploy-pages.yml  # Desplegament automàtic a GitHub Pages
```

## Funcionament

1. L'usuari inicia sessió amb les credencials del full de càlcul.
2. Veu una graella amb totes les fotografies i el seu estat (lliure, adoptada per ell o per un altre).
3. Pot fer clic en una fotografia lliure per **adoptar-la** i omplir la fitxa.
4. Pot editar les seves fitxes o **alliberar-les** perquè un altre usuari les adopti.


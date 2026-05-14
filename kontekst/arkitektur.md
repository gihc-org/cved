# cved — projektarkitektur og vigtige detaljer

## Stack

- `cv.toml` — single source of truth for al CV-data
- `app.py` — FastAPI web server (port 8000)
- `render.py` — PDF via WeasyPrint, DOCX via python-docx, ODF via LibreOffice headless
- `templates/cv.html` — CV layout (to-kolonne: mørk sidebar + hvid main)
- `templates/cv.css` — master-stylesheet, bruges af både browser og WeasyPrint
- `templates/edit.html` — web-editor med dynamisk JS til jobs/uddannelser
- `main.py` — entrypoint: `uv run python main.py`

## Endpoints

| Metode | Sti | Formål |
|--------|-----|--------|
| GET | `/` | Web-editor |
| GET | `/preview` | Live HTML-preview |
| POST | `/save` | Gem formular til cv.toml |
| GET | `/download/pdf` | Download PDF |
| GET | `/download/docx` | Download DOCX |
| GET | `/download/odf` | Download ODT |

## Ikke-oplagte detaljer

- **TOML-nøgle til skills hedder `tags`** (ikke `items`) — `items` kolliderer med Pythons `dict.items()` i Jinja2-templates
- **Jinja2 Environment direkte** (ikke Starlette Jinja2Templates) — Starlettes LRU-cache er inkompatibel med Python 3.14
- **WeasyPrint + `border-radius`** — `<span>` med `border-radius` kræver `display: inline-block`, ellers renderes dobbelt kant i PDF
- **Profilbillede** — browser-crop eksporterer square JPEG som base64; CSS `border-radius: 50%` håndterer cirkulær visning overalt

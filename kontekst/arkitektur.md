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
- **Nye job i editoren** — `addExperience()` bruger `prepend()`, så jobkortet ligger først i `#exp-list`. Da `/save` parser i felt-rækkefølge, bliver det nyeste job automatisk første post i `experience` i `cv.toml`. Ingen sortering i backend.
- **httpx 0.28 i tests** — `data=<liste af tupler>` sendes som rå content (ikke form-body), så gentagne feltnavne forsvinder. Tests skal urlencodes eksplicit og sende `content=...` med `content-type: application/x-www-form-urlencoded` (se `post_form()` i `tests/test_e2e.py`).
- **pytest i sandkasse** — Starlettes `TestClient` hænger under Codex-sandkassen (selv mod en minimal FastAPI-app); kør testsuiten uden for sandkassen.

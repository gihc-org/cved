# AGENTS.md

This file provides guidance to AI coding agents working in this repository.

## Generelle guidelines

@.guidelines/security.md
@.guidelines/web-frontend.md
@.guidelines/testing-and-docs.md
@.guidelines/process.md

---

## Projektbeskrivelse

CV-generator der læser data fra `cv.toml` og eksporterer til PDF, DOCX og ODT. Inkluderer en web-editor til redigering af CV-data i browseren.

## Stack

- **Backend:** Python, FastAPI, Jinja2
- **Pakkemanager:** uv
- **PDF:** WeasyPrint
- **DOCX:** python-docx
- **ODT:** LibreOffice headless

## Arkitektur

```
cv.toml  ──→  app.py (FastAPI)  ──→  edit.html (formular)
         ──→  render.py         ──→  templates/cv.html + cv.css  ──→  WeasyPrint  ──→  output/cv.pdf
                                ──→  python-docx                 ──→  output/cv.docx
                                ──→  LibreOffice headless        ──→  output/cv.odt
```

`cv.toml` er den eneste kilde til al CV-data. Web-editoren og CLI-rendering læser og skriver begge udelukkende denne fil.

## Kom i gang

```bash
# Start udviklingsserver (med auto-reload)
uv run python main.py

# Generer filer direkte fra kommandolinjen
uv run python -c "import render, tomllib; cv=tomllib.load(open('cv.toml','rb')); render.to_pdf(cv)"
uv run python -c "import render, tomllib; cv=tomllib.load(open('cv.toml','rb')); render.to_docx(cv)"
uv run python -c "import render, tomllib; cv=tomllib.load(open('cv.toml','rb')); render.to_odf(cv)"

# Tilføj pakker
uv add <pakke>
```

Serveren kører på http://localhost:8000.

## Vigtige filer

| Fil | Formål |
|-----|--------|
| `cv.toml` | Al CV-data |
| `app.py` | FastAPI-app — web-editor og API-endpoints |
| `render.py` | PDF-, DOCX- og ODT-generering |
| `templates/cv.html` | CV-skabelon til WeasyPrint og browser-preview |
| `templates/cv.css` | Master-stylesheet (bruges af både browser og WeasyPrint) |

## Nøglebeslutninger

| ADR | Beslutning |
|-----|------------|
| [0012](~/projects/adrs/0012-feature-flags-via-empty-env.md) | Tom env-variabel som feature flag |
| [0013](~/projects/adrs/0013-owasp-by-default.md) | OWASP-sikkerhed som del af definition of done |

## Projekt-specifikke detaljer

### Datamodel i cv.toml

Topniveau-nøgler: `personal`, `summary`, `about`, `languages`, `skills`, `experience` (array), `education` (array).

Skills-listen hedder `tags` (ikke `items`) — `items` kolliderer med Pythons `dict.items()` i Jinja2-templates.

`experience`-poster kan have to niveauer af indhold:
- `bullets` — direkte punktliste
- `subsections` — array af `{heading, bullets}` til jobs med flere klientopgaver

### Formular-parsing i `app.py`

HTML-formularen bruger gentagne felter med samme `name` (fx mange `exp_company`-inputs). Parsing sker ved at gennemløbe `form.multi_items()` i orden — `exp_company` fungerer som separator der starter en ny job-post. Samme mønster gælder `edu_institution` for uddannelse. Rækkefølgen af form-felter er derfor afgørende for korrekt parsing.

### Browser-preview vs. PDF-rendering

`templates/cv.css` er master-stylesheet. Til browser-preview (`/preview`) kopieres filen til `static/cv.css` og template renderes med `css_url="/static/cv.css"`. Til PDF-rendering læser WeasyPrint filen direkte fra `templates/cv.css` via absolut sti.

### Python 3.14 / Jinja2

`app.py` bruger Jinja2's `Environment` direkte frem for Starlettes `Jinja2Templates` wrapper, fordi Starlettes implementation bruger en LRU-cache der er inkompatibel med Python 3.14.

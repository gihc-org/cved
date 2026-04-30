# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Kommandoer

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

## Arkitektur

`cv.toml` er den eneste kilde til al CV-data. Web-editoren og CLI-rendering læser og skriver begge udelukkende denne fil.

```
cv.toml  ──→  app.py (FastAPI)  ──→  edit.html (formular)
         ──→  render.py         ──→  templates/cv.html + cv.css  ──→  WeasyPrint  ──→  output/cv.pdf
                                ──→  python-docx                 ──→  output/cv.docx
                                ──→  LibreOffice headless        ──→  output/cv.odt
```

### Datamodel i cv.toml

Topniveau-nøgler: `personal`, `summary`, `about`, `languages`, `skills`, `experience` (array), `education` (array).

Skills-listen hedder `tags` (ikke `items`) — `items` kolliderer med Pythons `dict.items()` i Jinja2-templates.

`experience`-poster kan have tre niveauer af indhold:
- `bullets` — direkte punktliste
- `subsections` — array af `{heading, bullets}` til jobs med flere klientopgaver

### Formular-parsing i `app.py`

HTML-formularen bruger gentagne felter med samme `name` (fx mange `exp_company`-inputs). Parsing sker ved at gennemløbe `form.multi_items()` i orden — `exp_company` fungerer som separator der starter en ny job-post. Samme mønster gælder `edu_institution` for uddannelse. Rækkefølgen af form-felter er derfor afgørende for korrekt parsing.

### Browser-preview vs. PDF-rendering

`templates/cv.css` er master-stylesheet. Til browser-preview (`/preview`) kopieres filen til `static/cv.css` og template renderes med `css_url="/static/cv.css"`. Til PDF-rendering læser WeasyPrint filen direkte fra `templates/cv.css` via absolut sti.

### Python 3.14 / Jinja2

`app.py` bruger Jinja2's `Environment` direkte frem for Starlettes `Jinja2Templates` wrapper, fordi Starlettes implementation bruger en LRU-cache der er inkompatibel med Python 3.14.

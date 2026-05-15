# TODO

- [x] **Upload af profilbillede i web-editoren**
  - [x] Fil-input med live preview i `edit.html`
  - [x] Håndtering af UploadFile i `/save` routen
  - [x] Indsæt billede i DOCX-output via `render.py`
  - [x] Tilføj `python-multipart` dependency

- [x] **Cirkulær crop ved upload af profilbillede**
  - [x] Crop-modal i `edit.html` med canvas-baseret UI (ingen ekstern afhængighed)
  - [x] Cirkulær overlay der matcher `border-radius: 50%` i CV
  - [x] Drag + zoom-slider til positionering
  - [x] Eksporter som base64 i skjult input, afkod i backend og gem som fil

- [x] **Engelsk CV og versionering af CV**

  Mål: dansk og engelsk CV aktivt parallelt; mulighed for at gemme et snapshot med
  job-metadata når man sender en ansøgning, og efterfølgende generere PDF/DOCX af
  en hvilken som helst gemt version via web-UI.

  - [x] Opret `cv-en.toml` som engelsk parallelversion af `cv.toml`
  - [x] Udvid `render.py` til at tage en valgfri fil-sti som argument (så begge sprog kan renderes)
  - [x] Udvid API-endpoints til at understøtte `?lang=da|en` (eller tilsvarende)
  - [x] Opret `versions/da/` og `versions/en/` mapper
  - [x] Definer metadata-felter `_job` og `_note` øverst i snapshot-TOML (ignoreres af renderer)
  - [x] "Gem version"-knap i web-editoren: dialog med job-titel og note, gemmer snapshot
  - [x] `/versions`-side i web-editoren: liste over gemte versioner med metadata
  - [x] Preview/PDF/DOCX-knapper på hver version i `/versions`-siden
  - [x] "Gendan"-knap der kopierer en version til den aktive `cv.toml` / `cv-en.toml`

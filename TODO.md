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
  - [x] Auto-gem kladde ved gendan: aktive CV gemmes som `kladde.toml` inden overskrivning, vises øverst i /versions med orange badge

- [x] **Rediger metadata på gemte versioner**
  - [x] Ny POST-endpoint `/versions/{lang}/{filename}/update-meta` der opdaterer `_job`, `_note` og `_application` i version-filen uden at gendanne den
  - [x] Inline redigeringsformular på hvert versionskort i `versions.html`

- [x] **Ansøgning-felt på gemte versioner**
  - [x] Nyt metadatafelt `_application` i version-TOML (adskilt fra `_note`)
  - [x] Tekstfelt i "Gem version"-modal i `edit.html`
  - [x] Vis indikator på versionskort hvis ansøgning er gemt
  - [x] Redigerbar via inline-formularen (se ovenfor)

- [x] **IPFS-storage til profilbilleder**
  - [x] Upload billede til lokal IPFS-daemon (port 5001) og gem CID i cv.toml
  - [x] Proxy-endpoint `/ipfs/<cid>` i app.py der henter fra lokal gateway (port 8080)
  - [x] Rendering: brug proxy-URL i HTML-template og WeasyPrint, download bytes til DOCX
  - [x] Fjern lagring af billeder i `static/` og git

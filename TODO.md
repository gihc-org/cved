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

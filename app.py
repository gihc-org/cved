import base64
import tomllib
import tomli_w
import uuid
from pathlib import Path
from fastapi import FastAPI, Request, UploadFile
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader
import render as cv_render

BASE = Path(__file__).parent
app = FastAPI()

static_dir = BASE / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

_jinja = Environment(loader=FileSystemLoader(str(BASE / "templates")), auto_reload=True)


def render_template(name: str, **ctx) -> str:
    return _jinja.get_template(name).render(**ctx)

_flash: dict | None = None


def load_cv() -> dict:
    with open(BASE / "cv.toml", "rb") as f:
        return tomllib.load(f)


def save_cv(data: dict):
    with open(BASE / "cv.toml", "wb") as f:
        tomli_w.dump(data, f)


def _vals(form: dict, key: str) -> list[str]:
    v = form.get(key, [])
    if isinstance(v, str):
        v = [v]
    return [x for x in v if x.strip()]


@app.get("/", response_class=HTMLResponse)
async def editor(request: Request):
    global _flash
    flash = _flash
    _flash = None
    cv = load_cv()
    return HTMLResponse(render_template("edit.html", cv=cv, flash=flash))


@app.get("/preview", response_class=HTMLResponse)
async def preview(request: Request):
    cv = load_cv()
    html = cv_render.render_html(cv)
    # Inject absolute CSS path for browser preview
    html = html.replace(
        'href="{{ css_url | default(\'cv.css\') }}"',
        'href="/static/cv.css"'
    )
    # Serve CSS from static for preview
    import shutil
    shutil.copy(BASE / "templates" / "cv.css", static_dir / "cv.css")
    # Re-render with correct css_url
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader(str(BASE / "templates")))
    tmpl = env.get_template("cv.html")
    html = tmpl.render(cv=cv, css_url="/static/cv.css")
    return HTMLResponse(html)


@app.post("/save")
async def save(request: Request):
    global _flash
    form = await request.form()

    # Handle photo: crop-data (base64 from browser crop tool) takes priority over raw upload
    photo_path = ""
    crop_data = form.get("personal_photo_crop", "")
    if crop_data and isinstance(crop_data, str) and crop_data.startswith("data:image"):
        _, encoded = crop_data.split(",", 1)
        safe_name = f"photo_{uuid.uuid4().hex[:8]}.jpg"
        dest = static_dir / safe_name
        dest.write_bytes(base64.b64decode(encoded))
        photo_path = f"static/{safe_name}"
    else:
        upload = form.get("personal_photo")
        if upload is not None and hasattr(upload, "filename") and upload.filename:
            ext = Path(upload.filename).suffix or ".jpg"
            safe_name = f"photo_{uuid.uuid4().hex[:8]}{ext}"
            dest = static_dir / safe_name
            dest.write_bytes(await upload.read())
            photo_path = f"static/{safe_name}"

    form_dict: dict[str, list[str]] = {}
    for k, v in form.multi_items():
        if hasattr(v, "filename"):
            continue  # UploadFile, already handled
        form_dict.setdefault(k, []).append(v)

    def first(key: str, default: str = "") -> str:
        return form_dict.get(key, [default])[0]

    def many(key: str) -> list[str]:
        return [x for x in form_dict.get(key, []) if x.strip()]

    cv: dict = {}

    # Photo: use new upload, or clear if remove requested, or keep existing
    if photo_path:
        cv_photo = photo_path
    elif first("remove_photo"):
        cv_photo = ""
        # Clean up old photo file
        old = load_cv().get("personal", {}).get("photo", "")
        if old:
            old_path = BASE / old
            if old_path.exists():
                old_path.unlink()
    else:
        cv_photo = load_cv().get("personal", {}).get("photo", "")

    # Personal
    cv["personal"] = {
        "name": first("personal_name"),
        "title": first("personal_title"),
        "email": first("personal_email"),
        "phone": first("personal_phone"),
        "address": first("personal_address"),
        "photo": cv_photo,
    }

    # Summary / About
    cv["summary"] = {"text": first("summary_text")}
    cv["about"] = {"text": first("about_text")}

    # Languages
    lang_names = form_dict.get("lang_name", [])
    lang_levels = form_dict.get("lang_level", [])
    cv["languages"] = [
        {"name": n, "level": int(l)}
        for n, l in zip(lang_names, lang_levels)
        if n.strip()
    ]

    # Skills
    cv["skills"] = {"tags": many("skill")}

    # Experience — walk parallel arrays from form
    companies   = form_dict.get("exp_company", [])
    durations   = form_dict.get("exp_duration", [])
    exp_titles  = form_dict.get("exp_title", [])
    periods     = form_dict.get("exp_period", [])
    types       = form_dict.get("exp_type", [])
    descriptions = form_dict.get("exp_description", [])

    # bullets and subsections come interleaved per job — we need a smarter parse
    # We rebuild from the raw multi_items in order
    items = list(form.multi_items())

    def extract_experience(items):
        jobs = []
        cur: dict | None = None
        cur_sub: dict | None = None

        for k, v in items:
            if k == "exp_company":
                if cur is not None:
                    if cur_sub is not None:
                        cur.setdefault("subsections", []).append(cur_sub)
                        cur_sub = None
                    jobs.append(cur)
                cur = {
                    "company": v, "duration": "", "title": "",
                    "period": "", "type": "", "description": "",
                    "bullets": [], "subsections": []
                }
                cur_sub = None
            elif cur is None:
                continue
            elif k == "exp_duration":    cur["duration"] = v
            elif k == "exp_title":       cur["title"] = v
            elif k == "exp_period":      cur["period"] = v
            elif k == "exp_type":        cur["type"] = v
            elif k == "exp_description": cur["description"] = v
            elif k == "exp_bullets":
                if v.strip():
                    cur["bullets"].append(v)
            elif k == "exp_sub_heading":
                if cur_sub is not None:
                    cur.setdefault("subsections", []).append(cur_sub)
                cur_sub = {"heading": v, "bullets": []}
            elif k == "exp_sub_bullet":
                if v.strip() and cur_sub is not None:
                    cur_sub["bullets"].append(v)

        if cur is not None:
            if cur_sub is not None:
                cur.setdefault("subsections", []).append(cur_sub)
            jobs.append(cur)

        # Clean empty optional fields
        cleaned = []
        for j in jobs:
            if not j.get("company", "").strip():
                continue
            if not j.get("type"):      del j["type"]
            if not j.get("description"): del j["description"]
            if not j.get("bullets"):   del j["bullets"]
            if not j.get("subsections"): del j["subsections"]
            cleaned.append(j)
        return cleaned

    def extract_education(items):
        edus = []
        cur: dict | None = None
        for k, v in items:
            if k == "edu_institution":
                if cur is not None:
                    edus.append(cur)
                cur = {"institution": v, "duration": "", "degree": "", "period": "", "bullets": []}
            elif cur is None:
                continue
            elif k == "edu_duration": cur["duration"] = v
            elif k == "edu_degree":   cur["degree"] = v
            elif k == "edu_period":   cur["period"] = v
            elif k == "edu_bullets":
                if v.strip():
                    cur["bullets"].append(v)
        if cur is not None:
            edus.append(cur)
        cleaned = []
        for e in edus:
            if not e.get("institution", "").strip():
                continue
            if not e.get("bullets"):
                del e["bullets"]
            cleaned.append(e)
        return cleaned

    cv["experience"] = extract_experience(items)
    cv["education"] = extract_education(items)

    save_cv(cv)
    _flash = {"type": "success", "message": "CV gemt!"}
    return RedirectResponse("/", status_code=303)


@app.get("/download/pdf")
async def download_pdf():
    cv = load_cv()
    path = cv_render.to_pdf(cv)
    return FileResponse(str(path), filename="cv.pdf", media_type="application/pdf")


@app.get("/download/docx")
async def download_docx():
    cv = load_cv()
    path = cv_render.to_docx(cv)
    return FileResponse(str(path), filename="cv.docx",
                        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")


@app.get("/download/odf")
async def download_odf():
    cv = load_cv()
    path = cv_render.to_odf(cv)
    return FileResponse(str(path), filename="cv.odt",
                        media_type="application/vnd.oasis.opendocument.text")

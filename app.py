import base64
import re
import subprocess
import tomllib
import tomli_w
import urllib.request
import uuid
from datetime import date, datetime
from pathlib import Path
from fastapi import FastAPI, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader
import render as cv_render

IPFS_GW = "http://localhost:8080"


def ipfs_upload(data: bytes) -> str:
    result = subprocess.run(
        ["ipfs", "add", "-q", "--stdin-name", "photo.jpg"],
        input=data, capture_output=True, check=True,
    )
    return result.stdout.decode().strip()


def _is_cid(photo: str) -> bool:
    return bool(photo) and "/" not in photo

BASE = Path(__file__).parent
app = FastAPI()

static_dir = BASE / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

_jinja = Environment(loader=FileSystemLoader(str(BASE / "templates")), auto_reload=True)

CV_FILES = {
    "da": BASE / "cv.toml",
    "en": BASE / "cv-en.toml",
}


def render_template(name: str, **ctx) -> str:
    return _jinja.get_template(name).render(**ctx)


_flash: dict | None = None


def load_cv(lang: str = "da") -> dict:
    with open(CV_FILES[lang], "rb") as f:
        return tomllib.load(f)


def save_cv(data: dict, lang: str = "da") -> None:
    data = {"lang": lang, **data}
    with open(CV_FILES[lang], "wb") as f:
        tomli_w.dump(data, f)


def _preview_html(cv: dict) -> str:
    import shutil
    shutil.copy(BASE / "templates" / "cv.css", static_dir / "cv.css")
    cv = dict(cv)
    cv["personal"] = dict(cv.get("personal", {}))
    photo = cv["personal"].get("photo", "")
    if _is_cid(photo):
        cv["personal"]["photo"] = f"/ipfs/{photo}"
    env = Environment(loader=FileSystemLoader(str(BASE / "templates")))
    tmpl = env.get_template("cv.html")
    cv_lang = cv.get("lang", "da")
    labels = cv_render.LABELS.get(cv_lang, cv_render.LABELS["da"])
    return tmpl.render(cv=cv, css_url="/static/cv.css", labels=labels)


@app.get("/ipfs/{cid}")
def ipfs_proxy(cid: str):
    if not re.match(r"^[a-zA-Z0-9]+$", cid):
        return HTMLResponse("Ugyldigt CID", status_code=400)
    try:
        with urllib.request.urlopen(f"{IPFS_GW}/ipfs/{cid}", timeout=15) as r:
            content = r.read()
            ct = r.headers.get("Content-Type", "image/jpeg")
        return Response(content=content, media_type=ct)
    except Exception:
        return HTMLResponse("Billede ikke tilgængeligt", status_code=502)


def list_versions(lang: str) -> list[dict]:
    versions_dir = BASE / "versions" / lang
    if not versions_dir.exists():
        return []
    kladde = None
    regular = []
    for f in sorted(versions_dir.glob("*.toml"), reverse=True):
        try:
            with open(f, "rb") as fp:
                data = tomllib.load(fp)
            if f.name == "kladde.toml":
                kladde = {
                    "filename": f.name,
                    "job": data.get("_job", "Kladde"),
                    "note": data.get("_note", ""),
                    "application": data.get("_application", ""),
                    "date": "",
                    "is_kladde": True,
                }
            else:
                regular.append({
                    "filename": f.name,
                    "job": data.get("_job", f.stem),
                    "note": data.get("_note", ""),
                    "application": data.get("_application", ""),
                    "date": f.stem[:10],
                    "is_kladde": False,
                })
        except Exception:
            pass
    return ([kladde] if kladde else []) + regular


def _vals(form: dict, key: str) -> list[str]:
    v = form.get(key, [])
    if isinstance(v, str):
        v = [v]
    return [x for x in v if x.strip()]


@app.get("/", response_class=HTMLResponse)
async def editor(request: Request, lang: str = Query("da")):
    global _flash
    flash = _flash
    _flash = None
    cv = load_cv(lang)
    return HTMLResponse(render_template("edit.html", cv=cv, flash=flash, lang=lang))


@app.get("/preview", response_class=HTMLResponse)
async def preview(request: Request, lang: str = Query("da")):
    cv = load_cv(lang)
    return HTMLResponse(_preview_html(cv))


@app.post("/save")
async def save(request: Request):
    global _flash
    form = await request.form()

    # Determine language from hidden form field
    lang = form.get("lang", "da") or "da"

    # Handle photo: crop-data (base64 from browser crop tool) takes priority over raw upload
    new_cid = ""
    crop_data = form.get("personal_photo_crop", "")
    if crop_data and isinstance(crop_data, str) and crop_data.startswith("data:image"):
        _, encoded = crop_data.split(",", 1)
        new_cid = ipfs_upload(base64.b64decode(encoded))
    else:
        upload = form.get("personal_photo")
        if upload is not None and hasattr(upload, "filename") and upload.filename:
            new_cid = ipfs_upload(await upload.read())

    form_dict: dict[str, list[str]] = {}
    for k, v in form.multi_items():
        if hasattr(v, "filename"):
            continue
        form_dict.setdefault(k, []).append(v)

    def first(key: str, default: str = "") -> str:
        return form_dict.get(key, [default])[0]

    def many(key: str) -> list[str]:
        return [x for x in form_dict.get(key, []) if x.strip()]

    cv: dict = {}

    if new_cid:
        cv_photo = new_cid
    elif first("remove_photo"):
        cv_photo = ""
    else:
        cv_photo = load_cv(lang).get("personal", {}).get("photo", "")

    cv["personal"] = {
        "name": first("personal_name"),
        "title": first("personal_title"),
        "email": first("personal_email"),
        "phone": first("personal_phone"),
        "address": first("personal_address"),
        "photo": cv_photo,
    }

    cv["summary"] = {"text": first("summary_text")}
    cv["about"] = {"text": first("about_text")}

    lang_names = form_dict.get("lang_name", [])
    lang_levels = form_dict.get("lang_level", [])
    cv["languages"] = [
        {"name": n, "level": int(l)}
        for n, l in zip(lang_names, lang_levels)
        if n.strip()
    ]

    cv["skills"] = {"tags": many("skill")}

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

        cleaned = []
        for j in jobs:
            if not j.get("company", "").strip():
                continue
            if not j.get("type"):        del j["type"]
            if not j.get("description"): del j["description"]
            if not j.get("bullets"):     del j["bullets"]
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

    save_cv(cv, lang)
    _flash = {"type": "success", "message": "CV gemt!"}
    return RedirectResponse(f"/?lang={lang}", status_code=303)


@app.post("/save-version")
async def save_version_endpoint(request: Request):
    global _flash
    form = await request.form()
    lang = (form.get("lang") or "da").strip()
    job = (form.get("_job") or "").strip()
    note = (form.get("_note") or "").strip()

    application = (form.get("_application") or "").strip()

    cv = load_cv(lang)
    cv["_job"] = job
    cv["_note"] = note
    cv["_application"] = application

    slug = re.sub(r"[^a-z0-9]+", "-", job.lower())[:40].strip("-") or "version"
    filename = f"{date.today().isoformat()}_{slug}.toml"

    versions_dir = BASE / "versions" / lang
    versions_dir.mkdir(parents=True, exist_ok=True)
    with open(versions_dir / filename, "wb") as f:
        tomli_w.dump(cv, f)

    _flash = {"type": "success", "message": f"Version gemt: {filename}"}
    return RedirectResponse("/versions", status_code=303)


@app.post("/versions/{lang}/{filename}/update-meta")
async def update_version_meta(lang: str, filename: str, request: Request):
    global _flash
    version_path = BASE / "versions" / lang / filename
    if not version_path.exists():
        return HTMLResponse("Version ikke fundet", status_code=404)
    form = await request.form()
    job = (form.get("_job") or "").strip()
    note = (form.get("_note") or "").strip()
    application = (form.get("_application") or "").strip()

    with open(version_path, "rb") as f:
        cv = tomllib.load(f)
    cv["_job"] = job
    cv["_note"] = note
    cv["_application"] = application
    with open(version_path, "wb") as f:
        tomli_w.dump(cv, f)

    _flash = {"type": "success", "message": f"Metadata opdateret: {filename}"}
    return RedirectResponse("/versions", status_code=303)


@app.get("/versions", response_class=HTMLResponse)
async def versions_page():
    global _flash
    flash = _flash
    _flash = None
    return HTMLResponse(render_template(
        "versions.html",
        versions_da=list_versions("da"),
        versions_en=list_versions("en"),
        flash=flash,
    ))


@app.get("/versions/{lang}/{filename}/preview", response_class=HTMLResponse)
async def preview_version(lang: str, filename: str):
    version_path = BASE / "versions" / lang / filename
    if not version_path.exists():
        return HTMLResponse("Version ikke fundet", status_code=404)
    with open(version_path, "rb") as f:
        cv = tomllib.load(f)
    return HTMLResponse(_preview_html(cv))


@app.get("/versions/{lang}/{filename}/download/pdf")
async def download_version_pdf(lang: str, filename: str):
    version_path = BASE / "versions" / lang / filename
    if not version_path.exists():
        return HTMLResponse("Version ikke fundet", status_code=404)
    with open(version_path, "rb") as f:
        cv = tomllib.load(f)
    out_path = BASE / "output" / "version-temp.pdf"
    out_path.parent.mkdir(exist_ok=True)
    cv_render.to_pdf(cv, out_path=out_path)
    stem = Path(filename).stem
    return FileResponse(str(out_path), filename=f"cv-{stem}.pdf", media_type="application/pdf")


@app.get("/versions/{lang}/{filename}/download/docx")
async def download_version_docx(lang: str, filename: str):
    version_path = BASE / "versions" / lang / filename
    if not version_path.exists():
        return HTMLResponse("Version ikke fundet", status_code=404)
    with open(version_path, "rb") as f:
        cv = tomllib.load(f)
    out_path = BASE / "output" / "version-temp.docx"
    out_path.parent.mkdir(exist_ok=True)
    cv_render.to_docx(cv, out_path=out_path)
    stem = Path(filename).stem
    return FileResponse(
        str(out_path),
        filename=f"cv-{stem}.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@app.post("/versions/{lang}/{filename}/restore")
async def restore_version(lang: str, filename: str):
    global _flash
    version_path = BASE / "versions" / lang / filename
    if not version_path.exists():
        return HTMLResponse("Version ikke fundet", status_code=404)

    # Auto-gem det aktive CV som kladde inden overskrivning
    current_cv = load_cv(lang)
    kladde_label = "Kladde" if lang == "da" else "Draft"
    timestamp = datetime.now().strftime("%d. %b %Y kl. %H:%M")
    current_cv["_job"] = kladde_label
    current_cv["_note"] = f"Auto-gemt inden gendan af '{Path(filename).stem}' ({timestamp})"
    versions_dir = BASE / "versions" / lang
    versions_dir.mkdir(parents=True, exist_ok=True)
    with open(versions_dir / "kladde.toml", "wb") as f:
        tomli_w.dump(current_cv, f)

    with open(version_path, "rb") as f:
        cv = tomllib.load(f)
    cv = cv_render.strip_meta(cv)
    save_cv(cv, lang)
    _flash = {"type": "success", "message": f"Version gendannet — kladde auto-gemt"}
    return RedirectResponse(f"/?lang={lang}", status_code=303)


@app.get("/download/pdf")
async def download_pdf(lang: str = Query("da")):
    cv = load_cv(lang)
    path = cv_render.to_pdf(cv)
    return FileResponse(str(path), filename=f"cv-{lang}.pdf", media_type="application/pdf")


@app.get("/download/docx")
async def download_docx(lang: str = Query("da")):
    cv = load_cv(lang)
    path = cv_render.to_docx(cv)
    return FileResponse(
        str(path),
        filename=f"cv-{lang}.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@app.get("/download/odf")
async def download_odf(lang: str = Query("da")):
    cv = load_cv(lang)
    path = cv_render.to_odf(cv)
    return FileResponse(str(path), filename=f"cv-{lang}.odt", media_type="application/vnd.oasis.opendocument.text")

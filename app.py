"""Paper Log web app. Run: .venv/bin/python app.py"""
from datetime import date

from flask import Flask, abort, flash, redirect, render_template, request, url_for

import papers
import store
from config import CHALLENGE_TAG, PORT

app = Flask(__name__)
app.secret_key = "paper-log-local"


def linkedin_draft(note):
    day = store.day_number(note.get("date", ""))
    tags = ["#MachineLearning", "#DeepLearning"]
    area = note.get("area")
    if area in ("CV", "Multimodal"):
        tags.insert(0, "#ComputerVision")
    if area in ("NLP", "Multimodal"):
        tags.insert(0, "#NLP")
    for t in (note.get("tags") or "").split(","):
        t = "".join(ch for ch in t.title() if ch.isalnum())
        if t:
            tags.append(f"#{t}")

    parts = [f"Day {day} of {CHALLENGE_TAG} 📄", "", f"Today I read: {note.get('title', '')}"]
    if note.get("url"):
        parts.append(note["url"])
    parts.append("")
    for key, label in (("tldr", "💡 TL;DR"), ("problem", "🔍 Problem"), ("method", "⚙️ Method"),
                       ("results", "📊 Results"), ("my_take", "🤔 My take")):
        if note.get(key):
            parts.append(f"{label}: {note[key].strip()}")
            parts.append("")
    if note.get("rating"):
        parts.append(f"Rating: {'⭐' * int(note['rating'])} ({note['rating']}/5)")
    parts.append(f"Full notes: {store.note_link(note['slug'])}")
    parts += ["", " ".join(dict.fromkeys(tags))]
    return "\n".join(parts)


def note_from_form(form):
    note = {k: form.get(k, "").strip() for k in store.META_FIELDS}
    note.update({k: form.get(k, "").strip() for k, _ in store.SECTIONS})
    if note["area"] not in store.AREAS:
        note["area"] = "Other"
    if note["rating"] not in {"1", "2", "3", "4", "5"}:
        note["rating"] = "3"
    if not note["date"]:
        note["date"] = date.today().isoformat()
    return note


@app.context_processor
def globals_():
    return {"streak": store.streak(), "done_today": store.done_today()}


@app.route("/")
def index():
    sugg = papers.suggestions(refresh=request.args.get("refresh") == "1")
    notes = store.all_notes()
    return render_template(
        "index.html",
        sugg=sugg,
        recent=notes[:5],
        total=len(notes),
        read_days=store.read_days(),
        calendar=_calendar(),
        unpushed=store.unpushed_count(),
        has_remote=store.has_remote(),
    )


def _calendar(weeks=12):
    """Last N weeks as columns of 7 days (Mon..Sun), GitHub-style."""
    from datetime import timedelta
    today = date.today()
    start = today - timedelta(days=today.weekday() + 7 * (weeks - 1))
    days = store.read_days()
    cols = []
    for w in range(weeks):
        col = []
        for d in range(7):
            day = start + timedelta(days=7 * w + d)
            col.append({"date": day.isoformat(), "read": day.isoformat() in days, "future": day > today})
        cols.append(col)
    return cols


@app.route("/new", methods=["GET", "POST"])
def new():
    if request.method == "POST":
        note = note_from_form(request.form)
        if not note["title"]:
            flash("Title is required.", "error")
            return render_template("edit.html", note=note, sections=store.SECTIONS, areas=store.AREAS, slug=None)
        slug = store.save(note)
        store.commit(f"read: {note['title']}")
        flash("Saved and committed. Nice work! 🔥", "ok")
        return redirect(url_for("view", slug=slug))

    note = {"date": date.today().isoformat(), "rating": "3", "area": request.args.get("area", "")}
    ref = request.args.get("arxiv", "")
    if ref:
        arxiv_id = papers.parse_arxiv_id(ref)
        meta = papers.fetch_arxiv(arxiv_id) if arxiv_id else None
        if meta:
            note.update({k: meta[k] for k in ("title", "url", "authors")})
            if not note["area"]:
                note["area"] = meta["area"]
            note["abstract"] = meta["summary"]
        else:
            flash(f"Couldn't fetch metadata for “{ref}”. Fill it in by hand.", "error")
    return render_template("edit.html", note=note, sections=store.SECTIONS, areas=store.AREAS, slug=None)


@app.route("/note/<slug>")
def view(slug):
    note = store.load(slug) or abort(404)
    return render_template("note.html", note=note, sections=store.SECTIONS, draft=linkedin_draft(note))


@app.route("/note/<slug>/edit", methods=["GET", "POST"])
def edit(slug):
    existing = store.load(slug) or abort(404)
    if request.method == "POST":
        note = note_from_form(request.form)
        if not note["title"]:
            flash("Title is required.", "error")
            return render_template("edit.html", note=note, sections=store.SECTIONS, areas=store.AREAS, slug=slug)
        store.save(note, slug=slug)
        store.commit(f"update: {note['title']}")
        flash("Updated.", "ok")
        return redirect(url_for("view", slug=slug))
    return render_template("edit.html", note=existing, sections=store.SECTIONS, areas=store.AREAS, slug=slug)


@app.post("/note/<slug>/delete")
def delete(slug):
    note = store.load(slug) or abort(404)
    store.delete(slug)
    store.commit(f"remove: {note.get('title', slug)}")
    flash("Note deleted.", "ok")
    return redirect(url_for("notes"))


@app.route("/notes")
def notes():
    area = request.args.get("area", "")
    q = request.args.get("q", "").lower()
    items = store.all_notes()
    if area:
        items = [n for n in items if n.get("area") == area]
    if q:
        items = [n for n in items if q in " ".join(str(v) for v in n.values()).lower()]
    return render_template("notes.html", notes=items, areas=store.AREAS, area=area, q=request.args.get("q", ""))


@app.post("/push")
def push():
    ok, msg = store.push()
    flash(("Pushed to GitHub. " if ok else "Push failed: ") + msg[-300:], "ok" if ok else "error")
    return redirect(request.referrer or url_for("index"))


if __name__ == "__main__":
    store.write_readme()
    app.run(host="127.0.0.1", port=PORT, debug=False)

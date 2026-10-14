"""Notes as markdown files in notes/, plus streak, README index and git."""
import re
import subprocess
from datetime import date, timedelta

from config import GITHUB_REPO_URL, NOTES_DIR, ROOT

META_FIELDS = ["title", "url", "authors", "area", "date", "rating", "tags"]
SECTIONS = [
    ("tldr", "TL;DR"),
    ("problem", "Problem"),
    ("method", "Method"),
    ("results", "Results"),
    ("strengths", "Strengths"),
    ("weaknesses", "Weaknesses"),
    ("my_take", "My Take"),
    ("questions", "Open Questions"),
]
AREAS = ["CV", "NLP", "Multimodal", "Other"]
SLUG_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9-]+$")


def slugify(title):
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return s[:60].rstrip("-") or "paper"


def valid_slug(slug):
    return bool(SLUG_RE.match(slug or ""))


def _one_line(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def to_markdown(note):
    lines = ["---"]
    for key in META_FIELDS:
        lines.append(f"{key}: {_one_line(note.get(key))}")
    lines += ["---", "", f"# {_one_line(note.get('title'))}", ""]
    if note.get("url"):
        lines += [f"**Paper:** {_one_line(note['url'])}  ", ""]
    if note.get("authors"):
        lines += [f"**Authors:** {_one_line(note['authors'])}  ", ""]
    lines += [f"**Area:** {note.get('area', '')} · **Rating:** {note.get('rating', '')}/5 · **Read on:** {note.get('date', '')}", ""]
    for key, heading in SECTIONS:
        body = (note.get(key) or "").strip().replace("\r\n", "\n")
        if body:
            lines += [f"## {heading}", "", body, ""]
    return "\n".join(lines)


def from_markdown(text):
    note = {}
    m = re.match(r"---\n(.*?)\n---\n", text, flags=re.S)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                note[k.strip()] = v.strip()
    body = text[m.end():] if m else text
    by_heading = {h: k for k, h in SECTIONS}
    for chunk in re.split(r"^## ", body, flags=re.M)[1:]:
        heading, _, content = chunk.partition("\n")
        key = by_heading.get(heading.strip())
        if key:
            note[key] = content.strip()
    return note


def load(slug):
    if not valid_slug(slug):
        return None
    path = NOTES_DIR / f"{slug}.md"
    if not path.exists():
        return None
    note = from_markdown(path.read_text())
    note["slug"] = slug
    return note


def all_notes():
    notes = []
    for path in NOTES_DIR.glob("*.md"):
        if valid_slug(path.stem):
            note = from_markdown(path.read_text())
            note["slug"] = path.stem
            notes.append(note)
    notes.sort(key=lambda n: (n.get("date", ""), n["slug"]), reverse=True)
    return notes


def save(note, slug=None):
    """Write the note; returns its slug. A new note gets slug <date>-<title>."""
    NOTES_DIR.mkdir(exist_ok=True)
    if not slug:
        base = f"{note['date']}-{slugify(note['title'])}"
        slug, i = base, 2
        while (NOTES_DIR / f"{slug}.md").exists():
            slug, i = f"{base}-{i}", i + 1
    (NOTES_DIR / f"{slug}.md").write_text(to_markdown(note))
    write_readme()
    return slug


def delete(slug):
    if valid_slug(slug):
        (NOTES_DIR / f"{slug}.md").unlink(missing_ok=True)
        write_readme()


def read_days():
    return {n.get("date") for n in all_notes() if n.get("date")}


def streak():
    """Consecutive days with a note, ending today (or yesterday if today isn't done yet)."""
    days = read_days()
    day = date.today()
    if day.isoformat() not in days:
        day -= timedelta(days=1)
    count = 0
    while day.isoformat() in days:
        count += 1
        day -= timedelta(days=1)
    return count


def done_today():
    return date.today().isoformat() in read_days()


def day_number(note_date):
    """1-based index of this note's day among all reading days (for 'Day N of ...')."""
    days = sorted(read_days())
    return days.index(note_date) + 1 if note_date in days else len(days) + 1


def note_link(slug):
    if GITHUB_REPO_URL:
        return f"{GITHUB_REPO_URL}/blob/main/notes/{slug}.md"
    return f"notes/{slug}.md"


def write_readme():
    notes = all_notes()
    counts = {a: sum(1 for n in notes if n.get("area") == a) for a in AREAS}
    lines = [
        "# Paper Log",
        "",
        "A daily habit of reading and reviewing papers in **Computer Vision** and **NLP**.",
        "",
        f"**Papers read:** {len(notes)} · **Current streak:** {streak()} day{'' if streak() == 1 else 's'} · "
        + " · ".join(f"**{a}:** {c}" for a, c in counts.items() if c),
        "",
        "| Date | Paper | Area | Rating | TL;DR |",
        "|------|-------|------|--------|-------|",
    ]
    for n in notes:
        title = _one_line(n.get("title")).replace("|", "\\|")
        tldr = _one_line(n.get("tldr")).replace("|", "\\|")
        if len(tldr) > 140:
            tldr = tldr[:137] + "..."
        stars = "★" * int(n["rating"]) if str(n.get("rating", "")).isdigit() else ""
        lines.append(f"| {n.get('date', '')} | [{title}](notes/{n['slug']}.md) | {n.get('area', '')} | {stars} | {tldr} |")
    (ROOT / "README.md").write_text("\n".join(lines) + "\n")


def _git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=60)


def commit(message):
    _git("add", "notes", "README.md")
    r = _git("commit", "-m", message)
    return r.returncode == 0


def has_remote():
    return bool(_git("remote").stdout.strip())


def unpushed_count():
    r = _git("rev-list", "--count", "@{u}..HEAD")
    if r.returncode != 0:
        r = _git("rev-list", "--count", "HEAD")
    try:
        return int(r.stdout.strip())
    except ValueError:
        return 0


def push():
    if not has_remote():
        return False, "No git remote set. See SETUP.md to connect a GitHub repo."
    r = _git("push", "-u", "origin", "HEAD")
    out = (r.stdout + r.stderr).strip()
    return r.returncode == 0, out or "Pushed."

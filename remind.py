"""Email a reminder if today's paper hasn't been logged yet.

Run by the systemd timer a few times a day. `--test` sends even if today is done.
"""
import html
import smtplib
import sys
from datetime import date
from email.message import EmailMessage

import papers
import store
from config import MAIL_TO, SITE_URL, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USER


def build_message():
    s = store.streak()
    total = len(store.all_notes())
    try:
        picks = papers.suggestions()["hf"][:3]
    except Exception:
        picks = []

    if s:
        subject = f"🔥 Keep your {s}-day streak alive — today's paper is waiting"
        lead = f"You're on a <b>{s}-day streak</b>. Don't break it today!"
    else:
        subject = "📄 Time for today's paper"
        lead = "No streak running right now — today is a great day to start one."

    items = "".join(
        f'<li style="margin-bottom:10px"><a href="{SITE_URL}/new?arxiv={p["id"]}">{html.escape(p["title"])}</a>'
        f'<br><span style="color:#666;font-size:13px">{html.escape(p["summary"][:180])}…</span></li>'
        for p in picks
    )
    body = f"""<div style="font-family:system-ui,sans-serif;max-width:560px;line-height:1.5">
<h2 style="margin:0 0 8px">Paper of the day 📄</h2>
<p>{lead}<br>Papers read so far: <b>{total}</b>.</p>
{f'<p>Popular on Hugging Face today:</p><ul style="padding-left:18px">{items}</ul>' if items else ''}
<p><a href="{SITE_URL}" style="display:inline-block;background:#2f6feb;color:#fff;padding:10px 16px;border-radius:8px;text-decoration:none">Open Paper Log</a></p>
<p style="color:#888;font-size:12px">You get this until today's note is saved.</p>
</div>"""

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = MAIL_TO
    msg.set_content(f"{lead.replace('<b>', '').replace('</b>', '')}\nOpen Paper Log: {SITE_URL}")
    msg.add_alternative(body, subtype="html")
    return msg


def main():
    test = "--test" in sys.argv
    if store.done_today() and not test:
        print("Already read today, no reminder.")
        return 0
    if not SMTP_USER or not SMTP_PASSWORD:
        print("SMTP_USER / SMTP_PASSWORD missing in .env — see SETUP.md.", file=sys.stderr)
        return 1
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
        smtp.login(SMTP_USER, SMTP_PASSWORD)
        smtp.send_message(build_message())
    print(f"Reminder sent to {MAIL_TO} ({date.today()}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

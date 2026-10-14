# Paper Log — setup

Local website for logging one CV/NLP paper a day, with reminder emails and a public GitHub log.

## Install

```bash
./setup.sh
```

This creates the venv, a git repo, and two systemd user units:

- `paper-log-web.service` — the site at http://localhost:5050, starts on login.
- `paper-log-remind.timer` — at 10:00, 15:00 and 20:00 it emails you **only if today's note isn't saved yet**. If the computer was off, it fires once on next boot.

## Email (Gmail)

1. Turn on 2-Step Verification on your Google account.
2. Create an App Password: https://myaccount.google.com/apppasswords
3. Put it in `.env` as `SMTP_PASSWORD=...` (also set `SMTP_USER` / `MAIL_TO`).
4. Test: `.venv/bin/python remind.py --test`

## GitHub

Create an empty public repo (e.g. `paper-log`) on GitHub, then:

```bash
git remote add origin git@github.com:<you>/paper-log.git
git push -u origin main
```

and set `GITHUB_REPO_URL=https://github.com/<you>/paper-log` in `.env`, then
`systemctl --user restart paper-log-web`. Each saved note is committed automatically;
the **Push to GitHub** button on the home page publishes them. `README.md` is regenerated
as a public index of everything you've read — don't edit it by hand.

## Handy commands

```bash
systemctl --user status paper-log-web        # is the site up?
journalctl --user -u paper-log-remind -n 20  # last reminder runs
systemctl --user disable --now paper-log-remind.timer   # pause reminders
```

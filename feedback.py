"""
AI-routed visitor feedback for the Canyon Lake Monitor.

process_feedback(name, email, text, page) -> (ok, action, github_issue_url)

Routes via the `claude` CLI (no ANTHROPIC_API_KEY needed in the app):
- Bugs / feature requests / code suggestions -> GitHub issue
- Everything else                            -> email to FEEDBACK_EMAIL
- claude CLI not found                       -> fallback plain email, no crash
- Any error                                  -> fallback plain email, no crash

Visitors are anonymous; name/email are optional and included when given.
"""

import json
import logging
import os
import smtplib
import subprocess
import urllib.error
import urllib.request
from email.mime.text import MIMEText

log = logging.getLogger(__name__)

_PROMPT = """\
You are the feedback assistant for iscanyonlakefullyet.org, a free public site
showing real-time Canyon Lake (Texas) water levels. An anonymous visitor has
submitted feedback through the site. Triage it and decide where to route it.

Rules:
- Route to github_issue for: bugs, broken pages, wrong or stale data, UI
  glitches, performance problems, and feature requests or suggestions to
  improve or change the site or its code.
- Route to email for: general comments, questions, praise, thanks, lake or
  community concerns, or anything that is not a software bug or change request.
- Be concise but include all relevant context in the title/body.
- If the visitor gave a name or email, attribute the feedback to them in the body.
- Note which page of the site the feedback was submitted from.

Output ONLY a single JSON object — no other text, no markdown fences.

For bugs / feature requests / code suggestions:
{"action":"github_issue","title":"<short title>","body":"<full body>","labels":["bug"|"enhancement"]}

For everything else:
{"action":"email","subject":"<subject>","body":"<full body>"}
"""


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def process_feedback(
    name: str,
    email: str,
    text: str,
    page: str,
) -> tuple[bool, str, str | None]:
    """Triage and route visitor feedback via the claude CLI.

    Returns (success, action, github_issue_url).
    """
    try:
        result = _call_claude_cli(name, email, text, page)
    except Exception as exc:
        log.error("claude CLI error in process_feedback: %s", exc)
        ok = _fallback_email(name, email, text, page)
        return ok, "fallback_email", None

    action = result.get("action")

    if action == "github_issue":
        github_url, ok = _create_github_issue(
            result["title"], result["body"], result.get("labels", []), name, email)
        if ok:
            return True, "github_issue", github_url
        log.warning("GitHub issue creation failed; falling back to email for: %s",
                    result["title"])
        ok = _send_email(f"[Feature/Bug] {result['title']}", result["body"])
        return ok, "fallback_email", None

    if action == "email":
        ok = _send_email(result["subject"], result["body"])
        return ok, "email", None

    log.warning("Unexpected action from claude CLI: %s; falling back to email", action)
    ok = _fallback_email(name, email, text, page)
    return ok, "fallback_email", None


# ---------------------------------------------------------------------------
# claude CLI call
# ---------------------------------------------------------------------------

def _call_claude_cli(name: str, email: str, text: str, page: str) -> dict:
    """Invoke the claude CLI and return parsed JSON routing decision."""
    who = name or "Anonymous visitor"
    if email:
        who += f" ({email})"
    message = (
        f"Visitor: {who}\n"
        f"Page: {page or 'unknown'}\n\n"
        f"Feedback:\n{text}"
    )

    claude_bin = os.environ.get("CLAUDE_BIN", "/home/richard/.local/bin/claude")
    # Remove CLAUDECODE so nested-session detection doesn't block us
    env = os.environ.copy()
    env.pop("CLAUDECODE", None)
    result = subprocess.run(
        [claude_bin, "-p", _PROMPT],
        input=message,
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )

    if result.returncode != 0:
        raise RuntimeError(f"claude exited {result.returncode}: {result.stderr.strip()}")

    output = result.stdout.strip()
    # Strip any accidental markdown fences
    if output.startswith("```"):
        output = output.split("```")[1]
        if output.startswith("json"):
            output = output[4:]
    return json.loads(output)


# ---------------------------------------------------------------------------
# GitHub issue creation (stdlib urllib only)
# ---------------------------------------------------------------------------

def _create_github_issue(title: str, body: str, labels: list,
                         name: str, email: str) -> tuple[str | None, bool]:
    """Returns (issue_url, success)."""
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPO", "richardahasting/canyon_lake_monitor")
    if not token:
        log.error("GITHUB_TOKEN not set; cannot create GitHub issue: %s", title)
        return None, False

    full_body = body
    who = name or "Anonymous visitor"
    if email:
        who += f" <{email}>"
    full_body += f"\n\n---\n**Submitted by:** {who} (via site feedback form)"

    payload = json.dumps({"title": title, "body": full_body, "labels": labels}).encode()
    url = f"https://api.github.com/repos/{repo}/issues"
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization":        f"Bearer {token}",
            "Accept":               "application/vnd.github+json",
            "Content-Type":         "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status in (200, 201):
                data = json.loads(resp.read())
                return data.get("html_url"), True
            return None, False
    except urllib.error.HTTPError as exc:
        log.error("GitHub API HTTP %s: %s", exc.code, exc.read())
        return None, False
    except Exception as exc:
        log.error("GitHub API error: %s", exc)
        return None, False


# ---------------------------------------------------------------------------
# Email sending (local Postfix, no auth needed on same server)
# ---------------------------------------------------------------------------

def _send_email(subject: str, body: str) -> bool:
    to_addr = os.environ.get("FEEDBACK_EMAIL", "richard@hastingtx.org")
    from_addr = os.environ.get("EMAIL_FROM", "canyon-lake@hastingtx.org")
    smtp_host = os.environ.get("SMTP_HOST", "localhost")
    smtp_port = int(os.environ.get("SMTP_PORT", "25"))

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = f"Canyon Lake Monitor <{from_addr}>"
    msg["To"] = to_addr
    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as smtp:
            smtp.sendmail(from_addr, [to_addr], msg.as_string())
        return True
    except Exception as exc:
        log.error("Email send failed (%s): %s", subject, exc)
        return False


def _fallback_email(name: str, email: str, text: str, page: str) -> bool:
    """Send a plain email when the claude CLI is unavailable."""
    who = name or "Anonymous visitor"
    if email:
        who += f" ({email})"
    subject = f"Site feedback from {who}"
    body = (
        f"Feedback submitted by {who}\n"
        f"Page: {page or 'unknown'}\n\n"
        f"{text}"
    )
    return _send_email(subject, body)

#!/usr/bin/env python3
"""Daily download report for WPSniffer.

Collects PyPI download counts (pypistats.org) and GitHub release asset
download counts, keeps the "Download stats" issue body current, and posts a
comment mentioning the repository owner only when the numbers changed since
the previous comment. GitHub emails the mention, so the comment is the
notification.

Environment: GITHUB_REPOSITORY (owner/repo), GH_TOKEN (for the gh CLI).
Set DRY_RUN=1 to print the report without touching the issue.
"""
import datetime
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

PACKAGE = "wpsniffer"
LABEL = "download-stats"
TITLE = "Download stats"
MARKER = "<!-- wpsniffer-stats "
REPO = os.environ.get("GITHUB_REPOSITORY", "CommanderWaterford/wpsniffer-releases")
OWNER = REPO.split("/")[0]
DRY_RUN = os.environ.get("DRY_RUN") == "1"


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "wpsniffer-download-stats"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as err:
        if err.code == 404:
            return None
        raise


def gh(*args, body=None):
    cmd = ["gh", "api", *args]
    if body is not None:
        cmd += ["--input", "-"]
    proc = subprocess.run(cmd, input=json.dumps(body) if body is not None else None,
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"gh api {' '.join(args)} failed: {proc.stderr.strip()}")
    return json.loads(proc.stdout) if proc.stdout.strip() else None


def pypi_counts():
    recent = fetch_json(f"https://pypistats.org/api/packages/{PACKAGE}/recent")
    overall = fetch_json(f"https://pypistats.org/api/packages/{PACKAGE}/overall?mirrors=false")
    if recent is None:
        return {"available": False, "day": 0, "week": 0, "month": 0, "total": 0}
    data = recent.get("data", {})
    total = sum(row.get("downloads", 0) for row in (overall or {}).get("data", [])
                if row.get("category") == "without_mirrors")
    return {"available": True, "day": data.get("last_day", 0), "week": data.get("last_week", 0),
            "month": data.get("last_month", 0), "total": total}


def github_counts():
    releases = gh(f"/repos/{REPO}/releases?per_page=100") or []
    by_release = {}
    for rel in releases:
        by_release[rel["tag_name"]] = sum(a.get("download_count", 0) for a in rel.get("assets", []))
    return {"total": sum(by_release.values()), "by_release": by_release}


def find_issue():
    issues = gh(f"/repos/{REPO}/issues?labels={LABEL}&state=open&per_page=10") or []
    for issue in issues:
        if "pull_request" not in issue:
            return issue
    return None


def ensure_label():
    try:
        gh(f"/repos/{REPO}/labels", body={"name": LABEL, "color": "0E8A16",
                                           "description": "Automated download statistics"})
    except RuntimeError as err:
        if "already_exists" not in str(err) and "422" not in str(err):
            raise


def previous_snapshot(issue_number):
    comments = gh(f"/repos/{REPO}/issues/{issue_number}/comments?per_page=100") or []
    for comment in reversed(comments):
        body = comment.get("body", "")
        start = body.find(MARKER)
        if start == -1:
            continue
        end = body.find("-->", start)
        try:
            return json.loads(body[start + len(MARKER):end].strip())
        except ValueError:
            continue
    return None


def fmt_change(new, old):
    if old is None:
        return ""
    delta = new - old
    return f"+{delta}" if delta > 0 else (str(delta) if delta else "±0")


def build_table(snap, prev):
    p = prev or {}
    pp = p.get("pypi") or {}
    pg = p.get("github") or {}
    rows = [
        ("PyPI, last day", snap["pypi"]["day"], pp.get("day")),
        ("PyPI, last week", snap["pypi"]["week"], pp.get("week")),
        ("PyPI, last month", snap["pypi"]["month"], pp.get("month")),
        ("PyPI, all time (without mirrors)", snap["pypi"]["total"], pp.get("total")),
        ("GitHub release assets, all time", snap["github"]["total"], pg.get("total")),
    ]
    for tag, count in sorted(snap["github"]["by_release"].items(), reverse=True):
        rows.append((f"GitHub release {tag}", count, (pg.get("by_release") or {}).get(tag)))
    lines = ["| Source | Downloads | Change |", "|---|---:|---:|"]
    for label, value, old in rows:
        lines.append(f"| {label} | {value} | {fmt_change(value, old)} |")
    if not snap["pypi"]["available"]:
        lines.append("")
        lines.append("_PyPI statistics are not available yet; pypistats.org publishes them with about a one-day delay._")
    return "\n".join(lines)


def issue_body(table, today):
    return (f"Automated daily download statistics for `{PACKAGE}`, collected from "
            f"[pypistats.org](https://pypistats.org/packages/{PACKAGE}) and this repository's "
            f"release assets by the `download-stats` workflow. A comment is posted whenever the "
            f"numbers change.\n\n{table}\n\n_Last updated {today}._")


def main():
    today = datetime.date.today().isoformat()
    snap = {"date": today, "pypi": pypi_counts(), "github": github_counts()}
    print(json.dumps(snap, indent=2))

    if DRY_RUN:
        print()
        print(build_table(snap, None))
        return

    ensure_label()
    issue = find_issue()
    prev = None
    if issue is None:
        issue = gh(f"/repos/{REPO}/issues",
                   body={"title": TITLE, "body": issue_body(build_table(snap, None), today), "labels": [LABEL]})
        print("created issue", issue["html_url"])
    else:
        prev = previous_snapshot(issue["number"])

    comparable = {k: v for k, v in snap.items() if k != "date"}
    if prev is not None and {k: v for k, v in prev.items() if k != "date"} == comparable:
        print("no change since", prev.get("date"))
        return

    table = build_table(snap, prev)
    since = f" since {prev['date']}" if prev else ""
    comment = (f"@{OWNER} download counts changed{since}.\n\n{table}\n\n"
               f"{MARKER}{json.dumps(snap, separators=(',', ':'))} -->")
    gh(f"/repos/{REPO}/issues/{issue['number']}/comments", body={"body": comment})
    gh("-X", "PATCH", f"/repos/{REPO}/issues/{issue['number']}", body={"body": issue_body(table, today)})
    print("posted update to", issue["html_url"])


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # make failures visible in the Actions log
        print("error:", exc, file=sys.stderr)
        sys.exit(1)

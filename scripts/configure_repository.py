#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]

if len(sys.argv) != 2:
    raise SystemExit("Usage: configure_repository.py https://github.com/OWNER/REPO")

url = sys.argv[1].rstrip("/")
parsed = urlparse(url)
if parsed.scheme != "https" or parsed.netloc.lower() != "github.com":
    raise SystemExit("Only an https://github.com/OWNER/REPO URL is accepted.")
parts = [part for part in parsed.path.split("/") if part]
if len(parts) != 2 or not all(re.fullmatch(r"[A-Za-z0-9_.-]+", part) for part in parts):
    raise SystemExit("Repository URL must look like https://github.com/OWNER/REPO")
owner, repo = parts

badges = (
    "[![CI](https://github.com/{owner}/{repo}/actions/workflows/ci.yml/badge.svg)]({url}/actions/workflows/ci.yml) "
    "[![License: GPL-3.0-or-later](https://img.shields.io/badge/License-GPL--3.0--or--later-blue.svg)]({url}/blob/main/LICENSE) "
    "[![Release](https://img.shields.io/github/v/release/{owner}/{repo}?display_name=tag)]({url}/releases)"
).format(owner=owner, repo=repo, url=url)


def replace_region(text: str, begin: str, end: str, content: str) -> str:
    pattern = re.escape(begin) + r".*?" + re.escape(end)
    replacement = begin + "\n" + content.rstrip() + "\n" + end
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.DOTALL)
    if count != 1:
        raise SystemExit(f"Could not find marker region: {begin}")
    return updated


for name, label in (("README.md", "Projekt-Repository"), ("README.en.md", "Project repository")):
    path = ROOT / name
    text = path.read_text(encoding="utf-8")
    text = replace_region(text, "<!-- project-badges -->", "<!-- /project-badges -->", badges)
    text = replace_region(
        text,
        "<!-- project-repository -->",
        "<!-- /project-repository -->",
        f"{label}: <{url}>",
    )
    path.write_text(text, encoding="utf-8")

for name, label in (("SOFTWARE_AND_LINKS.md", "Projekt-Repository"), ("SOFTWARE_AND_LINKS.en.md", "Project repository")):
    path = ROOT / name
    text = path.read_text(encoding="utf-8")
    text = replace_region(
        text,
        "<!-- project-repository -->",
        "<!-- /project-repository -->",
        f"- {label}: {url}",
    )
    path.write_text(text, encoding="utf-8")

(ROOT / ".github" / "CODEOWNERS").write_text(f"* @{owner}\n", encoding="utf-8")
print(f"Repository metadata configured for {url}")

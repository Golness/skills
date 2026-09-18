#!/usr/bin/env python3
"""Validate the observable contract of a generated technical-solution HTML file."""

from __future__ import annotations

import re
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) not in (2, 3) or (len(sys.argv) == 3 and sys.argv[2] != "--allow-placeholders"):
        print("Usage: validate_html.py <technical-solution.html> [--allow-placeholders]")
        return 2

    path = Path(sys.argv[1])
    allow_placeholders = len(sys.argv) == 3
    if path.suffix.lower() != ".html" or not path.is_file():
        print(f"FAIL: not an existing .html file: {path}")
        return 1

    text = path.read_text(encoding="utf-8")
    checks = {
        "HTML language is zh-CN": bool(re.search(r'<html\b[^>]*\blang=["\']zh-CN["\']', text, re.I)),
        "non-empty document title": bool(re.search(r"<title>\s*[^<]+</title>", text, re.I)),
        "visible H1 title": len(re.findall(r"<h1\b", text, re.I)) == 1,
        "favicon": bool(re.search(r'<link\b[^>]*\brel=["\'][^"\']*icon[^"\']*["\']', text, re.I)),
        "overview section": bool(
            re.search(r'<section\b[^>]*(?:id|aria-label)=["\'][^"\']*(?:overview|总览|概览)[^"\']*["\']', text, re.I)
            or re.search(r'<h[2-4]\b[^>]*>[^<]*(?:方案总览|总览|概览|方案摘要)', text, re.I)
        ),
        "table of contents": 'id="toc"' in text and "文档目录" in text,
        "sticky sidebar": bool(re.search(r"\.sidebar\s*\{[^}]*position\s*:\s*sticky", text, re.I | re.S)),
        "full-width desktop layout": all(
            re.search(rf"\.{name}\s*\{{[^}}]*width\s*:\s*100%", text, re.I | re.S)
            and not re.search(rf"\.{name}\s*\{{[^}}]*max-width\s*:\s*\d", text, re.I | re.S)
            for name in ("hero", "stats", "shell", "footer")
        ),
        "automatic heading discovery": "#content h2,#content h3,#content h4" in text,
        "scroll synchronization": "syncWithScroll" in text and "classList.toggle('active'" in text,
        "independent TOC scrolling": "sidebar.scrollBy" in text,
        "syntax highlighting": "highlight.min.js" in text and "hljs.highlightAll()" in text and ".hljs-keyword" in text,
        "responsive layout": "@media(max-width:" in text.replace(" ", ""),
        "print layout": "@media print" in text,
        "no unresolved placeholders": allow_placeholders or not bool(re.search(r"\{\{[A-Z0-9_]+\}\}", text)),
    }

    failed = [label for label, ok in checks.items() if not ok]
    for label, ok in checks.items():
        print(("PASS" if ok else "FAIL") + ": " + label)
    if failed:
        print(f"\n{len(failed)} check(s) failed.")
        return 1
    print("\nAll technical-solution HTML checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

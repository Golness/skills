#!/usr/bin/env python3
"""Validate the observable contract of a generated technical-solution HTML file."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path


@dataclass(eq=False)
class Node:
    tag: str
    attrs: dict[str, str]
    parent: "Node | None" = None
    children: list["Node"] = field(default_factory=list)

    @property
    def classes(self) -> set[str]:
        return set(self.attrs.get("class", "").split())

    def descendants(self) -> list["Node"]:
        result: list[Node] = []
        for child in self.children:
            result.append(child)
            result.extend(child.descendants())
        return result


class DocumentParser(HTMLParser):
    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.root = Node("#document", {})
        self.stack = [self.root]
        self.nodes: list[Node] = []
        self.div_balance = 0
        self.div_underflow = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        node = Node(tag, {name.lower(): value or "" for name, value in attrs}, self.stack[-1])
        self.stack[-1].children.append(node)
        self.nodes.append(node)
        if tag == "div":
            self.div_balance += 1
        if tag not in self.VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag.lower() not in self.VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "div":
            self.div_balance -= 1
            self.div_underflow = self.div_underflow or self.div_balance < 0
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return


def has_ancestor(node: Node, class_name: str) -> Node | None:
    parent = node.parent
    while parent:
        if class_name in parent.classes:
            return parent
        parent = parent.parent
    return None


def css_rule_has(text: str, selector: str, declarations: list[str]) -> bool:
    match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", text, re.I | re.S)
    if not match:
        return False
    body = re.sub(r"\s+", "", match.group(1)).lower()
    return all(re.sub(r"\s+", "", declaration).lower() in body for declaration in declarations)


def mermaid_checks(text: str, parser: DocumentParser) -> dict[str, bool]:
    blocks = [node for node in parser.nodes if "mermaid" in node.classes]
    if not blocks:
        return {}

    wrappers: list[Node] = []
    nested_correctly = True
    for block in blocks:
        wrapper = has_ancestor(block, "mermaid-wrapper")
        if wrapper is None:
            nested_correctly = False
        elif wrapper not in wrappers:
            wrappers.append(wrapper)

    controls_valid = bool(wrappers)
    required_actions = {"zoom-out", "reset", "zoom-in"}
    for wrapper in wrappers:
        descendants = wrapper.descendants()
        controls = [node for node in descendants if "mermaid-controls" in node.classes]
        actions = {
            node.attrs.get("data-mermaid-action", "")
            for node in descendants
            if node.tag == "button"
        }
        controls_valid = controls_valid and bool(controls) and required_actions.issubset(actions)

    interaction_tokens = (
        "setMermaidScale",
        "resetMermaid",
        "data-mermaid-action",
        "pointerdown",
        "pointermove",
        "wheel",
        "dblclick",
    )
    return {
        "Mermaid blocks are wrapped": nested_correctly and len(wrappers) == len(blocks),
        "Mermaid controls are complete": controls_valid,
        "Mermaid div tags are balanced": parser.div_balance == 0 and not parser.div_underflow,
        "Mermaid library and progressive rendering": "mermaid.min.js" in text and "mermaid.render" in text and "dataset.mermaidSource" in text,
        "Mermaid interaction support": all(token in text for token in interaction_tokens),
        "Mermaid theme re-rendering": "renderMermaidBlocks" in text and "isDarkTheme" in text,
        "Mermaid wrapper scrolling": css_rule_has(text, ".mermaid-wrapper", ["overflow:auto"]),
        "Mermaid SVG sizing": css_rule_has(text, ".mermaid-wrapper svg", ["max-width:none", "width:auto", "min-width:fit-content"]),
    }


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
    parser = DocumentParser()
    parser.feed(text)
    checks = {
        "HTML language is zh-CN": bool(re.search(r'<html\b[^>]*\blang=["\']zh-CN["\']', text, re.I)),
        "non-empty document title": bool(re.search(r"<title>\s*[^<]+</title>", text, re.I)),
        "visible H1 title": len(re.findall(r"<h1\b", text, re.I)) == 1,
        "favicon": bool(re.search(r'<link\b[^>]*\brel=["\'][^"\']*icon[^"\']*["\']', text, re.I)),
        "overview section": bool(
            re.search(r'<section\b[^>]*(?:id|aria-label)=["\'][^"\']*(?:overview|总览|概览)[^"\']*["\']', text, re.I)
            or re.search(r'<h[2-4]\b[^>]*>[^<]*(?:方案总览|总览|概览|方案摘要)', text, re.I)
        ),
        "table of contents": bool(re.search(r'\bid=["\']toc["\']', text, re.I)) and "文档目录" in text,
        "sticky sidebar": css_rule_has(text, ".sidebar", ["position:sticky"]),
        "full-width desktop layout": all(
            css_rule_has(text, f".{name}", ["width:100%"])
            and not re.search(rf"\.{name}\s*\{{[^}}]*max-width\s*:\s*\d", text, re.I | re.S)
            for name in ("hero", "stats", "shell", "footer")
        ),
        "automatic heading discovery": "#content h2,#content h3,#content h4" in text,
        "scroll synchronization": "syncWithScroll" in text and "classList.toggle('active'" in text,
        "independent TOC scrolling": "sidebar.scrollBy" in text,
        "syntax highlighting": "highlight.min.js" in text and "hljs.highlightAll()" in text and ".hljs-keyword" in text,
        "responsive layout": "@media(max-width:" in text.replace(" ", ""),
        "print layout": "@media print" in text,
        "safe theme storage": "try{return localStorage.getItem" in text and "try{localStorage.setItem" in text,
        "no unresolved placeholders": allow_placeholders or not bool(re.search(r"\{\{[A-Z0-9_]+\}\}", text)),
    }
    checks.update(mermaid_checks(text, parser))

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

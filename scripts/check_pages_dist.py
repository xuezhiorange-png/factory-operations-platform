"""Validate frozen M0.5 GitHub Pages output; no network calls or secrets needed."""

import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

BASE = "/factory-operations-platform/"


class StaticAssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.resources: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        if tag == "script" and attr.get("src"):
            self.resources.append(attr["src"] or "")
        elif tag == "link" and attr.get("href") and attr.get("rel") in (
            "stylesheet", "modulepreload", "icon", "preload"
        ):
            self.resources.append(attr["href"] or "")


def validate(dist: Path) -> None:
    index = dist / "index.html"
    if not index.is_file():
        raise ValueError(f"Missing built index: {index}")
    html = index.read_text(encoding="utf-8")
    parser = StaticAssetParser()
    parser.feed(html)
    if "加工厂设备运维" not in html:
        raise ValueError("Unexpected site; required M0.5 title absent")
    if not parser.resources:
        raise ValueError("No script/style assets in built index")
    js_found = False
    css_found = False
    for resource in parser.resources:
        parts = urlsplit(resource)
        if parts.scheme or parts.netloc or not parts.path.startswith(BASE):
            raise ValueError(f"External or wrong-base static resource: {resource}")
        relative = Path(unquote(parts.path[len(BASE) :]))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"Unsafe static resource path: {resource}")
        target = (dist / relative).resolve()
        if not target.is_relative_to(dist.resolve()) or not target.is_file():
            raise ValueError(f"Missing static asset: {resource}")
        js_found |= target.suffix == ".js"
        css_found |= target.suffix == ".css"
    if not (js_found and css_found):
        raise ValueError("Expected built JavaScript and CSS")
    for css in dist.rglob("*.css"):
        content = css.read_text(encoding="utf-8")
        for root_url in re.findall(r"url\(\s*['\"]?(/[^)'\"]+)", content):
            if not root_url.startswith(BASE):
                raise ValueError(f"Unexpected root asset path in {css.name}: {root_url}")
    bad = [
        path for path in dist.rglob("*") if path.is_file() and (
            path.name.startswith(".env")
            or path.suffix.lower() in {".pem", ".key", ".map", ".sqlite3"}
        )
    ]
    if bad:
        raise ValueError(f"Unexpected confidential or debug files: {[str(p) for p in bad]}")
    print(f"GitHub Pages build valid: {len(parser.resources)} linked assets, base={BASE}")


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) == 2 else Path("frontend/dist")
    try:
        validate(root)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

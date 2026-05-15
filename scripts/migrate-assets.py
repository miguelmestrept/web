#!/usr/bin/env python3
"""Organize media into assets/, ASCII filenames, update HTML references."""
from __future__ import annotations

import json
import re
import shutil
import unicodedata
from pathlib import Path
from urllib.parse import quote, unquote

ROOT = Path(__file__).resolve().parent.parent
MEDIA_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".heic", ".pdf", ".m4a", ".mp3", ".mp4", ".mov", ".webm", ".wav", ".ogg"}
HTML_GLOB = "*.html"

AVATAR_FILES = {
    "sara_03.png", "jose_02.png", "samira_02.png", "pedro_02.png",
    "raul_03-2.png", "martin_02.png",
}


def strip_accents(text: str) -> str:
    nfd = unicodedata.normalize("NFD", text)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def normalize_key(name: str) -> str:
    base = unquote(name).split("?")[0]
    base = Path(base).name
    return strip_accents(unicodedata.normalize("NFC", base)).lower()


def slugify(stem: str) -> str:
    ascii_stem = strip_accents(unicodedata.normalize("NFC", stem))
    ascii_stem = ascii_stem.encode("ascii", "ignore").decode("ascii").lower()
    ascii_stem = re.sub(r"[^a-z0-9]+", "-", ascii_stem)
    ascii_stem = re.sub(r"-+", "-", ascii_stem).strip("-")
    return ascii_stem or "file"


def classify(path: Path) -> str:
    ext = path.suffix.lower()
    norm = normalize_key(path.name)
    stem = path.stem

    if ext in {".m4a", ".mp3", ".wav", ".ogg"}:
        return "assets/audio"
    if ext in {".mp4", ".mov", ".webm", ".mkv"}:
        return "assets/video"
    if ext == ".pdf":
        return "assets/documents"
    if ext == ".heic":
        return "assets/images/resources"

    if norm.startswith("captura de pantalla") or norm.startswith("captura-de-pantalla"):
        return "assets/images/screenshots"

    if norm in {normalize_key(x) for x in AVATAR_FILES} or norm.replace(" ", "") in {
        normalize_key(x) for x in AVATAR_FILES
    }:
        return "assets/images/avatars"

    stem_key = strip_accents(stem).lower().replace(" ", "")
    slide_match = re.match(r"^(martin|jose|pedro|samira)(\d+)$", stem_key)
    if slide_match:
        return f"assets/images/pdi-slides/{slide_match.group(1)}"

    if re.match(r"^\d+$", stem):
        return "assets/images/icons"

    if norm.startswith("pdi ") or norm.startswith("pdi-"):
        return "assets/images/pdi-docs"

    # Book covers and similar tall portrait assets
    bookish = (
        norm.startswith("el ")
        or norm.startswith("la ")
        or norm.startswith("un ")
        or norm.startswith("del ")
        or norm.startswith("por ")
        or norm.startswith("como ")
        or norm.startswith("salvaje")
        or norm.startswith("encanto")
        or norm.startswith("e.t.")
        or "conejo" in norm
        or "dragon" in norm
        or "caballo" in norm
        or "elefante" in norm
        or "revolucion" in norm
        or "vaca que" in norm
        or "esquinitas" in norm
        or "polo pepe" in norm
        or "punto" == norm
    )
    if bookish and ext == ".png":
        return "assets/images/books"

    site_names = {
        "portada_02", "todos_02", "circulos-nenos", "entrevistas-admiracion",
        "visitas-con-admiracion", "panel-admiramos-talentos", "practicas-restaurativas",
        "practicas restaurativas", "punto de partida (10 x 10 cm) (a4)",
    }
    if any(norm.startswith(strip_accents(s).lower()) for s in site_names):
        return "assets/images/site"

    return "assets/images/resources"


def target_filename(path: Path, folder: str) -> str:
    ext = path.suffix.lower()
    norm = normalize_key(path.name)
    stem = path.stem

    stem_key = strip_accents(stem).lower().replace(" ", "")
    slide_match = re.match(r"^(martin|jose|pedro|samira)(\d+)$", stem_key)
    if slide_match and "pdi-slides" in folder:
        student, num = slide_match.group(1), int(slide_match.group(2))
        return f"{student}-slide-{num:02d}{ext}"

    if folder.endswith("/avatars"):
        return f"{slugify(stem)}{ext}"

    if folder.endswith("/icons") and re.match(r"^\d+$", stem):
        return f"icon-{int(stem):02d}{ext}"

    return f"{slugify(stem)}{ext}"


def unique_path(folder: Path, filename: str) -> Path:
    dest = folder / filename
    if not dest.exists():
        return dest
    stem, ext = dest.stem, dest.suffix
    n = 2
    while True:
        candidate = folder / f"{stem}-{n}{ext}"
        if not candidate.exists():
            return candidate
        n += 1


def collect_variants(filename: str) -> set[str]:
    variants = set()
    for form in {filename, unicodedata.normalize("NFC", filename), unicodedata.normalize("NFD", filename)}:
        variants.add(form)
        variants.add(quote(form, safe="/"))
        variants.add(quote(form, safe="/").replace("%20", " "))
    return variants


def main() -> None:
    moves: list[dict] = []
    key_to_new: dict[str, str] = {}
    used_names: dict[str, set[str]] = {}

    media_files = sorted(
        f for f in ROOT.iterdir()
        if f.is_file() and f.suffix.lower() in MEDIA_EXTS
    )

    for src in media_files:
        folder_rel = classify(src)
        folder = ROOT / folder_rel
        folder.mkdir(parents=True, exist_ok=True)

        used_names.setdefault(folder_rel, set())
        base_name = target_filename(src, folder_rel)
        dest = unique_path(folder, base_name)
        while dest.name in used_names[folder_rel]:
            stem, ext = dest.stem, dest.suffix
            if re.search(r"-\d+$", stem):
                stem = re.sub(r"-\d+$", "", stem)
            dest = unique_path(folder, f"{stem}-dup{ext}")

        used_names[folder_rel].add(dest.name)
        new_rel = dest.relative_to(ROOT).as_posix()

        moves.append({
            "from": src.name,
            "to": new_rel,
        })

        key_to_new[normalize_key(src.name)] = new_rel
        for variant in collect_variants(src.name):
            key_to_new[normalize_key(variant)] = new_rel

    # Execute moves
    for item in moves:
        src = ROOT / item["from"]
        dest = ROOT / item["to"]
        if dest.exists():
            raise SystemExit(f"Destination already exists: {dest}")
        shutil.move(str(src), str(dest))

    # Update HTML
    html_files = sorted(ROOT.glob(HTML_GLOB))
    attr_pattern = re.compile(
        r'(?P<attr>(?:src|href|data-src))\s*=\s*["\'](?P<url>[^"\']+)["\']',
        re.IGNORECASE,
    )

    def replace_url(url: str) -> str:
        base, sep, query = url.partition("?")
        decoded = unquote(base)
        key = normalize_key(decoded)
        if key not in key_to_new:
            return url
        new_url = key_to_new[key]
        if sep:
            new_url += sep + query
        return new_url

    updated_html = []
    for html_path in html_files:
        text = html_path.read_text(encoding="utf-8")
        original = text

        def sub(match: re.Match) -> str:
            new_url = replace_url(match.group("url"))
            return f'{match.group("attr")}="{new_url}"'

        text = attr_pattern.sub(sub, text)

        # url() in inline CSS
        def sub_url(m: re.Match) -> str:
            inner = m.group(1).strip("'\"")
            new_inner = replace_url(inner)
            return f'url("{new_inner}")'

        text = re.sub(r'url\((["\']?)([^"\')\s]+)\1\)', lambda m: f'url("{replace_url(m.group(2))}")', text)

        if text != original:
            html_path.write_text(text, encoding="utf-8")
            updated_html.append(html_path.name)

    manifest = ROOT / "assets" / "manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps({"moves": moves, "updated_html": updated_html}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Moved {len(moves)} files into assets/")
    print(f"Updated {len(updated_html)} HTML files")
    print(f"Manifest: {manifest}")


if __name__ == "__main__":
    main()

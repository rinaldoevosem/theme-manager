#!/usr/bin/env python3
"""Fetch the Google Fonts catalog and generate data/google_fonts.json.

Usage:
    python scripts/fetch_google_fonts.py

Requires the GOOGLE_FONTS_API_KEY env var or pass --api-key.
Get a key at: https://developers.google.com/fonts/docs/developer_api

If no API key is available, falls back to fetching the public catalog
from the Google Fonts GitHub repo (no key needed).
"""

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

# Shopify's built-in font_picker fonts (known subset)
# These can be used with the native font_picker setting type
SHOPIFY_PICKER_SLUGS: set[str] = {
    "inter", "work_sans", "anonymous_pro", "roboto", "open_sans", "lato",
    "montserrat", "playfair_display", "raleway", "nunito", "nunito_sans",
    "poppins", "oswald", "source_sans_pro", "source_serif_pro", "source_code_pro",
    "merriweather", "merriweather_sans", "pt_sans", "pt_serif", "noto_sans",
    "noto_serif", "libre_baskerville", "libre_franklin", "dm_sans",
    "dm_serif_display", "dm_serif_text", "cormorant_garamond", "crimson_text",
    "josefin_sans", "josefin_slab", "karla", "cabin", "arimo", "bitter",
    "archivo", "archivo_narrow", "barlow", "fira_sans", "fira_code", "rubik",
    "quicksand", "manrope", "mulish", "space_grotesk", "space_mono",
    "ibm_plex_sans", "ibm_plex_serif", "ibm_plex_mono", "lexend", "outfit",
    "plus_jakarta_sans", "assistant", "bebas_neue", "anton", "lora",
    "eb_garamond", "spectral", "old_standard_tt", "vollkorn", "crimson_pro",
    "fraunces", "hind", "maven_pro", "titillium_web", "yanone_kaffeesatz",
    "ubuntu", "overpass", "chivo", "jost", "sora", "red_hat_display",
    "red_hat_text", "league_spartan", "albert_sans", "hanken_grotesk",
}

# Classification rules based on Google Fonts category + visual characteristics
CLASSIFICATION_RULES: dict[str, list[str]] = {
    # Category keywords that map to our classifications
    "geometric_sans": ["inter", "work_sans", "montserrat", "raleway", "nunito",
        "nunito_sans", "poppins", "quicksand", "jost", "outfit", "sora",
        "josefin_sans", "lexend", "albert_sans", "manrope"],
    "humanist_sans": ["open_sans", "lato", "source_sans_pro", "noto_sans",
        "fira_sans", "cabin", "pt_sans", "dm_sans", "plus_jakarta_sans",
        "karla", "merriweather_sans", "assistant", "hind", "maven_pro",
        "red_hat_text", "mulish"],
    "neo_grotesque": ["roboto", "barlow", "arimo", "ibm_plex_sans", "overpass",
        "chivo", "hanken_grotesk", "libre_franklin", "archivo", "archivo_narrow",
        "rubik", "space_grotesk", "titillium_web", "ubuntu"],
    "serif_transitional": ["merriweather", "noto_serif", "pt_serif",
        "source_serif_pro", "ibm_plex_serif", "vollkorn", "bitter"],
    "serif_old_style": ["cormorant_garamond", "eb_garamond", "crimson_text",
        "crimson_pro", "libre_baskerville", "old_standard_tt", "spectral"],
    "serif_display": ["playfair_display", "dm_serif_display", "dm_serif_text",
        "fraunces", "lora"],
    "serif_slab": ["josefin_slab"],
    "monospace": ["anonymous_pro", "source_code_pro", "fira_code",
        "ibm_plex_mono", "space_mono"],
    "display_condensed": ["oswald", "bebas_neue", "anton", "league_spartan",
        "yanone_kaffeesatz", "red_hat_display"],
}

# Reverse lookup: slug -> classification
_SLUG_TO_CLASS: dict[str, str] = {}
for cls, slugs in CLASSIFICATION_RULES.items():
    for s in slugs:
        _SLUG_TO_CLASS[s] = cls


def _slugify(family: str) -> str:
    """Convert a Google Fonts family name to a slug."""
    return re.sub(r"[^a-z0-9]+", "_", family.strip().lower()).strip("_")


def _classify(slug: str, category: str) -> str:
    """Classify a font based on its slug and Google Fonts category."""
    if slug in _SLUG_TO_CLASS:
        return _SLUG_TO_CLASS[slug]
    # Infer from Google Fonts category
    cat = category.lower().replace("-", "_")
    if cat == "sans_serif" or cat == "sans-serif":
        return "humanist_sans"
    elif cat == "serif":
        return "serif_transitional"
    elif cat == "display":
        return "display_condensed"
    elif cat == "handwriting":
        return "handwriting"
    elif cat == "monospace":
        return "monospace"
    return "uncategorized"


def _parse_variants(variants: list[str]) -> tuple[list[int], bool]:
    """Parse Google Fonts variant strings into weights list and italic flag."""
    weights = set()
    has_italic = False
    for v in variants:
        v = v.strip().lower()
        if v == "regular":
            weights.add(400)
        elif v == "italic":
            weights.add(400)
            has_italic = True
        elif v.endswith("italic"):
            num = v.replace("italic", "").strip()
            if num.isdigit():
                weights.add(int(num))
            has_italic = True
        elif v.isdigit():
            weights.add(int(v))
    return sorted(weights) or [400], has_italic


def _build_css_url(family: str, weights: list[int], has_italic: bool) -> str:
    """Build a Google Fonts CSS2 URL."""
    encoded = family.replace(" ", "+")
    weight_str = ";".join(str(w) for w in weights)
    if has_italic:
        italic_weights = ";".join(f"0,{w}" for w in weights)
        italic_weights += ";" + ";".join(f"1,{w}" for w in weights)
        return f"https://fonts.googleapis.com/css2?family={encoded}:ital,wght@{italic_weights}&display=swap"
    return f"https://fonts.googleapis.com/css2?family={encoded}:wght@{weight_str}&display=swap"


def fetch_from_api(api_key: str) -> list[dict]:
    """Fetch fonts from the Google Fonts Developer API."""
    url = f"https://www.googleapis.com/webfonts/v1/webfonts?key={api_key}&sort=popularity"
    print(f"Fetching from Google Fonts API...", file=sys.stderr)
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    return data.get("items", [])


def fetch_from_webfonts_helper() -> list[dict]:
    """Fetch from google-webfonts-helper API (free, no key, full metadata)."""
    url = "https://gwfh.mranftl.com/api/fonts"
    print("Fetching from google-webfonts-helper API...", file=sys.stderr)
    req = urllib.request.Request(url, headers={"User-Agent": "theme-designer-agent/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode())
    # Normalize to match the Google Fonts API format
    fonts = []
    for item in data:
        fonts.append({
            "family": item.get("family", ""),
            "category": item.get("category", "sans-serif"),
            "variants": item.get("variants", ["regular"]),
        })
    return fonts


def main():
    parser = argparse.ArgumentParser(description="Generate Google Fonts dataset")
    parser.add_argument("--api-key", help="Google Fonts API key")
    parser.add_argument(
        "--output",
        default=str(Path(__file__).parent.parent / "data" / "google_fonts.json"),
        help="Output file path",
    )
    args = parser.parse_args()

    import os
    api_key = args.api_key or os.getenv("GOOGLE_FONTS_API_KEY")

    if api_key:
        raw_fonts = fetch_from_api(api_key)
    else:
        print("No API key — using webfonts-helper (full metadata, no key needed)", file=sys.stderr)
        raw_fonts = fetch_from_webfonts_helper()

    if not raw_fonts:
        print("ERROR: No fonts fetched!", file=sys.stderr)
        sys.exit(1)

    fonts = {}
    for item in raw_fonts:
        family = item.get("family", "")
        if not family:
            continue
        slug = _slugify(family)
        category = item.get("category", "sans-serif")
        variants = item.get("variants", ["regular"])
        weights, has_italic = _parse_variants(variants)
        classification = _classify(slug, category)

        fonts[slug] = {
            "family": family,
            "slug": slug,
            "category": category,
            "weights": weights,
            "has_italic": has_italic,
            "classification": classification,
            "in_shopify_picker": slug in SHOPIFY_PICKER_SLUGS,
            "css_url": _build_css_url(family, weights, has_italic),
        }

    output = {
        "meta": {
            "total_fonts": len(fonts),
            "shopify_picker_count": sum(1 for f in fonts.values() if f["in_shopify_picker"]),
            "note": "Generated by scripts/fetch_google_fonts.py",
        },
        "fonts": fonts,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {len(fonts)} fonts to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()

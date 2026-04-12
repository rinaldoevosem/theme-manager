"""Custom MCP tools for the Shopify Theme Designer agent."""

import json
import re
import shutil
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool, create_sdk_mcp_server, ToolAnnotations

# ---------------------------------------------------------------------------
# Shopify font library — common Google Fonts available in Shopify themes.
# Format: family_slug -> {weights: [int], has_italic: bool}
# Identifier format: {slug}_{n|i}{weight_digit}  e.g. inter_n4, work_sans_n7
# Weight digit: 1=100, 2=200, ..., 9=900
# ---------------------------------------------------------------------------

SHOPIFY_FONTS: dict[str, dict[str, Any]] = {
    "inter": {"weights": [100, 200, 300, 400, 500, 600, 700, 800, 900], "has_italic": True},
    "work_sans": {"weights": [100, 200, 300, 400, 500, 600, 700, 800, 900], "has_italic": True},
    "anonymous_pro": {"weights": [400, 700], "has_italic": True},
    "roboto": {"weights": [100, 300, 400, 500, 700, 900], "has_italic": True},
    "open_sans": {"weights": [300, 400, 500, 600, 700, 800], "has_italic": True},
    "lato": {"weights": [100, 300, 400, 700, 900], "has_italic": True},
    "montserrat": {"weights": [100, 200, 300, 400, 500, 600, 700, 800, 900], "has_italic": True},
    "playfair_display": {"weights": [400, 500, 600, 700, 800, 900], "has_italic": True},
    "raleway": {"weights": [100, 200, 300, 400, 500, 600, 700, 800, 900], "has_italic": True},
    "nunito": {"weights": [200, 300, 400, 500, 600, 700, 800, 900], "has_italic": True},
    "nunito_sans": {"weights": [200, 300, 400, 500, 600, 700, 800, 900], "has_italic": True},
    "poppins": {"weights": [100, 200, 300, 400, 500, 600, 700, 800, 900], "has_italic": True},
    "oswald": {"weights": [200, 300, 400, 500, 600, 700], "has_italic": False},
    "source_sans_pro": {"weights": [200, 300, 400, 600, 700, 900], "has_italic": True},
    "source_serif_pro": {"weights": [200, 300, 400, 600, 700, 900], "has_italic": True},
    "source_code_pro": {"weights": [200, 300, 400, 500, 600, 700, 900], "has_italic": True},
    "merriweather": {"weights": [300, 400, 700, 900], "has_italic": True},
    "merriweather_sans": {"weights": [300, 400, 500, 600, 700, 800], "has_italic": True},
    "pt_sans": {"weights": [400, 700], "has_italic": True},
    "pt_serif": {"weights": [400, 700], "has_italic": True},
    "noto_sans": {"weights": [100, 200, 300, 400, 500, 600, 700, 800, 900], "has_italic": True},
    "noto_serif": {"weights": [100, 200, 300, 400, 500, 600, 700, 800, 900], "has_italic": True},
    "libre_baskerville": {"weights": [400, 700], "has_italic": True},
    "libre_franklin": {"weights": [100, 200, 300, 400, 500, 600, 700, 800, 900], "has_italic": True},
    "dm_sans": {"weights": [100, 200, 300, 400, 500, 600, 700, 800, 900], "has_italic": True},
    "dm_serif_display": {"weights": [400], "has_italic": True},
    "dm_serif_text": {"weights": [400], "has_italic": True},
    "cormorant_garamond": {"weights": [300, 400, 500, 600, 700], "has_italic": True},
    "crimson_text": {"weights": [400, 600, 700], "has_italic": True},
    "josefin_sans": {"weights": [100, 200, 300, 400, 500, 600, 700], "has_italic": True},
    "josefin_slab": {"weights": [100, 200, 300, 400, 500, 600, 700], "has_italic": True},
    "karla": {"weights": [200, 300, 400, 500, 600, 700, 800], "has_italic": True},
    "cabin": {"weights": [400, 500, 600, 700], "has_italic": True},
    "arimo": {"weights": [400, 500, 600, 700], "has_italic": True},
    "bitter": {"weights": [100, 200, 300, 400, 500, 600, 700, 800, 900], "has_italic": True},
    "archivo": {"weights": [100, 200, 300, 400, 500, 600, 700, 800, 900], "has_italic": True},
    "archivo_narrow": {"weights": [400, 500, 600, 700], "has_italic": True},
    "barlow": {"weights": [100, 200, 300, 400, 500, 600, 700, 800, 900], "has_italic": True},
    "fira_sans": {"weights": [100, 200, 300, 400, 500, 600, 700, 800, 900], "has_italic": True},
    "fira_code": {"weights": [300, 400, 500, 600, 700], "has_italic": False},
    "rubik": {"weights": [300, 400, 500, 600, 700, 800, 900], "has_italic": True},
    "quicksand": {"weights": [300, 400, 500, 600, 700], "has_italic": False},
    "manrope": {"weights": [200, 300, 400, 500, 600, 700, 800], "has_italic": False},
    "mulish": {"weights": [200, 300, 400, 500, 600, 700, 800, 900], "has_italic": True},
    "space_grotesk": {"weights": [300, 400, 500, 600, 700], "has_italic": False},
    "space_mono": {"weights": [400, 700], "has_italic": True},
    "ibm_plex_sans": {"weights": [100, 200, 300, 400, 500, 600, 700], "has_italic": True},
    "ibm_plex_serif": {"weights": [100, 200, 300, 400, 500, 600, 700], "has_italic": True},
    "ibm_plex_mono": {"weights": [100, 200, 300, 400, 500, 600, 700], "has_italic": True},
    "lexend": {"weights": [100, 200, 300, 400, 500, 600, 700, 800, 900], "has_italic": False},
    "outfit": {"weights": [100, 200, 300, 400, 500, 600, 700, 800, 900], "has_italic": False},
    "plus_jakarta_sans": {"weights": [200, 300, 400, 500, 600, 700, 800], "has_italic": True},
    "assistant": {"weights": [200, 300, 400, 500, 600, 700, 800], "has_italic": False},
    "bebas_neue": {"weights": [400], "has_italic": False},
    "anton": {"weights": [400], "has_italic": False},
    "lora": {"weights": [400, 500, 600, 700], "has_italic": True},
    "eb_garamond": {"weights": [400, 500, 600, 700, 800], "has_italic": True},
    "spectral": {"weights": [200, 300, 400, 500, 600, 700, 800], "has_italic": True},
    "old_standard_tt": {"weights": [400, 700], "has_italic": True},
    "vollkorn": {"weights": [400, 500, 600, 700, 800, 900], "has_italic": True},
    "crimson_pro": {"weights": [200, 300, 400, 500, 600, 700, 800, 900], "has_italic": True},
    "fraunces": {"weights": [100, 200, 300, 400, 500, 600, 700, 800, 900], "has_italic": True},
    "hind": {"weights": [300, 400, 500, 600, 700], "has_italic": False},
    "maven_pro": {"weights": [400, 500, 600, 700, 800, 900], "has_italic": False},
    "titillium_web": {"weights": [200, 300, 400, 600, 700, 900], "has_italic": True},
    "yanone_kaffeesatz": {"weights": [200, 300, 400, 500, 600, 700], "has_italic": False},
    "ubuntu": {"weights": [300, 400, 500, 700], "has_italic": True},
    "overpass": {"weights": [100, 200, 300, 400, 500, 600, 700, 800, 900], "has_italic": True},
    "chivo": {"weights": [100, 200, 300, 400, 500, 600, 700, 800, 900], "has_italic": True},
    "jost": {"weights": [100, 200, 300, 400, 500, 600, 700, 800, 900], "has_italic": True},
    "sora": {"weights": [100, 200, 300, 400, 500, 600, 700, 800], "has_italic": False},
    "red_hat_display": {"weights": [300, 400, 500, 600, 700, 800, 900], "has_italic": True},
    "red_hat_text": {"weights": [300, 400, 500, 600, 700], "has_italic": True},
    "league_spartan": {"weights": [100, 200, 300, 400, 500, 600, 700, 800, 900], "has_italic": False},
    "albert_sans": {"weights": [100, 200, 300, 400, 500, 600, 700, 800, 900], "has_italic": True},
    "hanken_grotesk": {"weights": [100, 200, 300, 400, 500, 600, 700, 800, 900], "has_italic": True},
}

# Font classification for fallback suggestions (all 76 SHOPIFY_FONTS classified)
FONT_CLASSIFICATIONS: dict[str, list[str]] = {
    "geometric_sans": ["inter", "work_sans", "montserrat", "raleway", "nunito", "nunito_sans", "poppins", "quicksand", "jost", "outfit", "sora", "josefin_sans", "lexend", "albert_sans", "manrope"],
    "humanist_sans": ["open_sans", "lato", "source_sans_pro", "noto_sans", "fira_sans", "cabin", "pt_sans", "dm_sans", "plus_jakarta_sans", "karla", "merriweather_sans", "assistant", "hind", "maven_pro", "red_hat_text", "mulish"],
    "neo_grotesque": ["roboto", "barlow", "arimo", "ibm_plex_sans", "overpass", "chivo", "hanken_grotesk", "libre_franklin", "archivo", "archivo_narrow", "rubik", "space_grotesk", "titillium_web", "ubuntu"],
    "serif_transitional": ["merriweather", "noto_serif", "pt_serif", "source_serif_pro", "ibm_plex_serif", "vollkorn", "bitter"],
    "serif_old_style": ["cormorant_garamond", "eb_garamond", "crimson_text", "crimson_pro", "libre_baskerville", "old_standard_tt", "spectral"],
    "serif_display": ["playfair_display", "dm_serif_display", "dm_serif_text", "fraunces", "lora"],
    "serif_slab": ["josefin_slab"],
    "monospace": ["anonymous_pro", "source_code_pro", "fira_code", "ibm_plex_mono", "space_mono"],
    "display_condensed": ["oswald", "bebas_neue", "anton", "league_spartan", "yanone_kaffeesatz", "red_hat_display"],
}

# Map Google Fonts categories to our classification groups for fallback
_CATEGORY_TO_CLASSIFICATION: dict[str, str] = {
    "sans-serif": "humanist_sans",
    "serif": "serif_transitional",
    "display": "display_condensed",
    "handwriting": "display_condensed",
    "monospace": "monospace",
}

# Path to the Google Fonts dataset
_GOOGLE_FONTS_PATH = Path(__file__).parent / "data" / "google_fonts.json"
_google_fonts_cache: dict | None = None


def _load_google_fonts() -> dict:
    """Load the Google Fonts dataset (cached)."""
    global _google_fonts_cache
    if _google_fonts_cache is None:
        if _GOOGLE_FONTS_PATH.exists():
            _google_fonts_cache = json.loads(
                _GOOGLE_FONTS_PATH.read_text(encoding="utf-8")
            ).get("fonts", {})
        else:
            _google_fonts_cache = {}
    return _google_fonts_cache

# Non-configurable setting types (skipped during schema parsing)
_SKIP_TYPES = {"header", "paragraph"}

# Regex to strip the /* ... */ comment block from settings_data.json
_COMMENT_RE = re.compile(r"^/\*.*?\*/\s*", re.DOTALL)

# Hex color validation
_HEX_RE = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
_RGBA_RE = re.compile(r"^rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*(,\s*[\d.]+\s*)?\)$")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _normalize_font_family(name: str) -> str:
    """Normalize a font family name to Shopify slug format."""
    return name.strip().lower().replace(" ", "_").replace("-", "_")


def _weight_to_digit(weight: int) -> int:
    """Convert CSS weight (100-900) to Shopify single digit (1-9)."""
    return max(1, min(9, weight // 100))


def _snap_weight(requested: int, available: list[int]) -> int:
    """Find the closest available weight to the requested one."""
    return min(available, key=lambda w: abs(w - requested))


def _find_font_classification(slug: str) -> str | None:
    """Find which classification a font belongs to."""
    for classification, fonts in FONT_CLASSIFICATIONS.items():
        if slug in fonts:
            return classification
    return None


def _parse_schema_settings(schema_path: Path) -> dict[str, dict[str, Any]]:
    """Parse settings_schema.json into a dict keyed by setting ID."""
    raw = schema_path.read_text(encoding="utf-8", errors="replace")
    schema = json.loads(raw)

    settings: dict[str, dict[str, Any]] = {}
    color_scheme_definition: list[dict] = []
    color_scheme_roles: dict = {}

    for group in schema:
        if not isinstance(group, dict) or "settings" not in group:
            continue

        group_name = group.get("name", "")

        for setting in group["settings"]:
            if not isinstance(setting, dict):
                continue
            stype = setting.get("type", "")
            sid = setting.get("id", "")

            if stype in _SKIP_TYPES or not sid:
                continue

            entry: dict[str, Any] = {
                "type": stype,
                "group": group_name,
                "label": setting.get("label", ""),
                "default": setting.get("default"),
            }

            if stype == "select" or stype == "radio":
                entry["valid_options"] = [
                    {"value": opt.get("value", ""), "label": opt.get("label", "")}
                    for opt in setting.get("options", [])
                    if isinstance(opt, dict)
                ]

            elif stype == "range":
                entry["min"] = setting.get("min")
                entry["max"] = setting.get("max")
                entry["step"] = setting.get("step", 1)
                entry["unit"] = setting.get("unit", "")

            elif stype == "color_scheme_group":
                color_scheme_definition = setting.get("definition", [])
                color_scheme_roles = setting.get("role", {})

            settings[sid] = entry

    return {
        "_settings": settings,
        "_color_scheme_definition": color_scheme_definition,
        "_color_scheme_roles": color_scheme_roles,
    }


def _read_settings_data(data_path: Path) -> tuple[str, dict]:
    """Read settings_data.json, returning the comment header and parsed data."""
    raw = data_path.read_text(encoding="utf-8", errors="replace")

    # Extract and preserve the comment header
    comment_header = ""
    match = _COMMENT_RE.match(raw)
    if match:
        comment_header = match.group(0)
        raw = raw[match.end():]

    data = json.loads(raw)
    return comment_header, data


def _validate_color(value: str) -> bool:
    """Check if a value is a valid CSS color (hex or rgba)."""
    if isinstance(value, str):
        return bool(_HEX_RE.match(value) or _RGBA_RE.match(value))
    return False


def _validate_single_setting(
    setting_id: str,
    proposed_value: Any,
    schema_settings: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Validate a single proposed value against its schema definition."""
    if setting_id not in schema_settings:
        return {
            "valid": False,
            "proposed_value": proposed_value,
            "corrected_value": None,
            "reason": f"Setting '{setting_id}' does not exist in schema",
        }

    defn = schema_settings[setting_id]
    stype = defn["type"]

    if stype in ("select", "radio"):
        valid_values = [opt["value"] for opt in defn.get("valid_options", [])]
        if str(proposed_value) in valid_values:
            return {"valid": True, "proposed_value": proposed_value, "corrected_value": None, "reason": None}

        # Try numeric snapping for size selects
        try:
            proposed_num = float(proposed_value)
            numeric_opts = []
            for v in valid_values:
                try:
                    numeric_opts.append((float(v), v))
                except (ValueError, TypeError):
                    pass
            if numeric_opts:
                closest = min(numeric_opts, key=lambda x: abs(x[0] - proposed_num))
                return {
                    "valid": False,
                    "proposed_value": proposed_value,
                    "corrected_value": closest[1],
                    "reason": f"Snapped {proposed_value} to closest valid option: {closest[1]}",
                }
        except (ValueError, TypeError):
            pass

        return {
            "valid": False,
            "proposed_value": proposed_value,
            "corrected_value": None,
            "reason": f"'{proposed_value}' not in valid options: {valid_values}",
        }

    elif stype == "range":
        try:
            val = float(proposed_value) if not isinstance(proposed_value, (int, float)) else proposed_value
        except (ValueError, TypeError):
            return {
                "valid": False,
                "proposed_value": proposed_value,
                "corrected_value": defn.get("default"),
                "reason": f"Cannot convert '{proposed_value}' to number",
            }

        min_val = defn.get("min", 0)
        max_val = defn.get("max", 100)
        step = defn.get("step", 1)

        clamped = max(min_val, min(max_val, val))
        steps_from_min = round((clamped - min_val) / step)
        snapped = min_val + steps_from_min * step
        snapped = min(snapped, max_val)

        # Preserve int type if step is int
        if isinstance(step, int) and isinstance(min_val, int):
            snapped = int(snapped)

        if snapped == proposed_value:
            return {"valid": True, "proposed_value": proposed_value, "corrected_value": None, "reason": None}
        return {
            "valid": False,
            "proposed_value": proposed_value,
            "corrected_value": snapped,
            "reason": f"Snapped {proposed_value} to {snapped} (range: {min_val}-{max_val}, step: {step})",
        }

    elif stype == "font_picker":
        if isinstance(proposed_value, str) and re.match(r"^[a-z0-9_]+_[ni]\d$", proposed_value):
            return {"valid": True, "proposed_value": proposed_value, "corrected_value": None, "reason": None}
        return {
            "valid": False,
            "proposed_value": proposed_value,
            "corrected_value": None,
            "reason": f"Invalid font identifier format: '{proposed_value}'. Expected format: family_slug_n4",
        }

    elif stype == "checkbox":
        if isinstance(proposed_value, bool):
            return {"valid": True, "proposed_value": proposed_value, "corrected_value": None, "reason": None}
        return {
            "valid": False,
            "proposed_value": proposed_value,
            "corrected_value": bool(proposed_value),
            "reason": f"Converted '{proposed_value}' to boolean",
        }

    elif stype in ("color", "color_background"):
        if _validate_color(str(proposed_value)):
            return {"valid": True, "proposed_value": proposed_value, "corrected_value": None, "reason": None}
        return {
            "valid": False,
            "proposed_value": proposed_value,
            "corrected_value": None,
            "reason": f"Invalid color format: '{proposed_value}'. Expected hex (#RRGGBB) or rgba()",
        }

    elif stype == "color_scheme":
        if isinstance(proposed_value, str) and proposed_value.startswith("scheme-"):
            return {"valid": True, "proposed_value": proposed_value, "corrected_value": None, "reason": None}
        return {
            "valid": False,
            "proposed_value": proposed_value,
            "corrected_value": None,
            "reason": f"Invalid color scheme ID: '{proposed_value}'. Expected format: scheme-N",
        }

    # For types we don't specifically validate (text, image_picker, etc.), accept as-is
    return {"valid": True, "proposed_value": proposed_value, "corrected_value": None, "reason": None}


# ---------------------------------------------------------------------------
# MCP Tool 1: parse_settings_schema
# ---------------------------------------------------------------------------

@tool(
    name="parse_settings_schema",
    description=(
        "Parse a Shopify theme's settings_schema.json and settings_data.json "
        "to return a complete map of all configurable settings: their types, "
        "valid options, constraints, defaults, and current values. Also returns "
        "the color scheme definition and current scheme values. "
        "Provide the full path to the theme repo directory."
    ),
    input_schema={"theme_dir": str},
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def parse_settings_schema(args: dict[str, Any]) -> dict[str, Any]:
    theme_dir = Path(args.get("theme_dir", ""))

    schema_path = theme_dir / "config" / "settings_schema.json"
    data_path = theme_dir / "config" / "settings_data.json"

    if not schema_path.exists():
        return {"content": [{"type": "text", "text": f"Schema not found: {schema_path}"}], "isError": True}
    if not data_path.exists():
        return {"content": [{"type": "text", "text": f"Settings data not found: {data_path}"}], "isError": True}

    parsed = _parse_schema_settings(schema_path)
    settings = parsed["_settings"]
    color_def = parsed["_color_scheme_definition"]
    color_roles = parsed["_color_scheme_roles"]

    _, data = _read_settings_data(data_path)
    current = data.get("current", {})

    # Merge current values into settings map
    for sid, entry in settings.items():
        entry["current_value"] = current.get(sid)

    # Extract current color schemes
    current_schemes = current.get("color_schemes", {})

    output = {
        "theme_dir": str(theme_dir),
        "total_settings": len(settings),
        "settings": settings,
        "color_scheme_definition": color_def,
        "color_scheme_roles": color_roles,
        "current_color_schemes": {
            scheme_id: scheme.get("settings", {})
            for scheme_id, scheme in current_schemes.items()
            if isinstance(scheme, dict)
        },
        "color_scheme_ids": list(current_schemes.keys()),
    }

    return {"content": [{"type": "text", "text": json.dumps(output, indent=2)}]}


# ---------------------------------------------------------------------------
# MCP Tool 2: get_shopify_fonts
# ---------------------------------------------------------------------------

@tool(
    name="get_shopify_fonts",
    description=(
        "Search the Shopify font library for a font family by name and return "
        "the matching Shopify font identifier. Maps a Figma font family name "
        "(e.g., 'Inter', 'Work Sans') and weight to a valid Shopify identifier "
        "(e.g., 'inter_n4', 'work_sans_n7'). If the font is not in Shopify's "
        "library, suggests alternatives from the same visual classification."
    ),
    input_schema={"font_family": str, "weight": int, "italic": bool},
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def get_shopify_fonts(args: dict[str, Any]) -> dict[str, Any]:
    family = args.get("font_family", "")
    weight = args.get("weight", 400)
    italic = args.get("italic", False)

    slug = _normalize_font_family(family)
    style = "i" if italic else "n"

    result: dict[str, Any] = {
        "requested": {"family": family, "weight": weight, "italic": italic},
    }

    # Direct lookup
    font_data = SHOPIFY_FONTS.get(slug)

    if font_data:
        # Check italic support
        if italic and not font_data["has_italic"]:
            style = "n"
            result["italic_note"] = f"{family} does not have italic variants in Shopify; using normal"

        # Snap weight
        available = font_data["weights"]
        snapped = _snap_weight(weight, available)
        digit = _weight_to_digit(snapped)

        identifier = f"{slug}_{style}{digit}"
        result["found"] = True
        result["identifier"] = identifier
        result["family_slug"] = slug
        result["actual_weight"] = snapped
        result["style"] = style
        result["all_available_weights"] = available
        if snapped != weight:
            result["weight_note"] = f"Requested {weight}, snapped to closest available: {snapped}"
    else:
        # Fuzzy match: try prefix matching
        candidates = [s for s in SHOPIFY_FONTS if s.startswith(slug[:4])]

        # Also try common name variations
        variations = [
            slug,
            slug.replace("_", ""),
            slug + "_sans",
            slug.replace("_sans", ""),
            slug.replace("_pro", ""),
        ]
        for var in variations:
            if var in SHOPIFY_FONTS and var not in candidates:
                candidates.append(var)

        result["found"] = False
        result["identifier"] = None
        result["reason"] = f"Font '{family}' (slug: {slug}) not found in Shopify font library"

        # Suggest alternatives from same classification
        classification = _find_font_classification(slug)
        alternatives = []

        if classification:
            for alt_slug in FONT_CLASSIFICATIONS[classification]:
                if alt_slug in SHOPIFY_FONTS:
                    alt_data = SHOPIFY_FONTS[alt_slug]
                    alt_weight = _snap_weight(weight, alt_data["weights"])
                    alt_style = style if (style == "n" or alt_data["has_italic"]) else "n"
                    alt_digit = _weight_to_digit(alt_weight)
                    alternatives.append({
                        "identifier": f"{alt_slug}_{alt_style}{alt_digit}",
                        "family": alt_slug.replace("_", " ").title(),
                        "classification": classification,
                    })
        else:
            # Fallback: suggest popular geometric sans fonts
            for alt_slug in ["inter", "work_sans", "dm_sans", "nunito_sans"]:
                alt_data = SHOPIFY_FONTS[alt_slug]
                alt_weight = _snap_weight(weight, alt_data["weights"])
                alt_digit = _weight_to_digit(alt_weight)
                alternatives.append({
                    "identifier": f"{alt_slug}_{style}{alt_digit}",
                    "family": alt_slug.replace("_", " ").title(),
                    "classification": "geometric_sans (default fallback)",
                })

        result["alternatives"] = alternatives[:5]
        if candidates:
            result["fuzzy_matches"] = candidates[:3]

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


# ---------------------------------------------------------------------------
# MCP Tool 2b: resolve_font (multi-source, replaces get_shopify_fonts)
# ---------------------------------------------------------------------------

def _best_shopify_fallback(classification: str, category: str, weight: int, italic: bool) -> dict | None:
    """Find the best Shopify picker font for a given classification/category."""
    style = "i" if italic else "n"

    # First: try fonts in the same classification that are in the Shopify picker
    class_fonts = FONT_CLASSIFICATIONS.get(classification, [])
    for slug in class_fonts:
        if slug in SHOPIFY_FONTS:
            font_data = SHOPIFY_FONTS[slug]
            snapped = _snap_weight(weight, font_data["weights"])
            if italic and not font_data["has_italic"]:
                actual_style = "n"
            else:
                actual_style = style
            digit = _weight_to_digit(snapped)
            return {
                "identifier": f"{slug}_{actual_style}{digit}",
                "family": slug.replace("_", " ").title(),
                "slug": slug,
                "classification": classification,
                "weight": snapped,
            }

    # Second: try the default classification for the Google Fonts category
    fallback_class = _CATEGORY_TO_CLASSIFICATION.get(category, "humanist_sans")
    for slug in FONT_CLASSIFICATIONS.get(fallback_class, []):
        if slug in SHOPIFY_FONTS:
            font_data = SHOPIFY_FONTS[slug]
            snapped = _snap_weight(weight, font_data["weights"])
            digit = _weight_to_digit(snapped)
            return {
                "identifier": f"{slug}_n{digit}",
                "family": slug.replace("_", " ").title(),
                "slug": slug,
                "classification": fallback_class,
                "weight": snapped,
            }

    # Last resort: inter
    return {
        "identifier": f"inter_n{_weight_to_digit(weight)}",
        "family": "Inter",
        "slug": "inter",
        "classification": "geometric_sans",
        "weight": _snap_weight(weight, SHOPIFY_FONTS["inter"]["weights"]),
    }


@tool(
    name="resolve_font",
    description=(
        "Resolve a font family against multiple sources: Shopify's built-in "
        "font picker library, Google Fonts catalog (~1900 fonts), or fallback "
        "to the best visual match. Returns the resolution strategy, a Shopify "
        "font_picker identifier (always, even for external fonts as a fallback), "
        "and external loading instructions if needed.\n\n"
        "Use this tool instead of get_shopify_fonts for comprehensive font resolution."
    ),
    input_schema={
        "font_family": str,
        "weight": int,
        "italic": bool,
        "role": str,
    },
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def resolve_font(args: dict[str, Any]) -> dict[str, Any]:
    family = args.get("font_family", "")
    weight = args.get("weight", 400)
    italic = args.get("italic", False)
    role = args.get("role", "body")

    slug = _normalize_font_family(family)
    style = "i" if italic else "n"

    result: dict[str, Any] = {
        "requested": {"family": family, "weight": weight, "italic": italic, "role": role},
    }

    # --- Strategy 1: Shopify picker exact match ---
    if slug in SHOPIFY_FONTS:
        font_data = SHOPIFY_FONTS[slug]
        if italic and not font_data["has_italic"]:
            actual_style = "n"
            result["italic_note"] = f"{family} has no italic in Shopify; using normal"
        else:
            actual_style = style
        snapped = _snap_weight(weight, font_data["weights"])
        digit = _weight_to_digit(snapped)
        identifier = f"{slug}_{actual_style}{digit}"
        classification = _find_font_classification(slug) or "uncategorized"

        result["resolution"] = {
            "strategy": "shopify_picker",
            "shopify_identifier": identifier,
            "css_family_name": font_data.get("family", family),
            "weight": snapped,
            "style": actual_style,
            "classification": classification,
            "external_load": None,
        }
        if snapped != weight:
            result["weight_note"] = f"Snapped {weight} to closest: {snapped}"
        result["fallback_alternatives"] = []
        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}

    # --- Strategy 2: Google Fonts (not in Shopify picker) ---
    google_fonts = _load_google_fonts()
    gf_entry = google_fonts.get(slug)

    if gf_entry and gf_entry.get("css_url"):
        gf_weights = gf_entry.get("weights", [400])
        gf_has_italic = gf_entry.get("has_italic", False)
        snapped = _snap_weight(weight, gf_weights) if gf_weights else weight
        classification = gf_entry.get("classification", "uncategorized")
        category = gf_entry.get("category", "sans-serif")

        # Find the best Shopify picker fallback
        fallback = _best_shopify_fallback(classification, category, weight, italic)

        result["resolution"] = {
            "strategy": "google_fonts_external",
            "shopify_identifier": fallback["identifier"] if fallback else f"inter_n{_weight_to_digit(weight)}",
            "css_family_name": gf_entry["family"],
            "weight": snapped,
            "style": "italic" if (italic and gf_has_italic) else "normal",
            "classification": classification,
            "external_load": {
                "type": "google_fonts",
                "css_url": gf_entry["css_url"],
                "family_name": gf_entry["family"],
                "weights": gf_weights,
                "has_italic": gf_has_italic,
            },
        }
        result["shopify_fallback"] = fallback
        result["fallback_alternatives"] = []
        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}

    # --- Strategy 3: Classification-aware fallback ---
    # Font not in Shopify picker OR Google Fonts. Use classification to find best match.
    # Try to infer classification from the font name
    inferred_class = None
    # Check if the name contains hints
    name_lower = family.lower()
    if any(kw in name_lower for kw in ["mono", "code"]):
        inferred_class = "monospace"
    elif any(kw in name_lower for kw in ["slab"]):
        inferred_class = "serif_slab"
    elif any(kw in name_lower for kw in ["serif", "garamond", "baskerville", "caslon", "bodoni", "didot", "times"]):
        inferred_class = "serif_display"
    elif any(kw in name_lower for kw in ["display", "poster", "headline"]):
        inferred_class = "display_condensed"
    elif any(kw in name_lower for kw in ["condensed", "narrow", "compressed"]):
        inferred_class = "display_condensed"
    elif any(kw in name_lower for kw in ["sans", "grotesk", "gothic"]):
        inferred_class = "neo_grotesque"

    # If no hint from name, infer from role
    if not inferred_class:
        role_class_map = {
            "heading": "serif_display",
            "accent": "serif_display",
            "body": "humanist_sans",
            "subheading": "humanist_sans",
        }
        inferred_class = role_class_map.get(role, "humanist_sans")

    fallback = _best_shopify_fallback(inferred_class, "sans-serif", weight, italic)

    # Build alternatives from the inferred classification
    alternatives = []
    for alt_slug in FONT_CLASSIFICATIONS.get(inferred_class, []):
        if alt_slug in SHOPIFY_FONTS and alt_slug != (fallback or {}).get("slug"):
            alt_data = SHOPIFY_FONTS[alt_slug]
            alt_weight = _snap_weight(weight, alt_data["weights"])
            alt_digit = _weight_to_digit(alt_weight)
            alt_style = style if (style == "n" or alt_data["has_italic"]) else "n"
            alternatives.append({
                "identifier": f"{alt_slug}_{alt_style}{alt_digit}",
                "family": alt_slug.replace("_", " ").title(),
                "classification": inferred_class,
            })
            if len(alternatives) >= 4:
                break

    result["resolution"] = {
        "strategy": "fallback",
        "shopify_identifier": fallback["identifier"] if fallback else f"inter_n{_weight_to_digit(weight)}",
        "css_family_name": fallback["family"] if fallback else "Inter",
        "weight": fallback["weight"] if fallback else weight,
        "style": "normal",
        "classification": inferred_class,
        "external_load": None,
    }
    result["fallback_reason"] = (
        f"'{family}' not found in Shopify picker or Google Fonts catalog. "
        f"Inferred classification: {inferred_class}. "
        f"Best Shopify fallback: {fallback['family'] if fallback else 'Inter'}"
    )
    result["shopify_fallback"] = fallback
    result["fallback_alternatives"] = alternatives

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


# ---------------------------------------------------------------------------
# MCP Tool 3: validate_setting_value
# ---------------------------------------------------------------------------

@tool(
    name="validate_setting_value",
    description=(
        "Validate a proposed value for a specific theme setting against the "
        "schema constraints. Returns whether the value is valid, and if not, "
        "suggests the closest valid value. Provide the theme directory, "
        "setting ID, and proposed value."
    ),
    input_schema={"theme_dir": str, "setting_id": str, "proposed_value": Any},
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def validate_setting_value(args: dict[str, Any]) -> dict[str, Any]:
    theme_dir = Path(args.get("theme_dir", ""))
    setting_id = args.get("setting_id", "")
    proposed_value = args.get("proposed_value")

    schema_path = theme_dir / "config" / "settings_schema.json"
    if not schema_path.exists():
        return {"content": [{"type": "text", "text": f"Schema not found: {schema_path}"}], "isError": True}

    parsed = _parse_schema_settings(schema_path)
    settings = parsed["_settings"]

    result = _validate_single_setting(setting_id, proposed_value, settings)
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


# ---------------------------------------------------------------------------
# MCP Tool 4: apply_design_tokens
# ---------------------------------------------------------------------------

@tool(
    name="apply_design_tokens",
    description=(
        "Apply a batch of design token changes to settings_data.json. Each "
        "change is validated against the schema before being applied. Creates "
        "a backup of settings_data.json before writing. Returns a detailed "
        "report of all changes made, rejected, and unchanged settings.\n\n"
        "Parameters:\n"
        "- theme_dir: Full path to the theme repo directory\n"
        "- changes: List of {setting_id, new_value, design_token, reason}\n"
        "- color_scheme_changes: Dict of {scheme_id: {color_id: hex_value}}"
    ),
    input_schema={
        "theme_dir": str,
        "changes": list,
        "color_scheme_changes": dict,
    },
    annotations=ToolAnnotations(readOnlyHint=False),
)
async def apply_design_tokens(args: dict[str, Any]) -> dict[str, Any]:
    theme_dir = Path(args.get("theme_dir", ""))
    changes = args.get("changes", [])
    color_scheme_changes = args.get("color_scheme_changes", {})

    schema_path = theme_dir / "config" / "settings_schema.json"
    data_path = theme_dir / "config" / "settings_data.json"

    if not schema_path.exists():
        return {"content": [{"type": "text", "text": f"Schema not found: {schema_path}"}], "isError": True}
    if not data_path.exists():
        return {"content": [{"type": "text", "text": f"Settings data not found: {data_path}"}], "isError": True}

    # Parse schema
    parsed = _parse_schema_settings(schema_path)
    settings = parsed["_settings"]
    color_def = parsed["_color_scheme_definition"]
    valid_color_ids = {c.get("id") for c in color_def if isinstance(c, dict) and c.get("type") != "header"}

    # Read current settings data
    comment_header, data = _read_settings_data(data_path)
    current = data.get("current", {})

    # Create backup
    backup_path = data_path.with_suffix(".json.backup")
    shutil.copy2(data_path, backup_path)

    # Track results
    applied: list[dict] = []
    snapped: list[dict] = []
    rejected: list[dict] = []
    color_applied: list[dict] = []
    color_rejected: list[dict] = []

    # Process setting changes
    for change in changes:
        if not isinstance(change, dict):
            continue

        sid = change.get("setting_id", "")
        new_value = change.get("new_value")
        design_token = change.get("design_token", "")
        reason = change.get("reason", "")

        old_value = current.get(sid)
        validation = _validate_single_setting(sid, new_value, settings)

        if validation["valid"]:
            current[sid] = new_value
            applied.append({
                "setting_id": sid,
                "group": settings.get(sid, {}).get("group", ""),
                "old_value": old_value,
                "new_value": new_value,
                "design_token": design_token,
                "status": "applied",
            })
        elif validation.get("corrected_value") is not None:
            corrected = validation["corrected_value"]
            current[sid] = corrected
            snapped.append({
                "setting_id": sid,
                "group": settings.get(sid, {}).get("group", ""),
                "old_value": old_value,
                "new_value": corrected,
                "design_token": design_token,
                "status": "snapped",
                "note": validation.get("reason", ""),
            })
        else:
            rejected.append({
                "setting_id": sid,
                "proposed_value": new_value,
                "design_token": design_token,
                "reason": validation.get("reason", "Unknown validation failure"),
            })

    # Process color scheme changes
    current_schemes = current.get("color_schemes", {})

    for scheme_id, color_changes in color_scheme_changes.items():
        if not isinstance(color_changes, dict):
            continue

        if scheme_id not in current_schemes:
            color_rejected.append({
                "scheme": scheme_id,
                "reason": f"Scheme '{scheme_id}' does not exist. Available: {list(current_schemes.keys())}",
            })
            continue

        scheme_settings = current_schemes[scheme_id].get("settings", {})

        for color_id, hex_value in color_changes.items():
            if color_id not in valid_color_ids and color_id not in scheme_settings:
                color_rejected.append({
                    "scheme": scheme_id,
                    "color_id": color_id,
                    "proposed_value": hex_value,
                    "reason": f"Color ID '{color_id}' not in scheme definition",
                })
                continue

            if not _validate_color(str(hex_value)):
                color_rejected.append({
                    "scheme": scheme_id,
                    "color_id": color_id,
                    "proposed_value": hex_value,
                    "reason": f"Invalid color format: '{hex_value}'",
                })
                continue

            old_color = scheme_settings.get(color_id)
            scheme_settings[color_id] = hex_value
            color_applied.append({
                "scheme": scheme_id,
                "color_id": color_id,
                "old_value": old_color,
                "new_value": hex_value,
            })

    # Write back
    data["current"] = current
    json_output = json.dumps(data, indent=2, ensure_ascii=False)
    output_text = comment_header + json_output + "\n"
    data_path.write_text(output_text, encoding="utf-8")

    # Build report
    updated_schemes = list({c["scheme"] for c in color_applied})

    report = {
        "summary": {
            "total_settings_in_schema": len(settings),
            "settings_updated": len(applied),
            "settings_snapped": len(snapped),
            "settings_rejected": len(rejected),
            "color_changes_applied": len(color_applied),
            "color_changes_rejected": len(color_rejected),
            "color_schemes_updated": updated_schemes,
            "backup_created": str(backup_path),
        },
        "changes": applied + snapped,
        "color_changes": color_applied,
        "rejected_changes": rejected,
        "rejected_color_changes": color_rejected,
    }

    return {"content": [{"type": "text", "text": json.dumps(report, indent=2)}]}


# ---------------------------------------------------------------------------
# MCP Tool 5: inject_external_fonts
# ---------------------------------------------------------------------------

_CUSTOM_FONTS_HEADER = """\
{%- comment -%}
  Custom fonts loaded by the Theme Designer agent.
  Fonts not available in Shopify's built-in font picker are loaded
  from external sources (Google Fonts, Adobe Fonts).
  Do not remove — sections reference these fonts via CSS variables.
{%- endcomment -%}
"""

_CUSTOM_OVERRIDES_HEADER = """\
{%- comment -%}
  CSS custom property overrides for external fonts.
  Generated by the Theme Designer agent. Rendered AFTER
  theme-styles-variables.liquid to override Shopify's defaults.
{%- endcomment -%}
"""

_FONT_ROLE_TO_CSS_VAR: dict[str, str] = {
    "heading": "--font-heading--family",
    "body": "--font-body--family",
    "subheading": "--font-subheading--family",
    "accent": "--font-accent--family",
}

_CATEGORY_TO_GENERIC: dict[str, str] = {
    "sans-serif": "sans-serif",
    "serif": "serif",
    "monospace": "monospace",
    "display": "sans-serif",
    "handwriting": "cursive",
}


def _inject_render_tag(file_path: Path, tag_name: str, before: str | None = None, after: str | None = None) -> bool:
    """Inject a {%- render 'tag_name' -%} line into a Liquid file if not already present."""
    content = file_path.read_text(encoding="utf-8", errors="replace")
    render_line = f"{{% render '{tag_name}' %}}"
    render_line_dash = f"{{%- render '{tag_name}' -%}}"

    if tag_name in content:
        return False  # Already present

    if before:
        # Insert BEFORE the target line
        idx = content.find(before)
        if idx >= 0:
            content = content[:idx] + f"    {{%- render '{tag_name}' -%}}\n    " + content[idx:]
            file_path.write_text(content, encoding="utf-8")
            return True

    if after:
        # Insert AFTER the target line
        idx = content.find(after)
        if idx >= 0:
            end_of_line = content.find("\n", idx)
            if end_of_line >= 0:
                content = content[:end_of_line + 1] + f"    {{%- render '{tag_name}' -%}}\n" + content[end_of_line + 1:]
                file_path.write_text(content, encoding="utf-8")
                return True

    return False


@tool(
    name="inject_external_fonts",
    description=(
        "Create Liquid snippets to load external fonts (Google Fonts) and "
        "override CSS custom properties. Also injects render tags into layout "
        "files at the correct positions.\n\n"
        "Creates: snippets/custom-fonts.liquid (font loading) and "
        "snippets/custom-fonts-overrides.liquid (CSS variable overrides).\n\n"
        "Modifies: layout/theme.liquid, layout/password.liquid to include "
        "the new snippets at the correct positions in the font loading pipeline."
    ),
    input_schema={
        "theme_dir": str,
        "external_fonts": list,
    },
    annotations=ToolAnnotations(readOnlyHint=False),
)
async def inject_external_fonts(args: dict[str, Any]) -> dict[str, Any]:
    theme_dir = Path(args.get("theme_dir", ""))
    external_fonts = args.get("external_fonts", [])

    if not theme_dir.is_dir():
        return {"content": [{"type": "text", "text": f"Theme dir not found: {theme_dir}"}], "isError": True}
    if not external_fonts:
        return {"content": [{"type": "text", "text": "No external fonts to inject"}], "isError": True}

    snippets_dir = theme_dir / "snippets"
    layout_dir = theme_dir / "layout"

    # --- Build custom-fonts.liquid ---
    font_links = [_CUSTOM_FONTS_HEADER]
    font_links.append('<link rel="preconnect" href="https://fonts.googleapis.com">')
    font_links.append('<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>')
    font_links.append("")

    google_urls = []
    for font in external_fonts:
        source = font.get("source", "google_fonts")
        if source == "google_fonts":
            css_url = font.get("css_url", "")
            family_name = font.get("family_name", "")
            if css_url:
                font_links.append(f'{{% comment %}} {family_name} {{% endcomment %}}')
                font_links.append(f'<link rel="stylesheet" href="{css_url}" media="print" onload="this.media=\'all\'">')
                font_links.append(f'<noscript><link rel="stylesheet" href="{css_url}"></noscript>')
                font_links.append("")
                google_urls.append(css_url)

    custom_fonts_content = "\n".join(font_links)
    custom_fonts_path = snippets_dir / "custom-fonts.liquid"
    custom_fonts_path.write_text(custom_fonts_content, encoding="utf-8")

    # --- Build custom-fonts-overrides.liquid ---
    override_lines = [_CUSTOM_OVERRIDES_HEADER, "{% style %}", "  :root {"]

    for font in external_fonts:
        role = font.get("role", "")
        css_var = _FONT_ROLE_TO_CSS_VAR.get(role)
        if not css_var:
            continue

        family_name = font.get("family_name", font.get("css_family_name", ""))
        fallback_family = font.get("fallback_shopify_family", "")
        generic = font.get("generic_family", "sans-serif")

        # Build font stack: external font, Shopify fallback, generic
        stack_parts = [f'"{family_name}"']
        if fallback_family:
            stack_parts.append(f'"{fallback_family}"')
        stack_parts.append(generic)
        font_stack = ", ".join(stack_parts)

        override_lines.append(f"    {css_var}: {font_stack};")

    override_lines.extend(["  }", "{% endstyle %}", ""])
    overrides_content = "\n".join(override_lines)
    overrides_path = snippets_dir / "custom-fonts-overrides.liquid"
    overrides_path.write_text(overrides_content, encoding="utf-8")

    # --- Inject render tags into layout files ---
    layout_modifications = []

    for layout_file in ["theme.liquid", "password.liquid"]:
        layout_path = layout_dir / layout_file
        if not layout_path.exists():
            continue

        # custom-fonts BEFORE fonts.liquid
        injected = _inject_render_tag(
            layout_path,
            "custom-fonts",
            before="render 'fonts'",
        )
        if injected:
            layout_modifications.append(f"{layout_file}: added render 'custom-fonts' before fonts.liquid")

        # custom-fonts-overrides AFTER theme-styles-variables
        injected = _inject_render_tag(
            layout_path,
            "custom-fonts-overrides",
            after="render 'theme-styles-variables'",
        )
        if injected:
            layout_modifications.append(f"{layout_file}: added render 'custom-fonts-overrides' after theme-styles-variables")

    report = {
        "snippets_created": [
            str(custom_fonts_path),
            str(overrides_path),
        ],
        "google_fonts_loaded": [f.get("family_name", "") for f in external_fonts if f.get("source") == "google_fonts"],
        "css_overrides": [
            {"role": f.get("role", ""), "css_var": _FONT_ROLE_TO_CSS_VAR.get(f.get("role", ""), "")}
            for f in external_fonts
            if f.get("role") in _FONT_ROLE_TO_CSS_VAR
        ],
        "layout_modifications": layout_modifications,
    }

    return {"content": [{"type": "text", "text": json.dumps(report, indent=2)}]}


# ---------------------------------------------------------------------------
# Bundle all tools into an MCP server
# ---------------------------------------------------------------------------

designer_tools_server = create_sdk_mcp_server(
    name="designer-tools",
    version="1.0.0",
    tools=[
        parse_settings_schema,
        get_shopify_fonts,
        resolve_font,
        validate_setting_value,
        apply_design_tokens,
        inject_external_fonts,
    ],
)

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

# Font classification for fallback suggestions
FONT_CLASSIFICATIONS: dict[str, list[str]] = {
    "geometric_sans": ["inter", "work_sans", "montserrat", "raleway", "nunito", "poppins", "quicksand", "jost", "outfit", "sora"],
    "humanist_sans": ["open_sans", "lato", "source_sans_pro", "noto_sans", "fira_sans", "cabin", "pt_sans", "dm_sans", "plus_jakarta_sans"],
    "neo_grotesque": ["roboto", "barlow", "arimo", "ibm_plex_sans", "overpass", "chivo", "hanken_grotesk"],
    "serif_transitional": ["merriweather", "noto_serif", "pt_serif", "source_serif_pro", "ibm_plex_serif", "vollkorn"],
    "serif_old_style": ["cormorant_garamond", "eb_garamond", "crimson_text", "crimson_pro", "libre_baskerville", "old_standard_tt", "spectral"],
    "serif_display": ["playfair_display", "dm_serif_display", "fraunces", "lora"],
    "monospace": ["anonymous_pro", "source_code_pro", "fira_code", "ibm_plex_mono", "space_mono"],
    "display": ["oswald", "bebas_neue", "anton", "league_spartan", "yanone_kaffeesatz"],
}

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
# Bundle all tools into an MCP server
# ---------------------------------------------------------------------------

designer_tools_server = create_sdk_mcp_server(
    name="designer-tools",
    version="1.0.0",
    tools=[parse_settings_schema, get_shopify_fonts, validate_setting_value, apply_design_tokens],
)

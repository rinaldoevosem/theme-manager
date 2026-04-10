"""Custom MCP tools for the Shopify Theme Architect agent."""

import json
import os
import re
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool, create_sdk_mcp_server, ToolAnnotations

_SCHEMA_RE = re.compile(
    r"\{%[-\s]*schema\s*[-\s]*%\}(.*?)\{%[-\s]*endschema\s*[-\s]*%\}",
    re.DOTALL,
)

_RENDER_RE = re.compile(r"\{%-?\s*render\s+['\"]([^'\"]+)['\"]")


def _extract_schema(liquid_content: str) -> dict | None:
    """Extract and parse the {% schema %} JSON from a Liquid section file."""
    match = _SCHEMA_RE.search(liquid_content)
    if not match:
        return None
    try:
        return json.loads(match.group(1).strip())
    except (json.JSONDecodeError, ValueError):
        return None


def _extract_snippets_used(liquid_content: str) -> list[str]:
    """Extract snippet names from {% render 'name' %} calls."""
    return sorted(set(_RENDER_RE.findall(liquid_content)))


def _summarize_section(filepath: Path) -> dict[str, Any] | None:
    """Build a summary dict for a single section file."""
    content = filepath.read_text(encoding="utf-8", errors="replace")

    if filepath.suffix == ".json":
        # JSON template section (e.g., header-group.json)
        try:
            data = json.loads(content)
            return {
                "filename": filepath.name,
                "type": "json-template",
                "name": data.get("name", filepath.stem),
                "sections_referenced": list(data.get("sections", {}).keys()) if isinstance(data.get("sections"), dict) else [],
            }
        except (json.JSONDecodeError, ValueError):
            return None

    schema = _extract_schema(content)
    if schema is None:
        return None

    blocks = schema.get("blocks", [])
    block_types = [b.get("type", "unknown") for b in blocks if isinstance(b, dict)]
    settings = schema.get("settings", [])
    presets = schema.get("presets", [])

    return {
        "filename": filepath.name,
        "type": "liquid-section",
        "name": schema.get("name", filepath.stem),
        "block_types": block_types,
        "block_count": len(block_types),
        "setting_count": len(settings),
        "has_presets": len(presets) > 0,
        "preset_names": [p.get("name", "") for p in presets if isinstance(p, dict)],
        "max_blocks": schema.get("max_blocks"),
        "disabled_on": schema.get("disabled_on"),
        "tag": schema.get("tag"),
        "class": schema.get("class"),
    }


@tool(
    name="analyze_theme_architecture",
    description=(
        "Scan a Shopify theme directory and return a structured overview of its "
        "architecture: all sections with their block types and settings counts, "
        "plus lists of blocks, snippets, templates, and layout files. "
        "Provide the full path to the theme repo directory."
    ),
    input_schema={"theme_dir": str},
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def analyze_theme_architecture(args: dict[str, Any]) -> dict[str, Any]:
    theme_dir = Path(args.get("theme_dir", ""))

    if not theme_dir.is_dir():
        return {
            "content": [{"type": "text", "text": f"Directory not found: {theme_dir}"}],
            "isError": True,
        }

    sections_dir = theme_dir / "sections"
    if not sections_dir.is_dir():
        return {
            "content": [{"type": "text", "text": f"No sections/ directory found in {theme_dir}"}],
            "isError": True,
        }

    # Scan sections
    sections = []
    for f in sorted(sections_dir.iterdir()):
        if f.suffix in (".liquid", ".json"):
            summary = _summarize_section(f)
            if summary:
                sections.append(summary)

    # List other directories
    def _list_dir(name: str) -> list[str]:
        d = theme_dir / name
        if d.is_dir():
            return sorted(f.name for f in d.iterdir() if not f.name.startswith("."))
        return []

    blocks = _list_dir("blocks")
    snippets = _list_dir("snippets")
    templates = _list_dir("templates")
    layout_files = _list_dir("layout")

    # Theme info from settings_schema.json
    theme_info = {}
    settings_schema = theme_dir / "config" / "settings_schema.json"
    if settings_schema.exists():
        try:
            data = json.loads(settings_schema.read_text(encoding="utf-8", errors="replace"))
            if isinstance(data, list) and data:
                first = data[0]
                if isinstance(first, dict):
                    theme_info = {
                        "theme_name": first.get("name", ""),
                        "theme_version": first.get("theme_version", ""),
                        "theme_author": first.get("theme_author", ""),
                    }
        except (json.JSONDecodeError, ValueError):
            pass

    output = {
        "theme_dir": str(theme_dir),
        "theme_info": theme_info,
        "sections": sections,
        "section_count": len(sections),
        "blocks": blocks,
        "block_count": len(blocks),
        "snippets": snippets,
        "snippet_count": len(snippets),
        "templates": templates,
        "template_count": len(templates),
        "layout_files": layout_files,
    }

    return {
        "content": [{"type": "text", "text": json.dumps(output, indent=2)}],
    }


@tool(
    name="get_section_details",
    description=(
        "Get a detailed analysis of a specific section file: full schema, "
        "all settings with types, all block definitions, snippet dependencies, "
        "and key Liquid logic. Provide the theme directory and section filename."
    ),
    input_schema={"theme_dir": str, "section_filename": str},
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def get_section_details(args: dict[str, Any]) -> dict[str, Any]:
    theme_dir = Path(args.get("theme_dir", ""))
    filename = args.get("section_filename", "")
    section_path = theme_dir / "sections" / filename

    if not section_path.exists():
        return {
            "content": [{"type": "text", "text": f"Section file not found: {section_path}"}],
            "isError": True,
        }

    content = section_path.read_text(encoding="utf-8", errors="replace")
    lines = content.splitlines()

    # Handle JSON section files
    if section_path.suffix == ".json":
        try:
            data = json.loads(content)
            output = {
                "filename": filename,
                "type": "json-template",
                "full_content": data,
                "line_count": len(lines),
            }
            return {"content": [{"type": "text", "text": json.dumps(output, indent=2)}]}
        except (json.JSONDecodeError, ValueError):
            return {
                "content": [{"type": "text", "text": f"Failed to parse JSON: {section_path}"}],
                "isError": True,
            }

    schema = _extract_schema(content)
    snippets_used = _extract_snippets_used(content)

    # Extract key assign statements
    assign_re = re.compile(r"\{%-?\s*assign\s+(\w+)\s*=\s*(.+?)\s*-?%\}")
    assigns = [
        {"variable": m.group(1), "expression": m.group(2).strip()}
        for m in assign_re.finditer(content)
    ]

    # Extract CSS class patterns
    class_re = re.compile(r'class="([^"]*)"')
    css_classes = sorted(set(class_re.findall(content)))

    output: dict[str, Any] = {
        "filename": filename,
        "type": "liquid-section",
        "line_count": len(lines),
        "snippets_used": snippets_used,
        "key_assigns": assigns[:30],  # Limit to avoid huge output
        "css_classes": css_classes[:30],
    }

    if schema:
        settings = schema.get("settings", [])
        blocks = schema.get("blocks", [])

        output["name"] = schema.get("name", "")
        output["settings"] = [
            {
                "id": s.get("id", ""),
                "type": s.get("type", ""),
                "label": s.get("label", ""),
                "default": s.get("default"),
            }
            for s in settings
            if isinstance(s, dict) and s.get("type") != "header"
        ]
        output["blocks"] = [
            {
                "type": b.get("type", ""),
                "name": b.get("name", ""),
                "settings": [
                    {"id": s.get("id", ""), "type": s.get("type", ""), "label": s.get("label", "")}
                    for s in b.get("settings", [])
                    if isinstance(s, dict) and s.get("type") != "header"
                ],
                "limit": b.get("limit"),
            }
            for b in blocks
            if isinstance(b, dict)
        ]
        output["presets"] = schema.get("presets", [])
        output["max_blocks"] = schema.get("max_blocks")
        output["disabled_on"] = schema.get("disabled_on")
        output["tag"] = schema.get("tag")
        output["class"] = schema.get("class")
    else:
        output["schema"] = None
        output["note"] = "No {% schema %} block found in this section."

    return {"content": [{"type": "text", "text": json.dumps(output, indent=2)}]}


@tool(
    name="match_section_to_design",
    description=(
        "Score existing theme sections against design requirements and return "
        "ranked recommendations. Provide the theme directory and a requirements "
        "object with: layout_type (e.g., 'hero-banner', 'grid', 'carousel'), "
        "block_types_needed (list of block types like 'text', 'button', 'image'), "
        "settings_needed (list of setting types like 'color_scheme', 'image_picker'), "
        "interactive_elements (list like 'carousel', 'accordion', 'tabs'), "
        "and description (narrative summary of the design)."
    ),
    input_schema={
        "theme_dir": str,
        "requirements": {
            "layout_type": str,
            "block_types_needed": list,
            "settings_needed": list,
            "interactive_elements": list,
            "description": str,
        },
    },
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def match_section_to_design(args: dict[str, Any]) -> dict[str, Any]:
    theme_dir = Path(args.get("theme_dir", ""))
    reqs = args.get("requirements", {})

    sections_dir = theme_dir / "sections"
    if not sections_dir.is_dir():
        return {
            "content": [{"type": "text", "text": f"No sections/ directory found in {theme_dir}"}],
            "isError": True,
        }

    needed_blocks = set(b.lower() for b in reqs.get("block_types_needed", []))
    needed_settings = set(s.lower() for s in reqs.get("settings_needed", []))
    layout_type = reqs.get("layout_type", "").lower()
    description = reqs.get("description", "").lower()

    scored: list[dict[str, Any]] = []

    for f in sorted(sections_dir.iterdir()):
        if f.suffix != ".liquid":
            continue

        content = f.read_text(encoding="utf-8", errors="replace")
        schema = _extract_schema(content)
        if not schema:
            continue

        section_name = (schema.get("name") or f.stem).lower()
        blocks = schema.get("blocks", [])
        settings = schema.get("settings", [])
        presets = schema.get("presets", [])

        # Block type coverage (50% weight)
        section_block_types = set(
            b.get("type", "").lower() for b in blocks if isinstance(b, dict)
        )
        if needed_blocks:
            block_matches = needed_blocks & section_block_types
            block_score = len(block_matches) / len(needed_blocks)
        else:
            block_score = 0.5  # Neutral if no blocks required

        # Settings type coverage (30% weight)
        section_setting_types = set(
            s.get("type", "").lower() for s in settings if isinstance(s, dict)
        )
        section_setting_ids = set(
            s.get("id", "").lower() for s in settings if isinstance(s, dict)
        )
        all_section_settings = section_setting_types | section_setting_ids
        if needed_settings:
            settings_matches = needed_settings & all_section_settings
            settings_score = len(settings_matches) / len(needed_settings)
        else:
            settings_score = 0.5

        # Layout/name match (20% weight)
        name_score = 0.0
        search_text = f"{section_name} {' '.join(p.get('name', '').lower() for p in presets if isinstance(p, dict))}"
        css_class = (schema.get("class") or "").lower()
        search_text += f" {css_class}"

        # Check layout_type keywords against section name/presets
        if layout_type:
            layout_keywords = layout_type.replace("-", " ").replace("_", " ").split()
            matches = sum(1 for kw in layout_keywords if kw in search_text)
            name_score = matches / len(layout_keywords) if layout_keywords else 0.0

        # Also check description keywords for bonus
        if description and not layout_type:
            desc_words = description.split()[:10]  # First 10 words
            matches = sum(1 for w in desc_words if w in search_text)
            name_score = min(matches / max(len(desc_words), 1), 1.0)

        total_score = (block_score * 0.50) + (settings_score * 0.30) + (name_score * 0.20)

        # Identify gaps
        block_gaps = sorted(needed_blocks - section_block_types) if needed_blocks else []
        setting_gaps = sorted(needed_settings - all_section_settings) if needed_settings else []

        scored.append({
            "filename": f.name,
            "name": schema.get("name", f.stem),
            "score": round(total_score, 3),
            "block_match_pct": round(block_score * 100, 1),
            "settings_match_pct": round(settings_score * 100, 1),
            "layout_match_pct": round(name_score * 100, 1),
            "available_block_types": sorted(section_block_types),
            "missing_block_types": block_gaps,
            "missing_settings": setting_gaps,
            "has_presets": len(presets) > 0,
        })

    # Sort by score descending
    scored.sort(key=lambda x: x["score"], reverse=True)

    # Return top 10
    output = {
        "requirements": reqs,
        "total_sections_analyzed": len(scored),
        "top_matches": scored[:10],
    }

    return {"content": [{"type": "text", "text": json.dumps(output, indent=2)}]}


# Bundle all tools into an MCP server
architect_tools_server = create_sdk_mcp_server(
    name="architect-tools",
    version="1.0.0",
    tools=[analyze_theme_architecture, get_section_details, match_section_to_design],
)

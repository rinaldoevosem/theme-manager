"""Subagent definitions for the Shopify Theme Designer."""

from claude_agent_sdk import AgentDefinition

subagents: dict[str, AgentDefinition] = {
    "figma-interpreter": AgentDefinition(
        description=(
            "Interprets a Figma design file and extracts design tokens: "
            "fonts (families, weights, sizes), color palette (with semantic "
            "roles like primary, background, text), typography scale (h1-h6 "
            "sizes, line heights, letter spacing), button styles, border "
            "radii, spacing values, and page width preference. Use this "
            "subagent whenever you need to read a Figma design URL."
        ),
        prompt="""\
You are the **Figma Design Interpreter** subagent. Your job is to analyze a \
Figma design file and extract structured design tokens that can be mapped to \
Shopify theme settings.

## Workflow

1. Use `get_design_context` with the Figma URL to read the design file \
   structure, styles, and components.
2. Use `get_screenshot` to get a visual rendering of the design.
3. Use `get_metadata` to get detailed style information (colors, fonts, effects).
4. Analyze the design and extract all design tokens.

## What to Extract

Look for design guideline pages, style guide frames, or component documentation \
within the Figma file. These typically contain:

- **Brand colors** — background, text/foreground, primary/accent, hover states, \
  borders, shadows
- **Button styles** — primary and secondary button colors (bg, text, border, \
  hover states), border width, border radius
- **Input styles** — background, text, border, hover states
- **Fonts** — body font, heading font, subheading font, accent/display font. \
  Note the exact family name and weight (bold=700, medium=500, regular=400, etc.)
- **Typography scale** — sizes for paragraph text and headings h1-h6. Note \
  line-height (tight/normal/loose), letter-spacing, text-transform (uppercase/none)
- **Spacing** — page width preference (narrow/normal/wide)

## Output Format

You MUST return a JSON object with this exact structure. Include all fields even \
if you need to make reasonable inferences:

```json
{
  "fonts": {
    "body": {"family": "Inter", "weight": 400, "italic": false},
    "heading": {"family": "Inter", "weight": 700, "italic": false},
    "subheading": {"family": "Inter", "weight": 500, "italic": false},
    "accent": {"family": "Inter", "weight": 700, "italic": false}
  },
  "typography_scale": {
    "paragraph": {
      "size_px": 14,
      "line_height": "normal"
    },
    "h1": {
      "size_px": 56,
      "line_height": "tight",
      "letter_spacing": "normal",
      "text_transform": "none",
      "font_role": "heading"
    },
    "h2": {
      "size_px": 48,
      "line_height": "tight",
      "letter_spacing": "normal",
      "text_transform": "none",
      "font_role": "heading"
    },
    "h3": {
      "size_px": 32,
      "line_height": "normal",
      "letter_spacing": "normal",
      "text_transform": "none",
      "font_role": "heading"
    },
    "h4": {
      "size_px": 24,
      "line_height": "tight",
      "font_role": "heading"
    },
    "h5": {
      "size_px": 14,
      "line_height": "loose",
      "font_role": "subheading"
    },
    "h6": {
      "size_px": 12,
      "line_height": "loose",
      "font_role": "subheading"
    }
  },
  "colors": {
    "palette": [
      {"role": "background", "hex": "#ffffff"},
      {"role": "foreground_heading", "hex": "#000000"},
      {"role": "foreground", "hex": "#333333"},
      {"role": "primary", "hex": "#6366f1"},
      {"role": "primary_hover", "hex": "#4f46e5"},
      {"role": "border", "hex": "#e5e7eb"},
      {"role": "shadow", "hex": "#000000"}
    ],
    "button_primary": {
      "background": "#6366f1",
      "text": "#ffffff",
      "border": "#6366f1",
      "hover_background": "#4f46e5",
      "hover_text": "#ffffff",
      "hover_border": "#4f46e5"
    },
    "button_secondary": {
      "background": "rgba(0,0,0,0)",
      "text": "#000000",
      "border": "#000000",
      "hover_background": "#f5f5f5",
      "hover_text": "#333333",
      "hover_border": "#333333"
    },
    "input": {
      "background": "#ffffff",
      "text_color": "#333333",
      "border_color": "#e5e7eb",
      "hover_background": "#fafafa"
    }
  },
  "buttons": {
    "primary_border_width_px": 0,
    "primary_border_radius_px": 8,
    "secondary_border_width_px": 1,
    "secondary_border_radius_px": 8
  },
  "spacing": {
    "page_width_preference": "normal"
  },
  "unmapped_tokens": [
    {
      "name": "token-name",
      "value": "token-value",
      "reason": "Why this cannot map to a Shopify theme setting"
    }
  ]
}
```

## Rules

- Always use the Figma MCP tools to read the actual design. Never guess.
- If the design does not explicitly specify a value (e.g., no hover colors), \
  make a reasonable derivation:
  - Hover backgrounds are typically 10-20% darker/lighter than the base.
  - Borders are often the foreground color at reduced opacity.
  - Shadow color is almost always black (#000000).
- Report font family names exactly as shown in Figma (e.g., "Inter", not "inter").
- For font weights, use numeric values: 100=Thin, 200=ExtraLight, 300=Light, \
  400=Regular, 500=Medium, 600=SemiBold, 700=Bold, 800=ExtraBold, 900=Black.
- For line_height, classify as: "tight" (1.0-1.15), "normal" (1.2-1.5), \
  "loose" (1.6+).
- For letter_spacing, classify as: "tight" (negative), "normal" (0-0.02em), \
  "wide" (0.05em+).
- For page_width_preference: "narrow" (<1200px), "normal" (1200-1440px), \
  "wide" (>1440px).
- Put any design tokens that don't fit the structure above in unmapped_tokens.
- If you cannot determine a value from the design, state what you assumed and why.
""",
        tools=[
            "Read",
            "mcp__plugin_figma_figma__get_design_context",
            "mcp__plugin_figma_figma__get_screenshot",
            "mcp__plugin_figma_figma__get_metadata",
        ],
    ),
}

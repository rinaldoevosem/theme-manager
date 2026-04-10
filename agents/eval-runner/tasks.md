# Eval Runner — Tasks & Findings

## Recent Findings

### Run 2026-04-09T23-07 — First 10-case batch (Sonnet)

**Results:**
- Pass rate: **90%** (9/10)
- Avg composite: **0.794**
- Accuracy: 0.950
- Reasoning: 0.920
- Completeness: 0.795 (weakest dimension)
- Total cost: $3.67 ($0.367/task avg)
- Avg duration: 75.9s

**Suite performance:**
| Suite | Pass Rate | Avg Composite |
|-------|-----------|---------------|
| Blog | 100% (3/3) | 0.810 |
| Collection Display | 80% (4/5) | 0.795 |
| Content & Editorial | 100% (2/2) | 0.770 |

**The one failure: `collection-editorial`**
- Expected: `collection-list.liquid` or `media-with-content.liquid`
- Got: `collection-links.liquid`
- Confusion pattern: agent reaches for the minimal text-only `collection-links` when the ask is for an editorial layout with image + text. The word "editorial" in the description should have pointed to `collection-list.liquid`'s `Editorial` preset.

**Confusion pairs logged:**
- `collection-list.liquid → collection-links.liquid` (1)
- `media-with-content.liquid → collection-links.liquid` (1)

**Key observations:**
1. Architect is running on **Sonnet** (SDK default), not Opus. Cost/task of $0.367 is consistent with Sonnet pricing for 15-20 turn runs.
2. Accuracy and reasoning are very strong — the agent knows the theme well and cites schema JSON.
3. **Completeness** is the weakest dimension — the agent often doesn't explicitly mention alternatives or flag gaps.
4. **Cost scoring target of $0.15/task is too tight** — realistic Sonnet cost is ~$0.35-0.40/task. The cost dimension is dragging down composite scores despite high accuracy/reasoning.

---

## Next Actions (Priority Order)

### High
- [ ] **Run full 40-case suite** — Baseline all categories. Expected: ~2 hours, ~$14-15 at current rate.
- [ ] **Relax cost target in `scorer.py`** — Change `TARGET_COST_USD = 0.15` to `0.40` (or make it configurable via env var). Current target penalizes healthy runs.
- [ ] **Investigate collection-editorial confusion** — The agent consistently picks `collection-links.liquid` when "editorial" appears in the description. Either:
  - Add a disambiguation hint in `system_prompt.py` (e.g., "`collection-links` is text-only; for editorial layouts with images, use `collection-list.liquid` with the Editorial preset")
  - Adjust scoring weights in `theme-architect/tools.py` `match_section_to_design`

### Medium
- [ ] **A/B test Opus vs Sonnet** — Use the new `--model` flag on theme-architect. Run the same 10-case suite with `THEME_ARCHITECT_MODEL=claude-opus-4-6` and compare scores vs the Sonnet baseline. Expected cost: ~$15-20 for the Opus run.
- [ ] **Improve completeness scoring** — The current regex-based completeness check is weak. Consider LLM-as-judge mode (optional `--llm-grader` flag) for reasoning and completeness dimensions.
- [ ] **Parse stdout for in-flight progress** — Currently the subprocess buffers all output until exit. For long overnight runs, consider streaming or polling architect's `heartbeat_output.json`.

### Low / Future
- [ ] **Paperclip scheduled heartbeat** — Register eval-runner as a Paperclip agent with a nightly cron (e.g., 2 AM). Currently runs via manual `python main.py --overnight`.
- [ ] **Auto-update scoring weights** — `--auto-update` flag (dry-run by default) to adjust the `match_section_to_design` weights in `tools.py` based on failure patterns. Numeric weights only, never prompt prose.
- [ ] **Trend dashboard** — HTML report with charts comparing eval runs over time.
- [ ] **Per-section accuracy heatmap** — Show which sections the agent consistently gets right/wrong.
- [ ] **Multilingual eval cases** — descriptions in Spanish/French
- [ ] **Figma URL-based cases** — Currently text-only. Add cases that provide a real Figma URL via the Figma MCP tools.
- [ ] **Adversarial cases** — Intentionally vague or contradictory descriptions.
- [ ] **Eval theme-manager** — Add eval cases for theme-manager (PR review, sync detection).

## Done

- [x] Initial eval-runner skeleton with 40 test cases (9 YAML files)
- [x] 5-dimension scoring (accuracy, reasoning, completeness, cost, speed)
- [x] Markdown report generation with trend comparison
- [x] Failure pattern analysis with suggestions
- [x] End-to-end pipeline validated: task creation → heartbeat trigger → result collection → scoring → report
- [x] Stdout parser for cost/duration/turns extraction
- [x] Correct Paperclip API routes: `PATCH /api/issues/:id`, `POST /api/issues/:id/comments` with `body` field
- [x] Heartbeat status filter (`todo` only) to avoid disrupting user tasks
- [x] `--model` flag on theme-architect for Sonnet/Opus A/B testing
- [x] First 10-case baseline run: 90% pass, 0.794 avg (2026-04-09T23-07)

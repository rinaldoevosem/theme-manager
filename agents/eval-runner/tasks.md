# Eval Runner — Future Tasks

Track future work for the eval-runner system here.

## Backlog

### Automation
- [ ] **Paperclip scheduled heartbeat** — Register eval-runner as a Paperclip agent with a nightly cron schedule (e.g., 2 AM). Currently runs manually via `python main.py --overnight`. Once stable, switch to scheduled mode.
- [ ] **macOS launchd plist** — Alternative to Paperclip scheduling for native macOS scheduler. Survives sleep/wake.

### Evaluation improvements
- [ ] **LLM-as-judge mode** — Optional `--llm-grader` flag that uses Claude to score reasoning quality more accurately than regex matching.
- [ ] **Auto-update scoring weights** — `--auto-update` flag (gated, dry-run by default) to adjust the `match_section_to_design` weights in `tools.py` based on failure patterns. Numeric weights only, never prompt prose.
- [ ] **Trend dashboard** — HTML report with charts comparing eval runs over time.
- [ ] **Per-section accuracy heatmap** — Show which sections the agent gets right/wrong consistently.

### Test cases
- [ ] Add multilingual eval cases (descriptions in Spanish/French)
- [ ] Add Figma URL-based cases (currently text-only)
- [ ] Add adversarial cases (intentionally vague or contradictory descriptions)

### Other agents
- [ ] **Eval theme-manager** — Add eval cases for theme-manager (PR review, sync detection)
- [ ] **Eval design-interpreter subagent** — Test the subagent in isolation

## Done

- [x] Initial eval-runner skeleton with 40 test cases
- [x] 5-dimension scoring (accuracy, reasoning, completeness, cost, speed)
- [x] Markdown report generation with trend comparison
- [x] Failure pattern analysis with suggestions

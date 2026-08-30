# PathFinder — Final spatial UI review

Captured against a production stack (`next start` on :3002, API :8000, Postgres :5433). Baseline screenshots from before this pass were not available in-session; `artifacts/ui-final/after/` is the post-implementation set.

| Screen | Before | Change | After | Quality | Remaining issue |
| --- | --- | --- | --- | --- | --- |
| Onboarding | Destination command surface from prior pass | Unchanged on purpose | Same composition, Source Serif + intake card | 9 | Ambient graph is still faint; acceptable |
| Career Explorer | Role cards + compare columns | Selected card now has identity + skill signature; route preview + choose-destination line | Selected AI/ML card is distinct from siblings | 8 | Unselected cards still share one grid template |
| Dashboard | Command center, four metric cells | Destination-first label; dominant current-position; top gap beside next action; competency route | Loaded dashboard: AI/ML Engineer, 1/6, Verify docker, ML Fundamentals | 8 | Competency route is still a stacked readout, not a spatial route |
| Path | Week / resource / button rows | Vertical spine, destination nodes, week markers, waypoint states, sticky current week, Why on inspect | Desktop reads as a route; mobile is a compact vertical spine | 8 | Completed items still grow a frozen-work block; density can look like a list again below the fold |
| Path Why | Drawer with score breakdown | Same contract; forensic fields | Drawer sits on the right; path remains visible | 8 | Overlay Close vs dismiss control collision (fixed in source) |
| Assessment | Quiz-like choice cards | Question-first diagnostic: skill title, editorial prompt, hairline answers, route index | Docker Gate Q1 looks like a diagnostic, not a card quiz | 8 | Judge rail is tall on 390px and competes with the question |
| Result | Chain existed in source | Metric-first BEFORE → evidence → AFTER | **Not captured** — submit never reached `result-hero` in this QA loop | — | Browser QA incomplete |
| V1 → V2 | FLIP + cascade already present | Route waypoints, locked FLIP on frozen work, causality line | **Not captured** | — | Browser QA incomplete |
| Why Changed | Three sections | Denser forensic grid (evidence / before / after / action) | **Not captured** | — | Browser QA incomplete |
| Timeline | Version list | Archive spine + selected inspect (What changed / Why) | V1 ACTIVE with inspect panel | 8 | Only V1 existed on the judge-demo learner (no V2 yet) |
| Skill Map | Edge list | CURRENT / TARGET / STATE readout; HARD/SOFT neighborhood; faded unselected edges | ML Fundamentals neighborhood is usable | 8 | Graph is still a typographic edge list, not a plotted map |
| AI | Grounded facts + Ask | Intelligence note (left rule, not bubbles) | Ask PathFinder + Why this gap on dashboard | 8 | Suggestion chips still look like a prompt palette |
| Judge Mode | Context rail | Where / learned / changed / next | Present on workspace screens | 7 | Too much chrome on mobile; map view used to fall through to “Workspace” (fixed in source) |

## Screenshot-only critique (cycle 1)

Top weaknesses seen in the PNGs, ignoring code:

1. Path is a spine, but still lined like a list.
2. Judge rail occupies too much of 390×844.
3. Dashboard competency section is a list of meters.
4. Career cards remain a 2×2 template for unselected roles.
5. Result / adaptation screens were missing from the screenshot set.

Cycle 2 recaptured a **loaded** dashboard and path/path-why. Assessment submit still did not produce Result / V1 / V2 images.

## Quality gate (honest)

- [x] Major screens rendered (except Result, V1→V2, Why Changed)
- [x] Visual inspection of captured screens
- [x] Two screenshot passes attempted (first miss on workspace load; second recovered dashboard + path)
- [ ] Intermediate animation frames (0/25/50/75/100) — not filmed
- [x] Mobile 390 and desktop 1440 for captured screens
- [ ] Full viewport matrix 430 / 768 / 1280 / 1920
- [x] No occlusion on path-why drawer (path remains readable)
- [ ] Result/V1→V2 controls not observed
- [x] Production build passed
- [x] Backend tests 218 passed, 1 skipped
- [x] Frontend tests 49 passed
- [x] Benchmark 20/20
- [ ] Reduced-motion live check
- [ ] Automated a11y scan after last CSS edit
- [x] Intelligence code not changed in this UI pass (intake 422 work remains from earlier, unrelated to scoring)

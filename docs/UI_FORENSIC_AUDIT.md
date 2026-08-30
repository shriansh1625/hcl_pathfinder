# PathFinder UI forensic audit

Inspected from source plus live composition of `frontend/app`, `components`, `globals.css`, `lib/motion.ts`, and workspace screens. Intelligence architecture is out of scope.

| SCREEN | CURRENT QUALITY | WEAKNESS | SEVERITY | RECOMMENDED CHANGE | RISK | STATUS |
|---|---|---|---|---|---|---|
| Design tokens | Partial | Motion tokens (120/200/380) do not match the 80/140/220/360/hero grammar. Type scale is mostly `text-4xl` + ALL CAPS kickers. | P1 | Semantic type, spacing, z-index, motion tokens | Low | In this pass |
| Canvas | Competent graphite | Grid drift + sage wash reads as generic dark SaaS. | P2 | Lower opacity, respect reduced motion | Low | In this pass |
| Onboarding | Strong DNA, weak gravity | Left column has dead space; ambient route is faint and does not track pointer; right panel is a bordered box. | P1 | Editorial left / command right; route responds to step | Medium | In this pass |
| Goal field | Functional | Still a styled textarea; focus is a 1px border. | P1 | Goal intelligence field with route activation | Low | In this pass |
| Career explorer | Real backend roles | Cards are a cramped 2-col scroll; comparison looks like admin selects. | P1 | Stronger cards, editorial compare columns | Low | In this pass |
| Profile / config | Clear copy | Form controls feel like a questionnaire. | P2 | Configuration language, denser summary | Low | In this pass |
| Dashboard | Weak | Four KPI cards (`dash-stat`) + stacked sections. Same “header + cards” everywhere. | P0 | Command-center composition | Low | In this pass |
| Competency | Good semantics | Meter is thin; UNKNOWN is correct (dashed). | P2 | Stronger current/target distance | Low | In this pass |
| Path | Route spine exists | Extra Mark inside each row; items still read as a card list. | P1 | Spatial spine, state-coded connectors | Low | CSS + waypoint |
| Progress | Honest | Buttons are generic; slider is native. | P2 | Tactile press, confidence track | Low | CSS |
| Assessment | Professional | Answer rows share `.path-row` hover lift — too much motion. | P2 | Diagnostic selection, no lift | Low | CSS |
| Result / V1→V2 | Product hero exists | Choreography already FLIP-based; do not replace. | P1 | Preserve; tighten cascade CSS only | High if rewritten | Preserve |
| Why / Timeline | Forensic copy | Timeline markers are small; archival vs active is subtle. | P2 | Larger destination marker | Low | CSS |
| Skill map | Instrument | Connectors exist; selected neighborhood is quiet. | P2 | Local illumination | Low | CSS |
| Ask PathFinder | Correct (not a chat) | Surface looks like a form footer. | P2 | Contextual grounded panel | Low | CSS |
| Judge Mode | Useful | Reads as a tutorial strip, not mission control. | P1 | Where / knows / changed / next | Low | In this pass |
| Shell / nav | Desktop OK | Nav hidden below `md`; mobile has no primary nav. | P0 | Mobile route track | Low | In this pass |
| Errors / loading | Honest copy | Layout is stable. | P2 | Keep; refine route pulse | Low | Preserve |
| Pointer / parallax | Absent | Buttons and ambient graph do not respond. | P1 | Desktop-only 1–2px | Low | In this pass |
| Overlay | Drawers exist | Sticky footer can collide with CTAs on 390px. | P1 | Compact mobile footer + nav | Medium | In this pass |

## Visual self-red-team (pre-change)

A screenshot without context still reads as a serious dark editorial product, not purple-AI. Weakness is **sameness**: onboarding, dashboard, path, and assessments all use the same hairline card + uppercase kicker + serif H1. The brand is right; the composition is repeating.

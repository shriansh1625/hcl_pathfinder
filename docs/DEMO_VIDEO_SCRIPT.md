# PathFinder — 5-Minute Demo Video Script

**Target length:** 4:45 – 5:00 (leave 10s buffer)  
**Resolution:** 1920×1080 (primary) — also capture 390×844 B-roll if time permits  
**Stack:** Production only — `npm run build` + `next start` on :3002, API on :8000  
**Theme:** Dark (primary); show Light toggle once (~5 seconds)  
**Role for demo:** AI/ML Engineer (Judge demo path)

---

## Pre-Recording Checklist

- [ ] Docker Postgres running; seed complete
- [ ] Backend: `uvicorn app.main:app --port 8000`
- [ ] Frontend: `PORT=3002 npm run start` (NOT `next dev`)
- [ ] Browser zoom 100%; no bookmarks bar
- [ ] Close unrelated tabs; disable notifications
- [ ] Optional: `PATHFINDER_AI_API_KEY` set for live Groq explanations (stub works if not)
- [ ] Practice once with **Judge demo (~90s)** button to learn timing

---

## ON-SCREEN TEXT CARDS (optional, 3 seconds each)

Use simple title cards between sections if not recording voiceover live:

1. **“Evidence → Diagnosis → Adaptation”**
2. **“Not a course list — a competency engine”**
3. **“Path V1 → Path V2 — frozen work preserved”**

---

## SCRIPT

### [0:00 – 0:25] HOOK — The Problem

**SCREEN:** Title card or slow zoom on onboarding hero — “Build the path to the career you want.”

**VOICEOVER:**
> “Most career platforms recommend courses from keywords. They don’t tell you what you’re actually missing, why a resource comes *now*, or how your plan should change when you pass an assessment.
>
> **PathFinder** is different. It’s an evidence-driven intelligence system: **Evidence → Diagnosis → Adaptation.**”

**ACTION:** None yet — let thesis land.

---

### [0:25 – 1:10] ONBOARDING — Goal + Career + Evidence

**SCREEN:** Onboarding step 0 — goal field.

**VOICEOVER:**
> “A learner starts with a natural-language goal — not a dropdown.”

**ACTION:** Type (or paste quickly):
> “I want to become a machine learning engineer focused on computer vision.”

Click **Resolve goal**.

**VOICEOVER (as UI resolves):**
> “PathFinder interprets the language, but the **ontology decides** what’s real. Here — resolved to AI/ML Engineer, matched to our canonical career graph.”

**ACTION:** Click **Pick career manually** OR continue if already resolved → select **AI/ML Engineer** if needed.

Click **Continue** through profile steps. On evidence step, ensure **demo evidence** toggle is ON.

**VOICEOVER:**
> “We fuse self-reported skills with structured evidence. **Unknown doesn’t mean zero** — it means no proof yet.”

**ACTION:** Click **Judge demo (~90s)** OR **Build my path** → wait for workspace.

---

### [1:10 – 1:50] DASHBOARD — Diagnosis

**SCREEN:** Workspace dashboard.

**VOICEOVER:**
> “This is **KNOW** and **DIAGNOSE**. The dashboard shows destination role, diagnosed gaps, and the next action — all from the backend gap engine, not the UI guessing.”

**ACTION:** Scroll slowly through:
- Goal text
- Gap / competency rows (point at UNKNOWN vs GAP states)
- “What to do next”

Click **Continue** to Blockers if footer visible, or navigate via mobile/desktop nav.

**VOICEOVER:**
> “Blockers aren’t vague — they name the prerequisite chain. You can’t skip proof.”

**ACTION:** Briefly show Blockers screen (5–8 seconds).

---

### [1:50 – 2:25] MY PATH — Sequencing + WHY

**SCREEN:** My Path tab.

**VOICEOVER:**
> “The path isn’t a playlist. It’s a **dependency-aware route** — executable, waiting, or blocked.”

**ACTION:** Scroll path. Click **WHY THIS RESOURCE** on one item.

**VOICEOVER:**
> “Every recommendation is auditable. Gap, role relevance, prerequisites, intervention — then optional grounded AI explains the facts. The AI **cannot** change your score or reorder the path.”

**ACTION:** Close drawer. If an executable item shows progress actions, glance at Complete / Struggled / Skip (don’t submit yet).

---

### [2:25 – 3:15] ASSESSMENT — Prove It

**SCREEN:** Assessments tab.

**VOICEOVER:**
> “Proof enters the system through canonical assessments — tied to skills in the ontology.”

**ACTION:** Click **Prove this skill** → answer questions (click through at steady pace) → **Submit**.

**VOICEOVER (during “Updating competency model” if shown):**
> “Assessment evidence fuses into the competency model. Diagnosis updates.”

**ACTION:** Land on **Result** screen. Pause 2 seconds on diagnosis shift.

**VOICEOVER:**
> “The result isn’t a badge — it’s a **diagnosis change** that can trigger adaptation.”

---

### [3:15 – 4:15] ADAPTATION — Path V1 → V2 (HERO MOMENT)

**SCREEN:** Result → click **See what changed** / **What changed**.

**VOICEOVER:**
> “This is PathFinder’s signature moment: **Path V1 becomes Path V2.**”

**ACTION:** Let cascade animation play (or click Skip if practiced). Show:
- Added / moved / blocked items
- **Frozen completed work** (call out explicitly)
- FLIP animation on route if visible

**VOICEOVER:**
> “Completed work is **frozen** — we never steal credit when the plan adapts. New evidence reshapes what’s ahead, not what you’ve already proven.”

**ACTION:** Click **Why this changed** (8–10 seconds on adaptation trace).

**VOICEOVER:**
> “Forensic transparency: what changed, why, and which skill drove it.”

---

### [4:15 – 4:40] SKILL MAP + AI + CLOSE

**SCREEN:** Quick montage (5–7 sec each):

1. **History** — version timeline  
2. **Skill Map** — select one skill, show blocker neighborhood  
3. **Ask PathFinder** — one question, show grounded response  
4. **Theme toggle** — Light mode flash (optional, 3 sec)

**VOICEOVER:**
> “History versions every adaptation. The skill map shows dependency truth. Ask PathFinder explains — it doesn’t decide.
>
> Under the hood: deterministic fusion, gap engine, sequencing, and adaptation — **twenty out of twenty** on our intelligence benchmark. Optional semantic retrieval and Groq explanations sit on top — they don’t replace the engine.”

---

### [4:40 – 5:00] CLOSING CARD

**SCREEN:** GitHub URL + thesis text.

**ON-SCREEN TEXT:**
```
PathFinder
Evidence → Diagnosis → Adaptation

github.com/shriansh1625/hcl_pathfinder
HCLTech AMPlified · Round 2
```

**VOICEOVER:**
> “PathFinder — evidence-driven career intelligence. Clone it, run it, break it — the proofs are in the repo. Thank you.”

**FADE OUT.**

---

## TIMING SUMMARY

| Segment | Duration | Cumulative |
|---------|----------|------------|
| Hook | 0:25 | 0:25 |
| Onboarding | 0:45 | 1:10 |
| Dashboard + Blockers | 0:40 | 1:50 |
| Path + WHY | 0:35 | 2:25 |
| Assessment + Result | 0:50 | 3:15 |
| V1→V2 + Why changed | 1:00 | 4:15 |
| Montage + close | 0:45 | 5:00 |

---

## B-ROLL CUTS (if main take runs long)

Trim in this order:
1. Blockers screen (keep dashboard gaps)
2. Skill Map (keep History)
3. Light theme toggle
4. Ask PathFinder (keep one grounded AI line in voiceover without full UI)

**Never cut:** Assessment → Result → Path V2 → frozen work callout.

---

## VOICEOVER TIPS

- Speak at **~140 words/minute** — script is ~680 words for 5 minutes
- Emphasize: **“ontology decides,” “unknown not zero,” “frozen work,” “AI explains doesn’t control”**
- Avoid: “AI plans your career,” “chatbot recommends courses,” “100% ready”

---

## YOUTUBE UPLOAD NOTES

- **Title:** PathFinder — Evidence-Driven Career Intelligence | HCLTech AMPlified Round 2
- **Description:** Include GitHub link + one-line thesis + timestamps
- **Visibility:** Unlisted or Public per team preference
- **Length:** YouTube accepts 3–5 min; aim for **4:50**

---

## FORM FIELD (when ready)

**Demo video URL:** `https://youtu.be/<your-video-id>`

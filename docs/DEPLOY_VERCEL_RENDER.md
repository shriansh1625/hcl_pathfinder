# Deploy PathFinder on Render + Vercel

Production layout:

| Component | Platform | URL example |
|-----------|----------|-------------|
| PostgreSQL | Render | internal to API |
| FastAPI API | Render | `https://pathfinder-api.onrender.com` |
| Next.js UI | Vercel | `https://pathfinder.vercel.app` |

The browser talks to **Vercel** only. Next.js rewrites `/v1/*`, `/health`, and `/ready` to your Render API (`frontend/next.config.ts`).

**AI on production:** Groq **GPT-OSS 120B** (`openai/gpt-oss-120b`) for grounded explanations and intake — explanation-only; path/scoring/adaptation stay deterministic.

---

## Prerequisites

- GitHub repo: `https://github.com/shriansh1625/hcl_pathfinder`
- [Render](https://render.com) account
- [Vercel](https://vercel.com) account
- [Groq API key](https://console.groq.com) (for live AI explanations)

---

## Option A — One-click Render (recommended)

### 1. Apply the blueprint

1. Render Dashboard → **New +** → **Blueprint**
2. Connect `hcl_pathfinder` and apply `render.yaml` from the repo root
3. Render creates:
   - `pathfinder-db` (Postgres)
   - `pathfinder-api` (Python web service)

### 2. Set Render secrets

Open **pathfinder-api** → **Environment**:

| Variable | Value |
|----------|--------|
| `PATHFINDER_AI_API_KEY` | Your Groq key (`gsk_...`) |
| `PATHFINDER_CORS_ORIGINS` | `https://YOUR-APP.vercel.app` (set after Vercel deploy) |

Already set by blueprint:

```env
PATHFINDER_AI_PROVIDER=groq
PATHFINDER_AI_BASE_URL=https://api.groq.com/openai/v1
PATHFINDER_AI_MODEL=openai/gpt-oss-120b
PATHFINDER_AI_TIMEOUT_SECONDS=30
PATHFINDER_SEMANTIC_ENABLED=false
```

`PATHFINDER_SEMANTIC_ENABLED=false` avoids a heavy `fastembed` cold start on Render free tier. Enable later if you upgrade the instance.

### 3. Verify API

After the first deploy (migrations + seed run automatically):

```text
https://pathfinder-api.onrender.com/health   → 200
https://pathfinder-api.onrender.com/ready    → 200 (DB + ontology)
```

Seed log should show: `47 skills, 8 roles, 58 relationships, 62 resources, 4 assessments`.

---

## Option B — Manual Render setup

If you prefer the dashboard instead of the blueprint:

**PostgreSQL:** New → PostgreSQL → note internal connection string.

**Web service:**

| Setting | Value |
|---------|--------|
| Root Directory | *(repo root)* |
| Build | `pip install -r backend/requirements.txt` |
| Start | `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Pre-deploy | `cd backend && alembic upgrade head && cd .. && python scripts/seed.py` |
| Health check | `/health` |

Use the same environment variables as in Option A. `DATABASE_URL` from Render is auto-normalized to `postgresql+psycopg2://` in `backend/app/core/config.py`.

---

## Deploy frontend on Vercel

1. Vercel → **Add New Project** → import `hcl_pathfinder`
2. **Root Directory:** `frontend`
3. Framework: Next.js (auto)

### Required environment variable

| Name | Value |
|------|--------|
| `NEXT_PUBLIC_API_URL` | `https://pathfinder-api.onrender.com` |

No trailing slash. Apply to **Production** (and Preview if you want PR previews).

4. Deploy

### Verify proxy

```text
https://YOUR-APP.vercel.app/health   → should proxy to Render API
https://YOUR-APP.vercel.app          → onboarding loads
```

### Update CORS on Render

Set on **pathfinder-api**:

```env
PATHFINDER_CORS_ORIGINS=https://YOUR-APP.vercel.app
```

Redeploy API if needed. (Most traffic is same-origin via Vercel rewrites; CORS is a safety net.)

---

## Local development with Groq GPT-OSS 120B

Copy env examples, then in **repo-root** `.env.local`:

```env
PATHFINDER_AI_PROVIDER=groq
PATHFINDER_AI_BASE_URL=https://api.groq.com/openai/v1
PATHFINDER_AI_MODEL=openai/gpt-oss-120b
PATHFINDER_AI_API_KEY=gsk_your_key_here
PATHFINDER_AI_TIMEOUT_SECONDS=30
```

Never commit `.env.local`.

---

## Post-deploy smoke test

From your machine:

```powershell
$env:PATHFINDER_API_URL="https://pathfinder-api.onrender.com"
python scripts\api_smoke_test.py
```

Judge flow on Vercel URL: onboarding → AI/ML Engineer → dashboard → path → assessment → result → Path V2 → Ask PathFinder (should use Groq when key is set).

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Vercel build fails: `NEXT_PUBLIC_API_URL is required` | Add env var in Vercel project settings, redeploy |
| `/ready` 503 | Wait for DB; check `DATABASE_URL`; rerun pre-deploy (migrate + seed) |
| Empty careers | Run Render Shell: `python scripts/seed.py` |
| AI shows “Explanation is unavailable” | Set `PATHFINDER_AI_API_KEY` on Render; confirm `PATHFINDER_AI_PROVIDER=groq` |
| Slow first API request | Render free tier cold start (~30–60s) |
| Groq 404 on model | Model ID must be exactly `openai/gpt-oss-120b` |

---

## Security checklist

- Groq key **only** on Render (backend)
- Vercel gets **only** `NEXT_PUBLIC_API_URL` (public by design)
- Do not commit `.env.local`, GitHub PATs, or API keys
- Rotate any key that was ever pasted into chat or committed by mistake

---

## Custom domains

1. Add domain on Vercel → update `PATHFINDER_CORS_ORIGINS` on Render
2. Optional API subdomain on Render → update `NEXT_PUBLIC_API_URL` on Vercel → redeploy frontend

---

## Files reference

| File | Purpose |
|------|---------|
| `render.yaml` | Render Blueprint (Postgres + API) |
| `frontend/vercel.json` | Vercel build hints |
| `.env.example` | Local + Groq model reference |
| `frontend/next.config.ts` | API rewrite proxy |

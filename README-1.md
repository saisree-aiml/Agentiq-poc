# Sagility AgentIQ — Intelligent Agent Routing & Performance Optimization Platform

(formerly "AHT Booster")

A Streamlit application that recommends the best contact-center agent to
handle a given call category, based entirely on the uploaded Excel file (no
hardcoded agents, scores, or savings) — now with login, role-based access
(Manager / Admin), a Top 10 rankings view, and an Admin Console for data
management and configuration.

## Demo login credentials

| Role | Username | Password |
|---|---|---|
| Manager | manager@sagility.com | Manager@123 |
| Admin | admin@sagility.com | Admin@123 |

These are in-memory demo accounts (see `DEMO_ACCOUNTS` in `app.py`), structured
so they can later be replaced by enterprise SSO without touching the rest of
the app.

## What Manager vs Admin can see

- **Manager:** Dashboard, Recommendation, Top 10 Rankings
- **Admin:** everything above, plus the Admin Console (Data Management, Data
  Validation, Ranking Configuration, Availability Configuration)

## Core logic is unchanged

The scoring formula, normalization, eligibility filter, and time-saving
calculation are byte-for-byte the same as the original AHT Booster app. The
only difference is that the weights (60/15/15/10) and the 80% availability
threshold now live in session state, defaulting to those exact original
values — an Admin can optionally override them from the Admin Console, with
a one-click "Reset to Existing Default" always available.

## Files

- `app.py` — the Streamlit application
- `requirements.txt` — Python dependencies
- `AHT_Booster_Demo_Input.xlsx` — synthetic demo dataset (100 agents × 6 categories = 600 rows)
- `generate_data.py` — script used to generate the demo dataset (optional, not needed to run the app)

## Run locally (optional)

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the local URL Streamlit prints (usually `http://localhost:8501`),
and upload `AHT_Booster_Demo_Input.xlsx` when prompted.

## Deploy for free — Streamlit Community Cloud (5 minutes)

**Step 1 — Put the code on GitHub**
1. Go to https://github.com and sign in (create a free account if you don't have one).
2. Click the **+** icon (top right) → **New repository**.
3. Name it `aht-booster` → set it to **Public** → click **Create repository**.
4. On the new repo page, click **uploading an existing file**.
5. Drag in `app.py`, `requirements.txt`, and `AHT_Booster_Demo_Input.xlsx`.
6. Click **Commit changes**.

**Step 2 — Deploy on Streamlit Community Cloud**
1. Go to https://share.streamlit.io and sign in with your GitHub account (free).
2. Click **Create app** (or **New app**).
3. Choose **Deploy a public app from GitHub**.
4. Select:
   - Repository: `your-username/aht-booster`
   - Branch: `main`
   - Main file path: `app.py`
5. Click **Deploy**.
6. Wait 1–3 minutes while it installs dependencies and starts the app.
7. You'll get a public link like:
   `https://aht-booster-your-username.streamlit.app`

**Step 3 — Send it**
Copy that link and send it to your manager on WhatsApp. It works from any
phone or laptop browser — no install needed on their end.

When the app opens, upload `AHT_Booster_Demo_Input.xlsx` (or your own file
with the same required columns) to run the analysis.

## Required Excel columns

At minimum:
- `Agent ID`
- `Agent Name`
- `Call Category`
- `Average AHT (sec)`

Recommended (used by the scoring engine when present):
- `Calls Handled`
- `Target AHT (sec)`
- `Quality Score (%)`
- `FCR (%)`
- `Transfer Rate (%)`
- `Availability (%)`
- `Experience (Months)`

## How the recommendation works

For the selected call category:
1. Filter agents to that category, and to Availability ≥ 80% (if that column exists).
2. Normalize AHT, Quality, FCR, and Transfer Rate to a 0–100 scale.
3. Weighted score = AHT 60% + Quality 15% + FCR 15% + Transfer Rate 10%.
4. Rank and recommend the top-scoring agent.
5. Savings = (Category Average AHT − Recommended Agent AHT) × Number of Calls, converted to minutes.

Everything recalculates live from whatever Excel file is uploaded.

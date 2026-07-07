# Incremental Build Roadmap

Build order — **one piece at a time, no jumping ahead**.

## Step 1 — Login page ✅ (current)

- Enterprise login UI (dark navy, centered card)
- Username / password form
- Loading, error, and success states
- Session created on successful sign-in
- Temporary post-login placeholder (not the dashboard)
- Mock users until `dbo.users` is wired in Step 3

## Step 2 — Dashboard layout

- Operations-console shell (navbar, header, content area)
- Phase tabs placeholder (PRE, MAIN, BI, DAY5, POST)
- Static layout only — no database yet

## Step 3 — Connection loading

- Bootstrap env vars → `orchestration.app_connections`
- PRIMARY / REMOTE_SQL from database
- Encrypted password storage
- Replace mock auth with `dbo.users`

## Step 4 — Role-based screens

- Admin vs ReadOnly navigation
- Hide execution/admin controls from ReadOnly

## Step 5 — SQL Agent jobs page

- `orchestration.usp_GetMonitoredAgentJobs`
- SPUS001BDBEXT + SPAZ001EDM10

## Step 6 — Step execution

- Dashboard driven by `orchestration.job_steps`
- Run one step at a time via stored procedures

## Step 7 — Step validation

- Validation stored procedures per step
- Pass/fail display on step cards

## Step 8 — Logs panel

- `orchestration.db_execution_log`
- Live refresh

## Step 9 — Metrics panel

- `orchestration.run_metrics`
- Run progress header

## Step 10 — PowerShell bootstrap

- `scripts/setup.ps1`
- venv, install, port 50006, optional DB test

---

Design references for later steps are in `docs/planning/`.

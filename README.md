# Job Match API

A small, transparent, rule-based API that recommends jobs to candidates
(and candidates to jobs) based on skills, experience, location, and salary fit.

## Running locally

```bash
python -m venv venv
venv\Scripts\Activate.ps1   # Windows PowerShell
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API is now at http://localhost:8000 (or another port if 8000 is taken —
use `--port 8001`). Interactive docs at http://localhost:8000/docs.

Run tests:
```bash
pytest -q
```

## Running via Docker

```bash
docker compose up --build
```

**Note:** Dockerfile and docker-compose.yml are included but I was unable to
verify them locally due to a WSL2 environment issue on my Windows machine
(Docker Desktop couldn't start because the WSL2 backend failed to install/update).
The syntax follows standard FastAPI containerization patterns and should work
on a machine with a functioning Docker setup. The data store is in-memory
either way (resets on restart) — Postgres isn't wired up; see "What I'd do
differently" below.

## Endpoints

- `POST /candidates` — create a candidate
- `POST /jobs` — create a job
- `GET /candidates/{id}/recommendations?limit=N` — ranked jobs for a candidate
- `GET /jobs/{id}/recommendations?limit=N` — ranked candidates for a job (bonus, reverse view)
- Optional query params `weight_skills`, `weight_experience`, `weight_location`,
  `weight_salary` override the default weights on either recommendation endpoint (bonus).

## Scoring formula

Default weights, out of 100: **skills 50, experience 20, location 15, salary 15**.
Weights are normalized to sum to 100 regardless of what's passed in, so partial
overrides never accidentally inflate or shrink the total.

### Why these weights
Skills get the largest share because they're the most direct signal of whether
someone can do the job — and because must-have skills already act as a hard
filter, the remaining skill points reward *depth* of fit (nice-to-haves), not
just eligibility. Experience, location, and salary are all "soft" fit factors
that affect happiness/logistics more than raw capability, so they're weighted
lower and roughly evenly.

### Skills (default max 50)
Must-have skills are a hard gate — a job missing one is excluded from results
entirely before scoring runs, never just penalized. Within the skill score,
60% of the points are allocated to must-haves and 40% to nice-to-haves. Since
must-haves are guaranteed satisfied by the time we reach scoring, that 60%
share is effectively "free" for any job that appears at all — the real
differentiator between recommended jobs is how many nice-to-haves the
candidate covers.

### Experience (default max 20)
Meeting or exceeding `minYearsExperience` scores full marks. Falling short
scores `max * (candidateYears / minYears)` — a linear penalty, not exclusion.
I chose a penalty over exclusion because experience thresholds in job postings
are frequently soft/aspirational, and a candidate at 80% of the stated
requirement is usually still worth surfacing, just ranked below someone who
fully meets it.

### Location (default max 15)
Exact match scores full marks. `remoteAllowed = true` without a location match
scores 2/3 of max. A location mismatch with no remote option scores 0 — it's
not a hard filter (still shown), but it should rank at the very bottom on this
dimension since there's no way this job accommodates their location.

### Salary (default max 15)
Tiered, not a smooth curve, for explainability:
- Job's minimum already meets or exceeds the candidate's expectation → full marks.
- Candidate's expectation falls inside the job's range → 75% of max.
- Job's max is below the candidate's expectation → near-zero, scaled by
  `jobMax / expectedSalary` so a job that's just barely under isn't scored
  identically to one wildly under.

## Assumptions

- `expectedSalary` is treated as a single number (a candidate's ask), not a range.
- Skill name matching is case-insensitive, exact string match (no fuzzy/synonym
  matching — "JS" and "JavaScript" are treated as different skills).
- No persistence: data lives in memory and resets on restart.

## What I'd do differently with more time

- Wire up Postgres (SQLAlchemy models + Alembic migrations) instead of the
  in-memory store; the docker-compose is currently API-only for this reason.
- Get a working Docker environment to actually verify the containerized setup
  end-to-end — my local WSL2 install broke partway through this assignment.
- Fuzzy/synonym matching for skills.
- Pagination for `/candidates` and `/jobs` list endpoints.
- Return the applied weights alongside each recommendation response, since
  they're now configurable per-request.

## AI tool usage disclosure

I used an AI assistant (Claude) to help scaffold this project and draft the
scoring engine, routes, and initial test cases. I reviewed and adjusted:
- the salary tiering logic (initial draft used a smooth curve; I switched to
  explicit tiers because it's easier to explain and test edge cases against),
- the must-have skill exclusion path, to make sure it short-circuits before
  any other scoring runs rather than just zeroing out points,
- weight normalization, so passing partial/unusual weight combinations doesn't
  silently break the 0–100 scale.
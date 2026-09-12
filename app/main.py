from fastapi import FastAPI, HTTPException, Query
from typing import List, Optional

from app.models import CandidateIn, Candidate, JobIn, Job, ScoreWeights
from app.store import store
from app.scoring import score_candidate_job, DEFAULT_WEIGHTS

app = FastAPI(title="Job Match API")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/candidates", response_model=Candidate, status_code=201)
def create_candidate(payload: CandidateIn):
    return store.add_candidate(payload)


@app.get("/candidates", response_model=List[Candidate])
def list_candidates():
    return store.list_candidates()


@app.get("/candidates/{candidate_id}", response_model=Candidate)
def get_candidate(candidate_id: str):
    candidate = store.get_candidate(candidate_id)
    if not candidate:
        raise HTTPException(404, "candidate not found")
    return candidate


@app.post("/jobs", response_model=Job, status_code=201)
def create_job(payload: JobIn):
    return store.add_job(payload)


@app.get("/jobs", response_model=List[Job])
def list_jobs():
    return store.list_jobs()


@app.get("/jobs/{job_id}", response_model=Job)
def get_job(job_id: str):
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    return job


def _weights_from_query(
    weight_skills: Optional[float] = None,
    weight_experience: Optional[float] = None,
    weight_location: Optional[float] = None,
    weight_salary: Optional[float] = None,
) -> ScoreWeights:
    return ScoreWeights(
        skills=weight_skills if weight_skills is not None else DEFAULT_WEIGHTS.skills,
        experience=weight_experience if weight_experience is not None else DEFAULT_WEIGHTS.experience,
        location=weight_location if weight_location is not None else DEFAULT_WEIGHTS.location,
        salary=weight_salary if weight_salary is not None else DEFAULT_WEIGHTS.salary,
    )


@app.get("/candidates/{candidate_id}/recommendations")
def recommend_jobs_for_candidate(
    candidate_id: str,
    limit: Optional[int] = Query(default=None, gt=0),
    weight_skills: Optional[float] = None,
    weight_experience: Optional[float] = None,
    weight_location: Optional[float] = None,
    weight_salary: Optional[float] = None,
):
    candidate = store.get_candidate(candidate_id)
    if not candidate:
        raise HTTPException(404, "candidate not found")

    weights = _weights_from_query(weight_skills, weight_experience, weight_location, weight_salary)

    results = []
    for job in store.list_jobs():
        result = score_candidate_job(candidate, job, weights)
        if result.excluded:
            continue
        results.append({
            "job_id": job.id,
            "title": job.title,
            "overall_score": result.overall_score,
            "breakdown": result.breakdown,
        })

    results.sort(key=lambda r: r["overall_score"], reverse=True)
    return results[:limit] if limit else results
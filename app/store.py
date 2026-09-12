from typing import Dict, List, Optional
from app.models import Candidate, CandidateIn, Job, JobIn


class InMemoryStore:
    def __init__(self):
        self.candidates: Dict[str, Candidate] = {}
        self.jobs: Dict[str, Job] = {}

    def add_candidate(self, data: CandidateIn) -> Candidate:
        candidate = Candidate(**data.model_dump())
        self.candidates[candidate.id] = candidate
        return candidate

    def get_candidate(self, candidate_id: str) -> Optional[Candidate]:
        return self.candidates.get(candidate_id)

    def list_candidates(self) -> List[Candidate]:
        return list(self.candidates.values())

    def add_job(self, data: JobIn) -> Job:
        job = Job(**data.model_dump())
        self.jobs[job.id] = job
        return job

    def get_job(self, job_id: str) -> Optional[Job]:
        return self.jobs.get(job_id)

    def list_jobs(self) -> List[Job]:
        return list(self.jobs.values())

    def reset(self):
        self.candidates.clear()
        self.jobs.clear()


store = InMemoryStore()
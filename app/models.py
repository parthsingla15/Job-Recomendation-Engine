from pydantic import BaseModel, Field
from typing import List
from uuid import uuid4


class SkillRequirement(BaseModel):
    name: str
    must_have: bool


class CandidateIn(BaseModel):
    name: str
    skills: List[str]
    years_of_experience: float
    location: str
    expected_salary: float


class Candidate(CandidateIn):
    id: str = Field(default_factory=lambda: str(uuid4()))


class SalaryRange(BaseModel):
    min: float
    max: float


class JobIn(BaseModel):
    title: str
    required_skills: List[SkillRequirement]
    min_years_experience: float
    location: str
    salary_range: SalaryRange
    remote_allowed: bool


class Job(JobIn):
    id: str = Field(default_factory=lambda: str(uuid4()))


class ScoreWeights(BaseModel):
    skills: float = 50
    experience: float = 20
    location: float = 15
    salary: float = 15


class DimensionScore(BaseModel):
    score: float
    max: float
    details: str


class ScoreBreakdown(BaseModel):
    skills: DimensionScore
    experience: DimensionScore
    location: DimensionScore
    salary: DimensionScore


class MatchResult(BaseModel):
    overall_score: float
    breakdown: ScoreBreakdown
    excluded: bool = False
    exclusion_reason: str | None = None
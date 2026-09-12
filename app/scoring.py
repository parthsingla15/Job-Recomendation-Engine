from app.models import Candidate, Job, ScoreWeights, DimensionScore, ScoreBreakdown, MatchResult

DEFAULT_WEIGHTS = ScoreWeights(skills=50, experience=20, location=15, salary=15)


def _norm(s: str) -> str:
    return s.strip().lower()


def _round1(n: float) -> float:
    return round(n * 10) / 10


def _normalize_weights(weights: ScoreWeights) -> ScoreWeights:
    total = weights.skills + weights.experience + weights.location + weights.salary
    if total <= 0:
        return DEFAULT_WEIGHTS
    scale = 100 / total
    return ScoreWeights(
        skills=weights.skills * scale,
        experience=weights.experience * scale,
        location=weights.location * scale,
        salary=weights.salary * scale,
    )


def has_all_must_have_skills(candidate: Candidate, job: Job) -> bool:
    candidate_skills = {_norm(s) for s in candidate.skills}
    must_haves = [s for s in job.required_skills if s.must_have]
    return all(_norm(s.name) in candidate_skills for s in must_haves)


def _score_skills(candidate: Candidate, job: Job, max_points: float) -> DimensionScore:
    candidate_skills = {_norm(s) for s in candidate.skills}
    must_haves = [s for s in job.required_skills if s.must_have]
    nice_to_haves = [s for s in job.required_skills if not s.must_have]

    # Must-haves are already guaranteed satisfied (hard gate applied before
    # scoring runs), so they earn the full must-have share. We still compute
    # it defensively rather than hardcoding "full marks".
    must_have_weight = max_points * 0.6
    nice_to_have_weight = max_points * 0.4

    must_matched = sum(1 for s in must_haves if _norm(s.name) in candidate_skills)
    must_score = must_have_weight if not must_haves else must_have_weight * (must_matched / len(must_haves))

    nice_matched = sum(1 for s in nice_to_haves if _norm(s.name) in candidate_skills)
    nice_score = nice_to_have_weight if not nice_to_haves else nice_to_have_weight * (nice_matched / len(nice_to_haves))

    score = _round1(must_score + nice_score)
    details = f"must-have {must_matched}/{len(must_haves)}, nice-to-have {nice_matched}/{len(nice_to_haves)}"
    return DimensionScore(score=score, max=max_points, details=details)


def _score_experience(candidate: Candidate, job: Job, max_points: float) -> DimensionScore:
    if job.min_years_experience <= 0 or candidate.years_of_experience >= job.min_years_experience:
        return DimensionScore(
            score=max_points, max=max_points,
            details=f"meets minimum of {job.min_years_experience} yrs",
        )
    ratio = candidate.years_of_experience / job.min_years_experience
    score = max(0.0, max_points * ratio)
    return DimensionScore(
        score=_round1(score), max=max_points,
        details=f"{candidate.years_of_experience}/{job.min_years_experience} yrs required — penalized, not excluded",
    )


def _score_location(candidate: Candidate, job: Job, max_points: float) -> DimensionScore:
    if _norm(candidate.location) == _norm(job.location):
        return DimensionScore(score=max_points, max=max_points, details=f"exact location match ({job.location})")
    if job.remote_allowed:
        score = _round1(max_points * (2 / 3))
        return DimensionScore(score=score, max=max_points, details="remote allowed, no location match")
    return DimensionScore(
        score=0, max=max_points,
        details=f"location mismatch ({candidate.location} vs {job.location}), not remote",
    )


def _score_salary(candidate: Candidate, job: Job, max_points: float) -> DimensionScore:
    expected = candidate.expected_salary
    lo, hi = job.salary_range.min, job.salary_range.max

    if expected <= 0:
        return DimensionScore(score=max_points, max=max_points, details="no salary expectation given")
    if lo >= expected:
        return DimensionScore(
            score=max_points, max=max_points,
            details=f"job min (${lo:.0f}) already meets/exceeds expectation (${expected:.0f})",
        )
    if hi >= expected:
        score = _round1(max_points * 0.75)
        return DimensionScore(
            score=score, max=max_points,
            details=f"expectation (${expected:.0f}) falls within range [${lo:.0f}, ${hi:.0f}]",
        )
    ratio = max(0.0, min(1.0, hi / expected))
    score = _round1(max_points * 0.25 * ratio)
    return DimensionScore(
        score=score, max=max_points,
        details=f"job max (${hi:.0f}) below expectation (${expected:.0f})",
    )


def score_candidate_job(candidate: Candidate, job: Job, weights: ScoreWeights = DEFAULT_WEIGHTS) -> MatchResult:
    w = _normalize_weights(weights)

    if not has_all_must_have_skills(candidate, job):
        return MatchResult(
            overall_score=0,
            excluded=True,
            exclusion_reason="missing one or more must-have skills",
            breakdown=ScoreBreakdown(
                skills=DimensionScore(score=0, max=_round1(w.skills), details="excluded: missing must-have skill(s)"),
                experience=DimensionScore(score=0, max=_round1(w.experience), details="not scored (excluded)"),
                location=DimensionScore(score=0, max=_round1(w.location), details="not scored (excluded)"),
                salary=DimensionScore(score=0, max=_round1(w.salary), details="not scored (excluded)"),
            ),
        )

    skills = _score_skills(candidate, job, w.skills)
    experience = _score_experience(candidate, job, w.experience)
    location = _score_location(candidate, job, w.location)
    salary = _score_salary(candidate, job, w.salary)

    overall = _round1(skills.score + experience.score + location.score + salary.score)

    return MatchResult(
        overall_score=overall,
        breakdown=ScoreBreakdown(skills=skills, experience=experience, location=location, salary=salary),
    )
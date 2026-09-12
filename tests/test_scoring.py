import pytest
from app.models import Candidate, Job, SkillRequirement, SalaryRange, ScoreWeights
from app.scoring import score_candidate_job, has_all_must_have_skills, DEFAULT_WEIGHTS


def make_candidate(**overrides):
    base = dict(
        name="Test Candidate",
        skills=["python", "sql"],
        years_of_experience=3,
        location="Remote",
        expected_salary=80000,
    )
    base.update(overrides)
    return Candidate(**base)


def make_job(**overrides):
    base = dict(
        title="Backend Engineer",
        required_skills=[
            SkillRequirement(name="python", must_have=True),
            SkillRequirement(name="docker", must_have=False),
        ],
        min_years_experience=2,
        location="Remote",
        salary_range=SalaryRange(min=70000, max=100000),
        remote_allowed=True,
    )
    base.update(overrides)
    return Job(**base)


def test_missing_must_have_skill_excludes_job():
    candidate = make_candidate(skills=["sql"])  # no python
    job = make_job()
    result = score_candidate_job(candidate, job)
    assert result.excluded is True
    assert result.overall_score == 0
    assert not has_all_must_have_skills(candidate, job)


def test_nice_to_have_boosts_but_does_not_gate():
    candidate = make_candidate(skills=["python"])  # has must-have, missing nice-to-have
    job = make_job()
    result = score_candidate_job(candidate, job)
    assert result.excluded is False

    candidate_with_bonus = make_candidate(skills=["python", "docker"])
    result_with_bonus = score_candidate_job(candidate_with_bonus, job)
    assert result_with_bonus.breakdown.skills.score > result.breakdown.skills.score


def test_under_experienced_is_penalized_not_excluded():
    candidate = make_candidate(years_of_experience=1, skills=["python"])
    job = make_job(min_years_experience=4)
    result = score_candidate_job(candidate, job)
    assert result.excluded is False
    assert 0 < result.breakdown.experience.score < result.breakdown.experience.max


def test_meeting_experience_scores_full_marks():
    candidate = make_candidate(years_of_experience=5, skills=["python"])
    job = make_job(min_years_experience=4)
    result = score_candidate_job(candidate, job)
    assert result.breakdown.experience.score == result.breakdown.experience.max


def test_exact_location_beats_remote_beats_mismatch():
    job = make_job(location="Bangalore", remote_allowed=True)

    exact = make_candidate(skills=["python"], location="Bangalore")
    remote_only = make_candidate(skills=["python"], location="Delhi")
    job_no_remote = make_job(location="Bangalore", remote_allowed=False)
    mismatch = make_candidate(skills=["python"], location="Delhi")

    exact_score = score_candidate_job(exact, job).breakdown.location.score
    remote_score = score_candidate_job(remote_only, job).breakdown.location.score
    mismatch_score = score_candidate_job(mismatch, job_no_remote).breakdown.location.score

    assert exact_score > remote_score > mismatch_score
    assert mismatch_score == 0


def test_salary_no_overlap_scores_near_zero():
    candidate = make_candidate(skills=["python"], expected_salary=150000)
    job = make_job(salary_range=SalaryRange(min=70000, max=100000))
    result = score_candidate_job(candidate, job)
    assert result.breakdown.salary.score < result.breakdown.salary.max * 0.3


def test_salary_comfortably_above_expectation_scores_highest():
    candidate = make_candidate(skills=["python"], expected_salary=60000)
    job = make_job(salary_range=SalaryRange(min=70000, max=100000))
    result = score_candidate_job(candidate, job)
    assert result.breakdown.salary.score == result.breakdown.salary.max


def test_salary_within_range_scores_well_but_not_max():
    candidate = make_candidate(skills=["python"], expected_salary=85000)
    job = make_job(salary_range=SalaryRange(min=70000, max=100000))
    result = score_candidate_job(candidate, job)
    assert 0 < result.breakdown.salary.score < result.breakdown.salary.max


def test_custom_weights_are_normalized_to_100():
    candidate = make_candidate(skills=["python", "docker"])
    job = make_job()
    weights = ScoreWeights(skills=80, experience=40, location=40, salary=40)  # sums to 200
    result = score_candidate_job(candidate, job, weights)
    total_max = (
        result.breakdown.skills.max
        + result.breakdown.experience.max
        + result.breakdown.location.max
        + result.breakdown.salary.max
    )
    assert round(total_max) == 100


def test_overall_score_is_sum_of_dimensions_and_capped_at_100():
    candidate = make_candidate(skills=["python", "docker"], years_of_experience=10, expected_salary=50000)
    job = make_job()
    result = score_candidate_job(candidate, job)
    assert result.overall_score <= 100
    dims = result.breakdown
    expected_total = round(dims.skills.score + dims.experience.score + dims.location.score + dims.salary.score, 1)
    assert result.overall_score == expected_total
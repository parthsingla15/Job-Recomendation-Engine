from fastapi.testclient import TestClient
from app.main import app
from app.store import store

client = TestClient(app)


def setup_function():
    store.reset()


def test_must_have_missing_job_never_appears_in_recommendations():
    candidate = client.post("/candidates", json={
        "name": "No Python Dev",
        "skills": ["java"],
        "years_of_experience": 3,
        "location": "Remote",
        "expected_salary": 80000,
    }).json()

    client.post("/jobs", json={
        "title": "Python Backend Role",
        "required_skills": [{"name": "python", "must_have": True}],
        "min_years_experience": 1,
        "location": "Remote",
        "salary_range": {"min": 70000, "max": 100000},
        "remote_allowed": True,
    })

    resp = client.get(f"/candidates/{candidate['id']}/recommendations")
    assert resp.status_code == 200
    assert resp.json() == []


def test_limit_query_param_caps_results():
    candidate = client.post("/candidates", json={
        "name": "Generalist",
        "skills": ["python"],
        "years_of_experience": 5,
        "location": "Remote",
        "expected_salary": 50000,
    }).json()

    for i in range(5):
        client.post("/jobs", json={
            "title": f"Role {i}",
            "required_skills": [{"name": "python", "must_have": True}],
            "min_years_experience": 1,
            "location": "Remote",
            "salary_range": {"min": 40000, "max": 60000},
            "remote_allowed": True,
        })

    resp = client.get(f"/candidates/{candidate['id']}/recommendations?limit=2")
    assert len(resp.json()) == 2


def test_custom_weights_via_query_params_change_ranking():
    candidate = client.post("/candidates", json={
        "name": "Skill Heavy",
        "skills": ["python", "docker", "kubernetes"],
        "years_of_experience": 1,
        "location": "Mumbai",
        "expected_salary": 90000,
    }).json()

    client.post("/jobs", json={
        "title": "Senior Role",
        "required_skills": [
            {"name": "python", "must_have": True},
            {"name": "docker", "must_have": False},
            {"name": "kubernetes", "must_have": False},
        ],
        "min_years_experience": 8,
        "location": "Delhi",
        "salary_range": {"min": 60000, "max": 80000},
        "remote_allowed": False,
    })

    default_resp = client.get(f"/candidates/{candidate['id']}/recommendations").json()
    skills_heavy_resp = client.get(
        f"/candidates/{candidate['id']}/recommendations"
        "?weight_skills=90&weight_experience=5&weight_location=2.5&weight_salary=2.5"
    ).json()

    assert skills_heavy_resp[0]["overall_score"] != default_resp[0]["overall_score"]
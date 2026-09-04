import pytest
from app.services.matching_service import (
    evaluate_candidate_job_match,
    MatchEvaluationResult,
)
from app.services.skill_taxonomy import normalize_skill

def test_canonical_skill_taxonomy():
    assert normalize_skill("js")[0] == "JavaScript"
    assert normalize_skill("ReactJS")[0] == "React"
    assert normalize_skill("py")[0] == "Python"
    assert normalize_skill("k8s")[0] == "Kubernetes"
    assert normalize_skill("AWS")[0] == "AWS"

    skills = [normalize_skill(s)[0] for s in ["Postgres", "FASTAPI", "docker", "K8s", "Next.js"]]
    assert "PostgreSQL" in skills
    assert "FastAPI" in skills
    assert "Docker" in skills
    assert "Kubernetes" in skills
    assert "Next.js" in skills

def test_perfect_match_fixture():
    candidate = {
        "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS", "Redis"],
        "years_experience": 6.0,
        "seniority": "senior",
        "domains": ["Backend", "Distributed Systems", "Cloud"],
        "projects": [
            {"title": "P1", "technologies": ["Kafka", "Python"], "description": "Kafka pipeline"},
            {"title": "P2", "technologies": ["FastAPI", "PostgreSQL"], "description": "FastAPI service"},
            {"title": "P3", "technologies": ["AWS", "Docker"], "description": "Cloud migration"},
        ],
    }
    job = {
        "required_skills": ["Python", "FastAPI", "PostgreSQL"],
        "preferred_skills": ["Docker", "AWS"],
        "experience_min": 4.0,
        "experience_max": 7.0,
        "seniority": "senior",
        "domains": ["Backend", "Distributed Systems"],
    }

    result = evaluate_candidate_job_match(candidate, job)

    assert result.required_skill_coverage == 100.0
    assert result.preferred_skill_coverage == 100.0
    assert result.experience_fit == 100.0
    assert result.project_relevance >= 90.0
    assert result.seniority_fit == 100.0
    assert result.domain_fit == 100.0
    assert result.overall_score >= 95.0
    assert len(result.gaps) == 0
    assert any(s["skill"] == "Python" for s in result.strengths)

def test_partial_match_fixture():
    candidate = {
        "skills": ["Python", "Django", "MySQL"],
        "years_experience": 3.0,
        "seniority": "mid",
        "domains": ["Web Development"],
        "projects": [
            {"title": "P1", "description": "Django monolith"},
        ],
    }
    job = {
        "required_skills": ["Python", "FastAPI", "PostgreSQL", "Kafka"],
        "preferred_skills": ["Docker", "Kubernetes", "AWS"],
        "experience_min": 5.0,
        "experience_max": 8.0,
        "seniority": "senior",
        "domains": ["Distributed Systems", "Cloud"],
    }

    result = evaluate_candidate_job_match(candidate, job)

    # 1 out of 4 required skills (25%)
    assert result.required_skill_coverage == 25.0
    gap_skills = [g["skill"] for g in result.gaps]
    assert "FastAPI" in gap_skills
    assert "Kafka" in gap_skills
    assert "PostgreSQL" in gap_skills

    # 0 out of 3 preferred skills (0%)
    assert result.preferred_skill_coverage == 0.0

    # 3 years vs 5 years required
    assert result.experience_fit < 100.0
    # Mid vs Senior
    assert result.seniority_fit < 100.0
    assert result.overall_score < 50.0

def test_deterministic_scoring_reproducibility():
    candidate = {
        "skills": ["Go", "Kubernetes", "gRPC", "Docker"],
        "years_experience": 4.5,
        "seniority": "mid",
        "domains": ["Infrastructure", "Backend"],
        "projects": [
            {"title": "P1", "description": "Kube operator in Go"},
            {"title": "P2", "description": "gRPC gateway"},
        ],
    }
    job = {
        "required_skills": ["Go", "Kubernetes", "Docker"],
        "preferred_skills": ["gRPC", "Terraform"],
        "experience_min": 3.0,
        "experience_max": 6.0,
        "seniority": "mid",
        "domains": ["Infrastructure"],
    }

    r1 = evaluate_candidate_job_match(candidate, job)
    r2 = evaluate_candidate_job_match(candidate, job)

    assert r1.overall_score == r2.overall_score
    assert r1.required_skill_coverage == r2.required_skill_coverage
    assert r1.preferred_skill_coverage == r2.preferred_skill_coverage
    assert r1.explanation == r2.explanation

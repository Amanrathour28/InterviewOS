"""
Deterministic Candidate-Job Matching Engine — Phase 13.

Calculates reproducible, explainable component scores without relying on opaque LLM scores:
- Required Skill Coverage (0 - 100)
- Preferred Skill Coverage (0 - 100)
- Experience Fit (0 - 100)
- Project Relevance (0 - 100)
- Seniority Fit (0 - 100)
- Domain Fit (0 - 100)
- Weighted Overall Match Score (0 - 100)
"""

from typing import Any, Dict, List, Optional, Set, Tuple
from app.services.skill_taxonomy import normalize_skill

# Seniority level ordering for distance calculation
SENIORITY_LEVELS = {
    "entry": 1,
    "junior": 1,
    "mid": 2,
    "senior": 3,
    "lead": 4,
    "principal": 5,
    "staff": 5,
    "director": 6,
}

DEFAULT_WEIGHTS = {
    "required_skills": 0.35,
    "preferred_skills": 0.15,
    "experience_fit": 0.15,
    "project_relevance": 0.15,
    "seniority_fit": 0.10,
    "domain_fit": 0.10,
}


class MatchEvaluationResult:
    def __init__(
        self,
        overall_score: float,
        required_skill_coverage: float,
        preferred_skill_coverage: float,
        experience_fit: float,
        project_relevance: float,
        seniority_fit: float,
        domain_fit: float,
        scoring_weights: Dict[str, float],
        strengths: List[Dict[str, Any]],
        gaps: List[Dict[str, Any]],
        verification_areas: List[Dict[str, Any]],
        explanation: str,
    ):
        self.overall_score = round(overall_score, 1)
        self.required_skill_coverage = round(required_skill_coverage, 1)
        self.preferred_skill_coverage = round(preferred_skill_coverage, 1)
        self.experience_fit = round(experience_fit, 1)
        self.project_relevance = round(project_relevance, 1)
        self.seniority_fit = round(seniority_fit, 1)
        self.domain_fit = round(domain_fit, 1)
        self.scoring_weights = scoring_weights
        self.strengths = strengths
        self.gaps = gaps
        self.verification_areas = verification_areas
        self.explanation = explanation


def evaluate_candidate_job_match(
    candidate_profile: Dict[str, Any],
    job_profile: Dict[str, Any],
    claims: Optional[List[Dict[str, Any]]] = None,
    weights: Optional[Dict[str, float]] = None,
) -> MatchEvaluationResult:
    """
    Executes a deterministic, explainable evaluation of a candidate against a job specification.
    """
    scoring_weights = weights or DEFAULT_WEIGHTS.copy()
    claims_list = claims or []

    # 1. Normalize Candidate Skills & Evidence
    candidate_skills_raw = candidate_profile.get("skills", [])
    candidate_skill_map: Dict[str, Dict[str, Any]] = {}

    for item in candidate_skills_raw:
        if isinstance(item, str):
            canon, cat = normalize_skill(item)
            candidate_skill_map[canon] = {
                "canonical": canon,
                "category": cat,
                "evidence": f"Listed in candidate skill profile: {item}",
                "confidence": 1.0,
            }
        elif isinstance(item, dict):
            name = item.get("name") or item.get("skill") or ""
            canon, cat = normalize_skill(name)
            candidate_skill_map[canon] = {
                "canonical": canon,
                "category": item.get("category") or cat,
                "proficiency": item.get("proficiency", "proficient"),
                "experience_years": item.get("years_of_experience") or item.get("experience_years"),
                "evidence": item.get("evidence") or f"Listed in candidate skills ({item.get('proficiency', 'proficient')})",
                "confidence": item.get("confidence", 1.0),
            }

    # Integrate resume claims into skill map
    for c in claims_list:
        claim_text = c.get("claim", "")
        evidence_dict = c.get("evidence", {})
        evidence_str = evidence_dict.get("text") if isinstance(evidence_dict, dict) else str(evidence_dict)

        # Check which canonical skills are mentioned in the claim
        for canon in candidate_skill_map.keys():
            if canon.lower() in claim_text.lower() and evidence_str:
                candidate_skill_map[canon]["evidence"] = f"Claim: '{claim_text}' (Source: {evidence_str})"
                candidate_skill_map[canon]["confidence"] = c.get("confidence", 0.9)

    # 2. Extract Job Requirements (Required vs Preferred)
    job_reqs_raw = job_profile.get("requirements", [])
    required_reqs: List[Dict[str, Any]] = []
    preferred_reqs: List[Dict[str, Any]] = []

    for r in job_reqs_raw:
        skill_name = r.get("skill") or r.get("name") or ""
        canon, cat = normalize_skill(skill_name)
        req_type = str(r.get("requirement_type") or r.get("level") or "required").lower()
        importance = float(r.get("importance") or r.get("weight") or 1.0)
        evidence = r.get("evidence") or ""

        entry = {
            "raw_skill": skill_name,
            "canonical_skill": canon,
            "category": cat,
            "importance": importance,
            "evidence": evidence,
        }
        if "pref" in req_type:
            preferred_reqs.append(entry)
        else:
            required_reqs.append(entry)

    # Fallback if requirements not in structured list: check required_skills / preferred_skills fields
    if not required_reqs and not preferred_reqs:
        for s in job_profile.get("required_skills", []):
            skill_str = s if isinstance(s, str) else s.get("skill", "")
            canon, cat = normalize_skill(skill_str)
            required_reqs.append({"raw_skill": skill_str, "canonical_skill": canon, "category": cat, "importance": 1.0, "evidence": "Job description requirement"})
        for s in job_profile.get("preferred_skills", []):
            skill_str = s if isinstance(s, str) else s.get("skill", "")
            canon, cat = normalize_skill(skill_str)
            preferred_reqs.append({"raw_skill": skill_str, "canonical_skill": canon, "category": cat, "importance": 0.7, "evidence": "Preferred skill in job description"})

    # 3. Calculate Required Skill Coverage
    strengths: List[Dict[str, Any]] = []
    gaps: List[Dict[str, Any]] = []
    verification_areas: List[Dict[str, Any]] = []

    req_total_weight = 0.0
    req_matched_weight = 0.0

    for req in required_reqs:
        canon = req["canonical_skill"]
        imp = req["importance"]
        req_total_weight += imp

        if canon in candidate_skill_map:
            cand_info = candidate_skill_map[canon]
            conf = cand_info.get("confidence", 0.9)
            req_matched_weight += (imp * min(1.0, max(0.4, conf)))
            strengths.append({
                "skill": canon,
                "category": req["category"],
                "importance": "required",
                "evidence": cand_info.get("evidence", "Present in candidate profile"),
                "confidence": conf,
            })
            if conf < 0.75:
                verification_areas.append({
                    "skill": canon,
                    "topic": f"Verify {canon} depth and production experience",
                    "reason": "Skill claim is present but has lower confidence evidence.",
                })
        else:
            gaps.append({
                "skill": canon,
                "category": req["category"],
                "importance": "required",
                "reason": f"Required skill '{canon}' not explicitly identified in candidate profile or claims.",
            })

    req_coverage_score = 100.0 if req_total_weight == 0 else (req_matched_weight / req_total_weight) * 100.0

    # 4. Calculate Preferred Skill Coverage
    pref_total_weight = 0.0
    pref_matched_weight = 0.0

    for req in preferred_reqs:
        canon = req["canonical_skill"]
        imp = req["importance"]
        pref_total_weight += imp

        if canon in candidate_skill_map:
            cand_info = candidate_skill_map[canon]
            pref_matched_weight += imp
            strengths.append({
                "skill": canon,
                "category": req["category"],
                "importance": "preferred",
                "evidence": cand_info.get("evidence", "Present in candidate profile"),
                "confidence": cand_info.get("confidence", 0.9),
            })
        else:
            gaps.append({
                "skill": canon,
                "category": req["category"],
                "importance": "preferred",
                "reason": f"Preferred skill '{canon}' not found in candidate profile.",
            })

    pref_coverage_score = 100.0 if pref_total_weight == 0 else (pref_matched_weight / pref_total_weight) * 100.0

    # 5. Experience Fit
    candidate_exp = float(
        candidate_profile.get("experience_years")
        or candidate_profile.get("years_experience")
        or candidate_profile.get("years_of_experience")
        or 0.0
    )
    job_min_exp = float(
        job_profile.get("experience_min")
        or job_profile.get("min_years_experience")
        or 0.0
    )
    job_max_exp = float(
        job_profile.get("experience_max")
        or job_profile.get("max_years_experience")
        or max(job_min_exp + 3.0, 10.0)
    )

    if job_min_exp == 0.0:
        experience_fit_score = 100.0
    elif candidate_exp >= job_min_exp:
        experience_fit_score = 100.0
    else:
        # Scaled proportionally
        experience_fit_score = max(20.0, (candidate_exp / job_min_exp) * 100.0)

    # 6. Project Relevance
    candidate_projects = candidate_profile.get("projects", [])
    if not candidate_projects:
        project_relevance_score = 65.0 if candidate_exp >= 2.0 else 40.0
    else:
        relevant_projects = 0
        all_job_skills = set(r["canonical_skill"].lower() for r in required_reqs + preferred_reqs)
        for p in candidate_projects:
            techs = [normalize_skill(t)[0].lower() for t in p.get("technologies", [])]
            desc = p.get("description", "").lower()
            title = p.get("title", "").lower()
            # If any project technology or description matches a required or preferred job skill
            if any(t in all_job_skills for t in techs) or any(s in desc or s in title for s in all_job_skills):
                relevant_projects += 1
        project_relevance_score = min(100.0, 60.0 + (relevant_projects / max(1, len(candidate_projects))) * 40.0)

    # 7. Seniority Fit
    cand_sen = str(candidate_profile.get("seniority_level") or candidate_profile.get("seniority") or "mid").lower()
    job_sen = str(job_profile.get("seniority") or job_profile.get("seniority_level") or "mid").lower()

    cand_level = SENIORITY_LEVELS.get(cand_sen, 2)
    job_level = SENIORITY_LEVELS.get(job_sen, 2)
    diff = abs(cand_level - job_level)

    if diff == 0:
        seniority_fit_score = 100.0
    elif diff == 1:
        seniority_fit_score = 80.0
    elif diff == 2:
        seniority_fit_score = 60.0
    else:
        seniority_fit_score = 40.0

    # 8. Domain Fit
    cand_domains = set(d.lower() for d in (candidate_profile.get("domains") or candidate_profile.get("technical_domains") or []))
    job_domains = set(d.lower() for d in (job_profile.get("technical_domains") or job_profile.get("domains") or []))

    if not job_domains:
        domain_fit_score = 85.0
    else:
        matched_domains = cand_domains.intersection(job_domains)
        domain_fit_score = min(100.0, max(40.0, (len(matched_domains) / len(job_domains)) * 100.0))

    # 9. Compute Overall Weighted Score
    overall_score = (
        req_coverage_score * scoring_weights.get("required_skills", 0.35)
        + pref_coverage_score * scoring_weights.get("preferred_skills", 0.15)
        + experience_fit_score * scoring_weights.get("experience_fit", 0.15)
        + project_relevance_score * scoring_weights.get("project_relevance", 0.15)
        + seniority_fit_score * scoring_weights.get("seniority_fit", 0.10)
        + domain_fit_score * scoring_weights.get("domain_fit", 0.10)
    )

    # Add high-impact verification claims
    for c in claims_list:
        if c.get("verification_priority") == "high" or c.get("status") == "unverified":
            verification_areas.append({
                "claim": c.get("claim"),
                "category": c.get("category"),
                "probes": c.get("suggested_probes", []),
                "reason": "High-impact or unverified architecture claim requiring live probe.",
            })

    # 10. Generate structured explanation
    explanation = (
        f"Candidate matches {req_coverage_score:.0f}% of required skills and {pref_coverage_score:.0f}% of preferred skills. "
        f"Experience fit is {experience_fit_score:.0f}% ({candidate_exp} yrs vs {job_min_exp}-{job_max_exp} yrs req). "
        f"Identified {len(strengths)} key strengths and {len(gaps)} potential skill gaps to explore."
    )

    return MatchEvaluationResult(
        overall_score=overall_score,
        required_skill_coverage=req_coverage_score,
        preferred_skill_coverage=pref_coverage_score,
        experience_fit=experience_fit_score,
        project_relevance=project_relevance_score,
        seniority_fit=seniority_fit_score,
        domain_fit=domain_fit_score,
        scoring_weights=scoring_weights,
        strengths=strengths,
        gaps=gaps,
        verification_areas=verification_areas,
        explanation=explanation,
    )

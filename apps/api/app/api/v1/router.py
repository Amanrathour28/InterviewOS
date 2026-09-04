from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    availability,
    calendar,
    candidates,
    chat,
    coding,
    health,
    interview_templates,
    interviews,
    invitations,
    jobs,
    notifications,
    organizations,
    problems,
    questions,
    scheduling,
    sessions,
    whiteboard,
    workspaces,
    ai,
    intelligence,
    adaptive_interview,
    evaluation,
    analytics,
)

api_router = APIRouter()

api_router.include_router(health.router, tags=["System Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication & Profile"])
api_router.include_router(organizations.router, prefix="/organizations", tags=["Organizations & Tenants"])
api_router.include_router(workspaces.router, prefix="/workspaces", tags=["Workspaces"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["Jobs"])
api_router.include_router(candidates.router, prefix="/candidates", tags=["Candidates"])
api_router.include_router(questions.router, prefix="/questions", tags=["Question Bank"])
api_router.include_router(interview_templates.router, prefix="/interview-templates", tags=["Interview Templates"])
api_router.include_router(interviews.router, prefix="/interviews", tags=["Interviews"])
api_router.include_router(scheduling.router, prefix="/interviews", tags=["Interview Scheduling"])
api_router.include_router(availability.router, prefix="/availability", tags=["Availability"])
api_router.include_router(invitations.router, tags=["Invitations"])
api_router.include_router(calendar.router, prefix="/calendar", tags=["Calendar"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(sessions.router, tags=["Live Interview Sessions"])
api_router.include_router(chat.router, tags=["Live Room Chat & Code Snippets"])
api_router.include_router(coding.router, tags=["Collaborative Coding & Sandbox Execution"])
api_router.include_router(problems.router, tags=["Problem Library & Coding Assessments"])
api_router.include_router(whiteboard.router, tags=["Collaborative Whiteboard & System Design"])
api_router.include_router(ai.router, tags=["AI Copilot & Gateway"])
api_router.include_router(intelligence.router, prefix="/intelligence", tags=["Intelligence & Planning"])
api_router.include_router(adaptive_interview.router, tags=["Adaptive Interviewer"])
api_router.include_router(evaluation.router, tags=["Interview Evaluation"])
api_router.include_router(analytics.router, tags=["Analytics & Decision Intelligence"])

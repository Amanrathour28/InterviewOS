# Multi-Agent Intelligence System

## Agent Architecture

InterviewOS organizes intelligence tasks into discrete, single-responsibility agents under `apps/ai/app/agents/`. Each agent conforms to the `BaseAgent` contract:

```python
class BaseAgent(ABC):
    name: str
    description: str

    @abstractmethod
    async def run(self, context: AgentContext) -> AgentResult:
        ...
```

## Agent Catalog

### 1. Interview Orchestrator Agent (`orchestrator.py`)
- **Role**: State and dispatch coordinator.
- **Responsibilities**: Inspects incoming request task types, verifies required dependencies, initiates context building, and directs execution to the target agent node within the LangGraph workflow.

### 2. Question Generation Agent (`question_agent.py`)
- **Role**: Stage-aware dynamic technical inquiry.
- **Inputs**: Current stage, topics already covered, candidate resume themes, job seniority requirements, difficulty setting.
- **Outputs**:
  - `question_text`: Clear, non-trivial prompt.
  - `question_type`: Technical, behavioral, system design, or problem solving.
  - `rubric`: 4-tier rubric (Exemplary, Competent, Developing, Unsatisfactory) for deterministic grading.
  - `follow_up_hooks`: Nuances to probe if candidate provides high-level answers.
  - `expected_key_points`: Concrete concepts expected from a strong candidate.

### 3. Follow-Up Suggestion Agent (`followup_agent.py`)
- **Role**: Live response evaluation and drill-down advisor.
- **Inputs**: Question asked, candidate's transcript/notes, remaining session time, target skill.
- **Outputs**:
  - `primary_follow_up`: Immediate next question.
  - `alternative_angles`: Strategic secondary angles (edge cases, scaling, internals).
  - `purpose`: Rationale explaining what interviewer is looking to verify.

### 4. Resume Intelligence Agent (`resume_agent.py`)
- **Role**: Document claims verification & experience probing.
- **Inputs**: Extracted resume text or candidate profile.
- **Outputs**:
  - `depth_verification_questions`: Targeted questions to confirm hands-on ownership vs. team attribution.
  - `project_deep_dives`: Scenario-based challenge probes.
  - `skill_gaps_or_red_flags`: Missing prerequisites for the role.

### 5. Coding Analysis Agent (`coding_agent.py`)
- **Role**: Algorithmic & implementation analysis.
- **Rule**: Docker sandbox test execution results are 100% authoritative and are never overridden by LLM speculation.
- **Outputs**:
  - Time & space complexity assessment.
  - Unhandled edge cases (null inputs, overflows, recursion depth).
  - Code smell detections (variable naming, memory leaks, unidiomatic patterns).
  - Progressive hint ladder (3 tiers of non-spoiler hints).

### 6. System Design Agent (`system_design_agent.py`)
- **Role**: Distributed architecture evaluation.
- **Inputs**: Whiteboard canvas stencils/elements, candidate verbal notes, problem constraints.
- **Outputs**:
  - Architecture pattern classification (event-driven, microservices, lambda).
  - Single Points of Failure (SPOF) identification.
  - Scalability and partition tolerance risks (CAP theorem bottlenecks).
  - Targeted critique inquiries for candidate.

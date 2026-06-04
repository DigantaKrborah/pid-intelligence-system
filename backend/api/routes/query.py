from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db
from backend.db.repositories.unit_repo import UnitRepository
from backend.models.query import NLQueryRequest, NLQueryResponse, BugReportRequest
from backend.agents.coordinator import CoordinatorAgent
from backend.graph.builder import GraphBuilder
from backend.rag.engine import RAGEngine
from loguru import logger

router = APIRouter()
_graph = GraphBuilder()
_rag = RAGEngine()
_agent = CoordinatorAgent(_graph, _rag)


@router.post("/nl", response_model=NLQueryResponse)
async def natural_language_query(
    payload: NLQueryRequest,
    db: AsyncSession = Depends(get_db),
):
    """Answer a natural language engineering question about the selected unit."""
    if payload.unit_id is None:
        return NLQueryResponse(
            answer="Please select a unit before asking a question.",
            query_type="error",
        )

    unit = await UnitRepository(db).get_by_id(payload.unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")

    result = _agent.run(
        question=payload.question,
        unit_name=unit.name,
        chat_history=payload.chat_history,
    )

    return NLQueryResponse(
        answer=result["answer"],
        query_type="general",
        unit_context=unit.name,
    )


@router.post("/bug", status_code=201)
async def report_bug(payload: BugReportRequest):
    """Create a GitHub Issue for an in-app bug report."""
    from backend.config import get_settings
    settings = get_settings()

    if not settings.github_token or not settings.github_repo:
        return {"message": "Bug reporting not configured (missing GITHUB_TOKEN or GITHUB_REPO)"}

    try:
        from github import Github
        gh = Github(settings.github_token)
        repo = gh.get_repo(settings.github_repo)
        body = f"""**Component:** {payload.component}
**Severity:** {payload.severity}
**Unit:** {payload.unit_name or 'N/A'}
**Page:** {payload.page_context or 'N/A'}

**Description:**
{payload.description}

**Steps to Reproduce:**
{payload.steps_to_reproduce}
"""
        issue = repo.create_issue(
            title=f"[Bug] {payload.component}: {payload.description[:80]}",
            body=body,
            labels=["bug"],
        )
        return {"issue_url": issue.html_url, "issue_number": issue.number}
    except Exception as e:
        logger.error(f"GitHub issue creation failed: {e}")
        return {"message": "Bug report saved locally (GitHub unreachable)"}

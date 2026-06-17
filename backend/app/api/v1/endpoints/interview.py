"""AI-powered mock interview session endpoints."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.v1.deps import CurrentUser, DBSession, Pagination
from app.core.logging import get_logger
from app.db.models import InterviewSession, Job
from app.db.schemas import (
    InterviewAnswerRequest,
    InterviewFeedback,
    InterviewQuestionResponse,
    InterviewSessionResponse,
    InterviewStartRequest,
    MessageResponse,
    PaginatedResponse,
)

router = APIRouter(prefix="/interview", tags=["Interview"])
logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Static question banks (production version uses AI generation)
# ---------------------------------------------------------------------------

_BEHAVIORAL_QUESTIONS = [
    {
        "id": "b1",
        "question": "Tell me about a time you faced a significant challenge at work and how you overcame it.",
        "category": "behavioral",
        "difficulty": "medium",
        "follow_up_hints": ["What was the outcome?", "What did you learn?"],
    },
    {
        "id": "b2",
        "question": "Describe a situation where you had to work with a difficult team member.",
        "category": "behavioral",
        "difficulty": "medium",
        "follow_up_hints": ["What approach did you take?", "How was the conflict resolved?"],
    },
    {
        "id": "b3",
        "question": "Give an example of a goal you set and how you achieved it.",
        "category": "behavioral",
        "difficulty": "easy",
        "follow_up_hints": ["What metrics did you track?"],
    },
    {
        "id": "b4",
        "question": "Tell me about a time you had to make a decision with incomplete information.",
        "category": "behavioral",
        "difficulty": "hard",
        "follow_up_hints": ["What were the trade-offs?"],
    },
    {
        "id": "b5",
        "question": "Describe a situation where you demonstrated leadership without formal authority.",
        "category": "behavioral",
        "difficulty": "hard",
        "follow_up_hints": ["Who was impacted?", "What was the outcome?"],
    },
]

_TECHNICAL_QUESTIONS = [
    {
        "id": "t1",
        "question": "Explain the difference between a process and a thread.",
        "category": "technical",
        "difficulty": "medium",
        "follow_up_hints": ["How does this affect concurrency?"],
    },
    {
        "id": "t2",
        "question": "What is the time complexity of quicksort in the average and worst case?",
        "category": "technical",
        "difficulty": "medium",
        "follow_up_hints": ["When would you choose merge sort instead?"],
    },
    {
        "id": "t3",
        "question": "Design a URL shortening service like bit.ly.",
        "category": "system_design",
        "difficulty": "hard",
        "follow_up_hints": ["Consider scale: 1M requests/day.", "How would you handle collisions?"],
    },
    {
        "id": "t4",
        "question": "What are the SOLID principles? Give an example of each.",
        "category": "technical",
        "difficulty": "medium",
        "follow_up_hints": ["Which principle do you find hardest to apply?"],
    },
    {
        "id": "t5",
        "question": "How does garbage collection work in Python?",
        "category": "technical",
        "difficulty": "medium",
        "follow_up_hints": ["What is reference counting?", "What are weak references?"],
    },
]

_QUESTION_BANKS: dict[str, list[dict]] = {
    "behavioral": _BEHAVIORAL_QUESTIONS,
    "technical": _TECHNICAL_QUESTIONS,
    "system_design": [q for q in _TECHNICAL_QUESTIONS if q["category"] == "system_design"],
    "hr": _BEHAVIORAL_QUESTIONS[:3],
}


async def _get_session_or_404(
    session_id: uuid.UUID, user_id: uuid.UUID, db
) -> InterviewSession:
    result = await db.execute(
        select(InterviewSession).where(
            InterviewSession.id == session_id,
            InterviewSession.user_id == user_id,
        )
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview session not found",
        )
    return session


@router.post(
    "/session/start",
    response_model=InterviewSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new mock interview session",
)
async def start_session(
    request: InterviewStartRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> InterviewSessionResponse:
    """Initialise a new mock interview session and queue the first questions."""
    if request.job_id:
        job_result = await db.execute(select(Job).where(Job.id == request.job_id))
        if job_result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
            )

    bank = _QUESTION_BANKS.get(request.interview_type, _BEHAVIORAL_QUESTIONS)
    difficulty_filter = [
        q for q in bank
        if q["difficulty"] == request.difficulty or request.difficulty == "all"
    ]
    if not difficulty_filter:
        difficulty_filter = bank

    selected = difficulty_filter[: request.num_questions]

    session_data = {
        "interview_type": request.interview_type,
        "difficulty": request.difficulty,
        "questions": selected,
        "answers": {},
        "current_question_index": 0,
        "status": "active",
        "started_at": datetime.now(tz=timezone.utc).isoformat(),
    }

    session = InterviewSession(
        user_id=current_user.id,
        job_id=request.job_id,
        session_data=session_data,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    logger.info(
        "Interview session started",
        extra={
            "user_id": str(current_user.id),
            "session_id": str(session.id),
            "type": request.interview_type,
        },
    )
    return InterviewSessionResponse.model_validate(session)


@router.get(
    "/sessions/",
    response_model=PaginatedResponse[InterviewSessionResponse],
    summary="List interview sessions for the current user",
)
async def list_sessions(
    current_user: CurrentUser,
    db: DBSession,
    pagination: Pagination,
) -> PaginatedResponse[InterviewSessionResponse]:
    """Return all interview sessions for the current user."""
    from sqlalchemy import func

    query = select(InterviewSession).where(
        InterviewSession.user_id == current_user.id
    )
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar_one()

    result = await db.execute(
        query.order_by(InterviewSession.created_at.desc())
        .offset(pagination.skip)
        .limit(pagination.limit)
    )
    sessions = result.scalars().all()

    return PaginatedResponse.create(
        items=[InterviewSessionResponse.model_validate(s) for s in sessions],
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
    )


@router.get(
    "/sessions/{session_id}",
    response_model=InterviewSessionResponse,
    summary="Get a specific interview session",
)
async def get_session(
    session_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> InterviewSessionResponse:
    """Return details and current state of an interview session."""
    session = await _get_session_or_404(session_id, current_user.id, db)
    return InterviewSessionResponse.model_validate(session)


@router.post(
    "/sessions/{session_id}/question",
    response_model=InterviewQuestionResponse,
    summary="Get the next question in a session",
)
async def get_next_question(
    session_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> InterviewQuestionResponse:
    """Advance to and return the next interview question."""
    session = await _get_session_or_404(session_id, current_user.id, db)
    data = session.session_data or {}

    if data.get("status") == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This interview session has already been completed",
        )

    questions = data.get("questions", [])
    index = data.get("current_question_index", 0)

    if index >= len(questions):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No more questions available. Complete the session to get feedback.",
        )

    question = questions[index]
    return InterviewQuestionResponse(
        question_id=question["id"],
        question=question["question"],
        category=question["category"],
        difficulty=question["difficulty"],
        follow_up_hints=question.get("follow_up_hints"),
    )


@router.post(
    "/sessions/{session_id}/answer",
    response_model=MessageResponse,
    summary="Submit an answer to the current question",
)
async def submit_answer(
    session_id: uuid.UUID,
    answer_request: InterviewAnswerRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> MessageResponse:
    """Record the user's answer and advance the question pointer."""
    session = await _get_session_or_404(session_id, current_user.id, db)
    data = session.session_data or {}

    if data.get("status") == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session is already completed",
        )

    answers = data.get("answers", {})
    answers[answer_request.question_id] = {
        "answer": answer_request.answer,
        "submitted_at": datetime.now(tz=timezone.utc).isoformat(),
    }
    data["answers"] = answers

    questions = data.get("questions", [])
    index = data.get("current_question_index", 0) + 1
    data["current_question_index"] = index

    if index >= len(questions):
        data["status"] = "completed"
        data["completed_at"] = datetime.now(tz=timezone.utc).isoformat()

    session.session_data = data
    await db.commit()

    return MessageResponse(
        message=(
            "Answer recorded. Session complete — retrieve feedback!"
            if data["status"] == "completed"
            else f"Answer recorded. Question {index + 1} of {len(questions)} up next."
        )
    )


@router.get(
    "/sessions/{session_id}/feedback",
    response_model=InterviewFeedback,
    summary="Get detailed feedback for a completed session",
)
async def get_session_feedback(
    session_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> InterviewFeedback:
    """Return AI-evaluated feedback once the interview session is complete."""
    session = await _get_session_or_404(session_id, current_user.id, db)
    data = session.session_data or {}

    if data.get("status") != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session must be completed before feedback is available",
        )

    questions = data.get("questions", [])
    answers = data.get("answers", {})

    # Calculate a basic score based on answer completeness
    answered = len(answers)
    total_q = len(questions)
    completeness_score = (answered / max(total_q, 1)) * 100

    # Simple heuristic scoring per answer
    category_scores: dict[str, float] = {}
    detailed_feedback: list[dict] = []

    for q in questions:
        qid = q["id"]
        user_ans = answers.get(qid, {}).get("answer", "")
        word_count = len(user_ans.split())

        # Score heuristics: length, presence of specific words
        answer_score = min(100.0, (word_count / 80) * 100)
        if "because" in user_ans.lower() or "result" in user_ans.lower():
            answer_score = min(100.0, answer_score + 10)
        if word_count < 20:
            answer_score = max(0.0, answer_score - 20)

        cat = q.get("category", "general")
        if cat not in category_scores:
            category_scores[cat] = []  # type: ignore
        category_scores[cat].append(answer_score)  # type: ignore

        detailed_feedback.append(
            {
                "question_id": qid,
                "question": q["question"],
                "your_answer": user_ans[:500] if user_ans else "(no answer)",
                "score": round(answer_score, 1),
                "feedback": (
                    "Good answer with clear reasoning."
                    if answer_score >= 70
                    else "Consider expanding your answer with more specific examples."
                ),
            }
        )

    # Average category scores
    averaged_cats = {
        cat: round(sum(scores) / len(scores), 1)  # type: ignore
        for cat, scores in category_scores.items()
    }

    overall = round(
        sum(averaged_cats.values()) / max(len(averaged_cats), 1) * 0.7
        + completeness_score * 0.3,
        1,
    )

    # Save score to session
    session.score = overall
    session.feedback = (
        f"Overall score: {overall}/100. "
        f"Answered {answered}/{total_q} questions."
    )
    await db.commit()

    return InterviewFeedback(
        session_id=session.id,
        overall_score=overall,
        category_scores=averaged_cats,
        strengths=[
            "Engaged with all questions"
            if completeness_score == 100
            else "Completed most questions",
            "Demonstrated effort in responses",
        ],
        areas_for_improvement=[
            "Use the STAR method (Situation, Task, Action, Result) for behavioral questions",
            "Include quantifiable outcomes where possible",
            "Practice concise yet complete answers (aim for 100-200 words per answer)",
        ],
        detailed_feedback=detailed_feedback,
        recommended_resources=[
            "https://www.themuse.com/advice/star-interview-method",
            "https://leetcode.com (for technical prep)",
            "https://www.pramp.com (live mock interviews)",
        ],
    )

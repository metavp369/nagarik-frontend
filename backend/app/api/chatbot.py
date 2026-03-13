"""
Nischint AI Chatbot — Public-facing conversational AI for the marketing website.
Handles platform questions, safety demos, and lead capture.
Uses Emergent LLM Key for GPT-5.2 responses.
"""
import logging
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from pydantic import BaseModel, EmailStr
from typing import Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.api.deps import get_db_session
from app.core.rate_limiter import limiter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chatbot", tags=["AI Chatbot"])

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

def _get_llm_key():
    """Get Emergent LLM key from env or settings."""
    key = os.environ.get("EMERGENT_LLM_KEY", "")
    if not key:
        try:
            from app.core.config import settings
            key = settings.emergent_llm_key
        except Exception:
            pass
    return key

SYSTEM_PROMPT = """You are Nischint AI, the official assistant for the Nischint AI Safety Infrastructure platform.

About Nischint:
- Nischint is an AI Safety Operating System that transforms real-time safety signals, mobility intelligence, and predictive AI into a unified safety network.
- The vision is to build India's AI Safety Network, enabling predictive risk detection and coordinated response across society.
- The platform has 4 layers: User App (mobile safety interface) → AI Safety Brain (behavioral analysis, anomaly detection, predictive risk) → Command Center (real-time operational dashboard) → City Intelligence Layer (aggregated safety insights).
- 8 AI engines: Behavior Pattern Engine, Digital Twin Engine, Risk Prediction Engine, Incident Narrative AI, Replay Intelligence Engine, Location Risk Intelligence, Voice AI Detection, Environmental AI.
- Target sectors: School Safety, University Campuses, Corporate Safety, Urban Safety Networks, Smart Cities, Public Safety Infrastructure.
- Currently running pilot programs with schools, universities, corporate campuses, and smart city initiatives.

Key capabilities:
- Real-time safety monitoring with <15s average response time
- Shake-to-SOS emergency trigger
- Guardian network with live location tracking
- AI-powered risk prediction and behavioral anomaly detection
- Incident replay and narrative generation
- Geofence monitoring and route deviation alerts
- Voice distress detection
- Command center for institutional deployment

Contact information:
- General: hello@nischint.app
- Partnerships: partners@nischint.app
- Support: support@nischint.app
- Press: press@nischint.app
- Security: security@nischint.app

Website pages:
- Homepage: /
- Investors: /investors
- Pilot signup: /pilot
- Live telemetry: /telemetry

Instructions:
- Be concise, professional, and helpful.
- Keep responses under 150 words.
- When relevant, suggest visiting specific pages or contacting via email.
- If someone is interested in a pilot or demo, guide them to /pilot or suggest emailing hello@nischint.app.
- Never reveal internal technical details, API keys, or sensitive information.
- Use a confident, enterprise tone matching Palantir-style communication.
"""

DEMO_STEPS = [
    {"delay": 0, "message": "Initializing safety monitoring session...", "type": "system"},
    {"delay": 2, "message": "Session active. Monitoring behavioral patterns, location signals, and environmental data.", "type": "system"},
    {"delay": 3, "message": "ANOMALY DETECTED: Unusual route deviation identified. Risk score: 0.34 → 0.58", "type": "warning"},
    {"delay": 3, "message": "AI Safety Brain analyzing behavioral pattern... Extended stop detected in unfamiliar zone.", "type": "warning"},
    {"delay": 2, "message": "ALERT: Risk score escalating. 0.58 → 0.78. Geofence boundary approached.", "type": "alert"},
    {"delay": 2, "message": "Guardian notification dispatched. Response window: 30 seconds.", "type": "system"},
    {"delay": 2, "message": "Command Center alert triggered. Patrol unit notified for Zone Delta.", "type": "alert"},
    {"delay": 3, "message": "Guardian response confirmed. Location verified. Safer route generated.", "type": "success"},
    {"delay": 2, "message": "Risk score normalizing. 0.78 → 0.31. Behavioral pattern stabilized.", "type": "success"},
    {"delay": 2, "message": "Session completed safely. Incident replay generated. AI narrative logged.", "type": "success"},
    {"delay": 1, "message": "This is how Nischint protects in real-time — from detection to resolution in under 30 seconds. Would you like to request a pilot deployment for your institution?", "type": "info"},
]


class ChatMessage(BaseModel):
    session_id: str
    message: str


class LeadCaptureRequest(BaseModel):
    session_id: str
    name: str
    institution: str
    email: str
    city: Optional[str] = None


@router.post("/message")
@limiter.limit("30/minute")
async def chat_message(request: Request, body: ChatMessage):
    """Process a chat message and return AI response."""
    user_msg = body.message.strip().lower()

    # Handle demo trigger
    if "demo" in user_msg and ("run" in user_msg or "safety" in user_msg or "live" in user_msg or "show" in user_msg or "start" in user_msg):
        return {
            "type": "demo",
            "steps": DEMO_STEPS,
            "session_id": body.session_id,
        }

    # Handle city simulation trigger
    if "city" in user_msg and ("simulation" in user_msg or "simulate" in user_msg or "grid" in user_msg):
        return {
            "type": "text",
            "message": "You can watch the City Safety Simulation on our homepage. It demonstrates how Nischint detects, propagates, and resolves safety incidents across an entire city network.\n\nScroll to the 'AI Safety Network Simulation' section on the homepage, or visit /",
            "session_id": body.session_id,
        }

    # Handle lead capture trigger
    if any(kw in user_msg for kw in ["schedule", "pilot", "deploy", "sign up", "signup", "contact sales"]):
        return {
            "type": "lead_prompt",
            "message": "I'd be happy to help you get started. You can:\n\n1. Fill out our pilot request form at /pilot\n2. Email us directly at hello@nischint.app\n3. Share your details here and we'll reach out within 48 hours.\n\nWould you like to share your contact information now?",
            "session_id": body.session_id,
        }

    # Use LLM for general questions
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        api_key = _get_llm_key()
        if not api_key:
            raise ValueError("EMERGENT_LLM_KEY not configured")
        chat = LlmChat(
            api_key=api_key,
            session_id=f"chatbot-{body.session_id}",
            system_message=SYSTEM_PROMPT,
        ).with_model("openai", "gpt-5.2")
        response = await chat.send_message(UserMessage(text=body.message))
        return {
            "type": "text",
            "message": response.strip() if isinstance(response, str) else str(response),
            "session_id": body.session_id,
        }
    except Exception as e:
        logger.error(f"Chatbot LLM error: {e}")
        return {
            "type": "text",
            "message": "I can help you learn about Nischint's AI Safety Infrastructure. You can ask about our platform capabilities, school safety solutions, corporate safety, or request a pilot deployment. For immediate assistance, email hello@nischint.app.",
            "session_id": body.session_id,
        }


@router.get("/demo-steps")
async def get_demo_steps():
    """Return the safety demo sequence."""
    return {"steps": DEMO_STEPS}


@router.post("/lead")
@limiter.limit("10/hour")
async def capture_lead(
    request: Request,
    body: LeadCaptureRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """Capture a lead from the chatbot conversation."""
    try:
        # pilot_leads uses SERIAL id (auto-increment), so don't specify id
        await session.execute(
            text("""
                INSERT INTO pilot_leads (institution_name, contact_person, email, city, created_at)
                VALUES (:inst, :contact, :email, :city, :now)
            """),
            {
                "inst": body.institution,
                "contact": body.name,
                "email": body.email,
                "city": body.city or "",
                "now": datetime.now(timezone.utc),
            },
        )
        await session.commit()

        # Send email notification
        try:
            from app.services.email_service import send_email
            html = f"""
            <h2>New Lead from Nischint AI Chatbot</h2>
            <p><b>Name:</b> {body.name}</p>
            <p><b>Institution:</b> {body.institution}</p>
            <p><b>Email:</b> {body.email}</p>
            <p><b>City:</b> {body.city or 'Not provided'}</p>
            <p><b>Source:</b> AI Chatbot</p>
            <p><b>Session:</b> {body.session_id}</p>
            """
            send_email("partners@nischint.app", "New Chatbot Lead — Nischint", html)
            send_email("hello@nischint.app", "New Chatbot Lead — Nischint", html)
        except Exception as email_err:
            logger.warning(f"Lead email notification failed: {email_err}")

        return {
            "type": "text",
            "message": "Thank you! Your information has been received. Our team will contact you within 48 hours to discuss a pilot deployment. In the meantime, explore our live telemetry at /telemetry.",
            "session_id": body.session_id,
        }
    except Exception as e:
        logger.error(f"Lead capture error: {e}")
        return {
            "type": "text",
            "message": "Thank you for your interest. Please email hello@nischint.app and we'll get back to you within 48 hours.",
            "session_id": body.session_id,
        }

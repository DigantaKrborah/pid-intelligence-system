"""
settings.py — LLM provider settings
GET  /api/settings/llm/models  → static list of available models per provider
GET  /api/settings/llm         → current active LLM config (api_key_hint only)
POST /api/settings/llm         → save LLM config — admin only

The full API key IS stored in the api_key column so that extraction.py background tasks
can retrieve it.  Only api_key_hint (last 4 chars) is returned to the frontend; the full
key is never sent over the API.

Route order: /llm/models must come before /llm so FastAPI does not treat
"models" as a path segment of a different route.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin

router = APIRouter()


# ── Static model catalogue (update this list when new models release) ──────────

_AVAILABLE_MODELS = {
    "claude": [
        {"id": "claude-opus-4-6",   "name": "Claude Opus 4.6 (Best accuracy)"},
        {"id": "claude-sonnet-4-6", "name": "Claude Sonnet 4.6 (Balanced)"},
        {"id": "claude-haiku-4-5-20251001", "name": "Claude Haiku 4.5 (Fastest)"},
    ],
    "openai": [
        {"id": "gpt-4o",      "name": "GPT-4o (Best for vision)"},
        {"id": "gpt-4o-mini", "name": "GPT-4o Mini (Faster, lower cost)"},
    ],
    "gemini": [
        {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash (Fast, recommended)"},
        {"id": "gemini-2.5-pro",   "name": "Gemini 2.5 Pro (Best accuracy)"},
        {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash (Stable)"},
        {"id": "gemini-2.0-flash-lite", "name": "Gemini 2.0 Flash Lite (Fastest)"},
    ],
}

_VALID_PROVIDERS = set(_AVAILABLE_MODELS.keys())


# ── Request body for POST /llm ─────────────────────────────────────────────────

class LLMSettingsRequest(BaseModel):
    """
    Body for saving LLM settings.
    api_key is optional — omit it to keep the existing key hint already on file.
    When provided, only the last 4 characters are stored as api_key_hint.
    """
    provider:   str            # claude | openai | gemini
    model_name: str            # e.g. claude-sonnet-4-6
    api_key:    Optional[str] = None  # full key — only last 4 chars are saved


# ── GET /api/settings/llm/models ──────────────────────────────────────────────
# Defined FIRST to avoid any path-matching ambiguity with /llm

@router.get("/llm/models")
def get_available_models(_=Depends(get_current_user)):
    """
    Return the catalogue of LLM providers and their available models.
    Any logged-in user can view this — no admin required.
    """
    return _AVAILABLE_MODELS


# ── GET /api/settings/llm ─────────────────────────────────────────────────────

@router.get("/llm")
def get_llm_settings(
    db=Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Return the currently active LLM configuration for this organisation.
    Returns { configured: false } if no settings have been saved yet.
    """
    org_id = str(current_user["org_id"])

    with db.cursor() as cur:
        cur.execute(
            """
            SELECT
                id::text, provider, model_name,
                api_key_hint, is_active, updated_at,
                updated_by::text AS updated_by
            FROM llm_settings
            WHERE org_id = %s AND is_active = true
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (org_id,),
        )
        row = cur.fetchone()

    if row is None:
        return {
            "configured":   False,
            "provider":     None,
            "model_name":   None,
            "api_key_hint": None,
            "updated_at":   None,
        }

    result = dict(row)
    result["configured"] = True
    return result


# ── POST /api/settings/llm ────────────────────────────────────────────────────

@router.post("/llm")
def save_llm_settings(
    payload: LLMSettingsRequest,
    db=Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """
    Save (or replace) the LLM configuration for this organisation.
    Admin only — regular users cannot change the AI provider.

    Security:
      - The full api_key is NEVER written to the database.
      - Only api_key[-4:] is stored as a display hint.
      - All previous active settings are deactivated before inserting the new row.
    """
    # 1. Validate provider
    if payload.provider not in _VALID_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown provider '{payload.provider}'. "
                   f"Allowed: {', '.join(sorted(_VALID_PROVIDERS))}",
        )

    # 2. Validate model_name is in our catalogue for that provider
    valid_model_ids = {m["id"] for m in _AVAILABLE_MODELS[payload.provider]}
    if payload.model_name not in valid_model_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"model_name '{payload.model_name}' is not valid for provider "
                   f"'{payload.provider}'. "
                   f"Valid models: {sorted(valid_model_ids)}",
        )

    org_id  = str(current_user["org_id"])
    user_id = str(current_user["id"])

    # 3. Determine the key to store.
    #    If a new key is provided → use it.
    #    If no key provided → keep the existing key on file.
    new_key = (payload.api_key or "").strip()
    if new_key:
        store_key  = new_key
        store_hint = new_key[-4:]
    else:
        with db.cursor() as cur:
            cur.execute(
                """
                SELECT api_key, api_key_hint FROM llm_settings
                WHERE org_id = %s AND is_active = true
                ORDER BY updated_at DESC LIMIT 1
                """,
                (org_id,),
            )
            existing = cur.fetchone()

        if existing is None or not existing["api_key"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No API key is on file yet. Please provide an API key.",
            )
        store_key  = existing["api_key"]
        store_hint = existing["api_key_hint"]

    # 4. Deactivate all existing settings for this org
    with db.cursor() as cur:
        cur.execute(
            "UPDATE llm_settings SET is_active = false WHERE org_id = %s",
            (org_id,),
        )

    # 5. Insert the new active settings row (full key stored for extraction use)
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO llm_settings
                (org_id, provider, model_name, api_key, api_key_hint, is_active, updated_by)
            VALUES (%s, %s, %s, %s, %s, true, %s)
            RETURNING id::text, provider, model_name, api_key_hint, updated_at
            """,
            (org_id, payload.provider, payload.model_name, store_key, store_hint, user_id),
        )
        saved = cur.fetchone()

    return {
        "provider":     saved["provider"],
        "model_name":   saved["model_name"],
        "api_key_hint": saved["api_key_hint"],
        "updated_at":   saved["updated_at"],
        "message":      "LLM settings saved successfully.",
    }

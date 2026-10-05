"""Schemas for DeepSeek automations (lead score, documents, email copy)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AutomationsStatusOut(BaseModel):
    deepseek_configured: bool
    model: str
    user_id: str
    user_name: str


class LeadPayloadIn(BaseModel):
    payload: Any = Field(description="Raw form JSON, text, or structured lead fields")


class DocumentIn(BaseModel):
    template: str
    variables: dict[str, Any] = Field(default_factory=dict)
    doc_type: str = "proposal"


class EmailCopyIn(BaseModel):
    kind: str
    context: dict[str, Any] = Field(default_factory=dict)


class AutomationRunOut(BaseModel):
    id: UUID
    user_id: UUID
    kind: str
    payload: dict = Field(default_factory=dict)
    result: dict = Field(default_factory=dict)
    created_at: datetime

    model_config = {"from_attributes": True}

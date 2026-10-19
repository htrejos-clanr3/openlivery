"""Deterministic lead qualification against the client's ideal customer profile.

No LLM call: qualification runs in bulk and must be cheap, stable and testable.
Every run writes `leads.score` and appends a `lead_activities` row of kind
`qualification`, so the reasoning stays visible in the lead timeline.
"""

from __future__ import annotations

import unicodedata
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Contact, IdealCustomerProfile, Lead, LeadActivity, now_utc

MAX_SCORE = 100
SECTOR_POINTS = 30
CITY_POINTS = 20
SIZE_POINTS = 15
KEYWORD_POINTS = 5
KEYWORD_CAP = 20
EMAIL_POINTS = 10
PHONE_POINTS = 5
DEFAULT_HOT_MIN = 75
DEFAULT_WARM_MIN = 45
ACTIVITY_KIND = "qualification"
EMPLOYEE_KEYS = ("employees", "employee_count", "headcount", "size", "company_size")


def normalize(value: str | None) -> str:
    """Lowercase and strip accents so "Bogotá" matches "bogota"."""
    text = unicodedata.normalize("NFKD", (value or "").strip().lower())
    return "".join(char for char in text if not unicodedata.combining(char))


def _clean_list(values) -> list[str]:
    cleaned: list[str] = []
    for value in values or []:
        text = str(value).strip()
        if text and text not in cleaned:
            cleaned.append(text)
    return cleaned


def _extra(contact: Contact | None) -> dict[str, Any]:
    return contact.extra if contact and isinstance(contact.extra, dict) else {}


def _haystack(lead: Lead, contact: Contact | None) -> str:
    extra = _extra(contact)
    parts: list[str] = [
        contact.name if contact else "",
        contact.company if contact else "",
        contact.email if contact else "",
        lead.notes,
        " ".join(str(tag) for tag in (lead.tags or [])),
        " ".join(str(value) for value in extra.values() if isinstance(value, (str, int, float))),
    ]
    return normalize(" ".join(str(part) for part in parts if part))


def _employees(contact: Contact | None) -> int | None:
    extra = _extra(contact)
    for key in EMPLOYEE_KEYS:
        if key not in extra:
            continue
        raw = str(extra[key]).replace(",", "").replace(".", "").strip()
        try:
            number = int(float(raw))
        except (TypeError, ValueError):
            continue
        if number > 0:
            return number
    return None


def _hits(terms: list[str], haystack: str) -> list[str]:
    return [term for term in terms if normalize(term) and normalize(term) in haystack]


@dataclass
class Qualification:
    score: int
    band: str
    reasons: list[str] = field(default_factory=list)
    matched: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {"score": self.score, "band": self.band, "reasons": list(self.reasons), "matched": dict(self.matched)}

    def message(self) -> str:
        detail = " ".join(self.reasons) or "No signals matched."
        return f"Qualified {self.score}/100 ({self.band}). {detail}"


def load_icp(db: Session, *, client_id: uuid.UUID, agency_id: uuid.UUID) -> IdealCustomerProfile | None:
    return db.scalar(
        select(IdealCustomerProfile).where(
            IdealCustomerProfile.client_id == client_id,
            IdealCustomerProfile.agency_id == agency_id,
        )
    )


def score_lead(*, lead: Lead, contact: Contact | None, icp: IdealCustomerProfile) -> Qualification:
    haystack = _haystack(lead, contact)
    reasons: list[str] = []
    matched: dict[str, Any] = {}

    disqualifier = next((item for item in _clean_list(icp.disqualifiers) if normalize(item) in haystack), None)
    if disqualifier:
        return Qualification(
            score=0,
            band="disqualified",
            reasons=[f'Matches disqualifier "{disqualifier}".'],
            matched={"disqualifier": disqualifier},
        )

    total = SECTOR_POINTS if _clean_list(icp.sectors) and _hits(_clean_list(icp.sectors), haystack) else 0
    sectors = _hits(_clean_list(icp.sectors), haystack)
    if sectors:
        matched["sectors"] = sectors
        reasons.append(f'Sector matched: {", ".join(sectors)}.')
    elif _clean_list(icp.sectors):
        reasons.append("Sector did not match the profile.")

    cities = _hits(_clean_list(icp.cities), haystack)
    if cities:
        total += CITY_POINTS
        matched["cities"] = cities
        reasons.append(f'City matched: {", ".join(cities)}.')
    elif _clean_list(icp.cities):
        reasons.append("City did not match the profile.")

    if icp.size_min is not None or icp.size_max is not None:
        employees = _employees(contact)
        lower = icp.size_min if icp.size_min is not None else 0
        upper = icp.size_max if icp.size_max is not None else 10**9
        if employees is not None and lower <= employees <= upper:
            total += SIZE_POINTS
            matched["employees"] = employees
            reasons.append(f"Size matched: {employees} employees.")
        elif employees is not None:
            reasons.append(f"Size {employees} is outside {lower}-{upper}.")

    keywords = _hits(_clean_list(icp.keywords), haystack)
    if keywords:
        points = min(len(keywords) * KEYWORD_POINTS, KEYWORD_CAP)
        total += points
        matched["keywords"] = keywords
        reasons.append(f'Keywords matched: {", ".join(keywords)} (+{points}).')

    if contact and contact.email:
        total += EMAIL_POINTS
        matched["has_email"] = True
    if contact and contact.phone:
        total += PHONE_POINTS
        matched["has_phone"] = True

    total = max(0, min(MAX_SCORE, total))
    hot_min = icp.hot_min if icp.hot_min is not None else DEFAULT_HOT_MIN
    warm_min = icp.warm_min if icp.warm_min is not None else DEFAULT_WARM_MIN
    if total >= hot_min:
        band = "hot"
    elif total >= warm_min:
        band = "warm"
    else:
        band = "cold"
    if not keywords and not cities and not sectors and not matched:
        reasons.append("No configured signals matched.")
    return Qualification(score=total, band=band, reasons=reasons, matched=matched)


def qualify_lead(
    db: Session,
    lead: Lead,
    *,
    icp: IdealCustomerProfile | None = None,
    user_id: uuid.UUID | None = None,
) -> Qualification:
    profile = icp or load_icp(db, client_id=lead.client_id, agency_id=lead.agency_id)
    if profile is None:
        raise ValueError("Ideal customer profile is not configured for this client.")
    contact = db.get(Contact, lead.contact_id) if lead.contact_id else None
    result = score_lead(lead=lead, contact=contact, icp=profile)
    lead.score = result.score
    lead.updated_at = now_utc()
    # Qualification is metadata, not commercial activity: last_activity_at is
    # deliberately left alone so scoring does not reshuffle the pipeline.
    db.add(
        LeadActivity(
            agency_id=lead.agency_id,
            client_id=lead.client_id,
            lead_id=lead.id,
            user_id=user_id,
            kind=ACTIVITY_KIND,
            message=result.message()[:2000],
        )
    )
    return result


def maybe_auto_qualify(db: Session, lead: Lead) -> Qualification | None:
    """Score a freshly captured lead when the client opted in."""
    profile = load_icp(db, client_id=lead.client_id, agency_id=lead.agency_id)
    if profile is None or not profile.auto_qualify:
        return None
    try:
        return qualify_lead(db, lead, icp=profile)
    except ValueError:
        return None

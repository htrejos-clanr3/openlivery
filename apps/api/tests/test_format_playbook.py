"""Instagram format playbook (hook, enganche, single CTA)."""

from app.services.format_playbook import (
    assign_slide_cta,
    normalize_content_goal,
    playbook_prompt,
    slide_role,
)


def test_normalize_content_goal():
    assert normalize_content_goal("REACH") == "reach"
    assert normalize_content_goal("nope") == "loyalty"
    assert normalize_content_goal(None) == "loyalty"


def test_slide_role_hook_structure():
    assert slide_role(1, 7, hook_structure=True) == "hook"
    assert slide_role(2, 7, hook_structure=True) == "enganche"
    assert slide_role(3, 7, hook_structure=True) == "point"
    assert slide_role(7, 7, hook_structure=True) == "cta"
    assert slide_role(2, 7, hook_structure=False) == "point"


def test_assign_slide_cta_only_last():
    slides = [{"cta": "x"} for _ in range(5)]
    for i, item in enumerate(slides, start=1):
        assign_slide_cta(item, position=i, total=5, cta_instruction="Comenta MENU")
    assert [s["cta"] for s in slides] == ["", "", "", "", "Comenta MENU"]


def test_playbook_prompt_mentions_enganche_and_cta():
    text = playbook_prompt(
        content_type="CAROUSEL",
        content_goal="convert",
        cta_instruction="Escríbeme info",
        hook_structure=True,
        slide_count=7,
    )
    assert "ENGANCHE" in text
    assert "Escríbeme info" in text
    assert "likes" in text.lower()

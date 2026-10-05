"""Carousel visuals follow the product/service — not a people-photo default."""

from app.services.carousels import (
    _is_legacy_generic_style_prompt,
    _parse_scenes_json,
    _parse_slides_json,
    _slide_image_prompt,
)


def test_slide_image_prompt_has_no_headline_or_message():
    prompt = _slide_image_prompt(
        item={
            "headline": "Desarrollo web a tu medida",
            "body": "Sistemas administrativos, portales de clientes, intranets, inventarios y más.",
            "cta": "Cuéntanos tu idea",
            "image_scene": "Flat cartoon of a tablet showing blurred dashboards on a wooden counter, no people.",
        },
        primary="#075985",
        secondary="#0f172a",
        description="Agencia digital",
        company="Hacemos software a medida para restaurantes y clínicas.",
    )
    lowered = prompt.lower()
    assert "Desarrollo web a tu medida" not in prompt
    assert "Sistemas administrativos" not in prompt
    assert "Cuéntanos tu idea" not in prompt
    assert "headline:" not in lowered
    assert "message:" not in lowered
    assert "frosted cubes" not in lowered
    assert "do not default to people" in lowered
    assert "cartoon" in lowered or "Flat cartoon" in prompt
    assert "real brand mark is added later" in lowered


def test_prompt_without_scene_asks_medium_from_offer():
    prompt = _slide_image_prompt(
        item={"headline": "Menú de la semana", "body": "", "cta": "Pide ya"},
        primary="#075985",
        secondary="#0f172a",
        description="Promociona lasagna y postres",
        company="Restaurante La Casona",
    )
    lowered = prompt.lower()
    assert "Menú de la semana" not in prompt
    assert "Pide ya" not in prompt
    assert "Restaurante La Casona" in prompt
    assert "photorealistic" not in lowered
    assert "product or service" in lowered or "product/service" in lowered


def test_legacy_copy_prompts_are_detected():
    old = (
        "Photorealistic vertical 4:5 photograph, Instagram carousel frame. "
        "HEADLINE: Desarrollo web a tu medida\nMESSAGE: Sistemas administrativos"
    )
    assert _is_legacy_generic_style_prompt(old) is True
    assert _is_legacy_generic_style_prompt("a plated lasagna on a rustic table, no people") is False


def test_parse_keeps_image_scene():
    slides, caption = _parse_slides_json(
        '{"caption":"hola","slides":[{"headline":"A","body":"B","cta":"C","image_scene":"Still-life of tomatoes"}]}',
        1,
    )
    assert caption == "hola"
    assert slides[0]["image_scene"] == "Still-life of tomatoes"


def test_parse_scenes_json_by_index():
    scenes = _parse_scenes_json(
        '{"scenes":[{"i":2,"image_scene":"Cartoon bakery"},{"i":1,"image_scene":"Empty terrace"}]}',
        2,
    )
    assert scenes[1] == "Empty terrace"
    assert scenes[2] == "Cartoon bakery"

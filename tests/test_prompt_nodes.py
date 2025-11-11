import json
from pathlib import Path

import pytest

from prompt_loader_node import (
    PromptLibraryLoaderError,
    PromptLibraryLoaderNode,
    _parse_prompt_file,
)
from prompt_rolling_node import PromptRollingNode, PromptRollingError, _parse_library_payload
from text_preview_node import TextPreviewNode


def test_parse_prompt_file_array(tmp_path: Path):
    payload = [["low angle", "medium distance"], ["fish eye", "18mm"]]
    path = tmp_path / "camera.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    entries = _parse_prompt_file(path)

    assert entries == [["low angle", "medium distance"], ["fish eye", "18mm"]]

    # Cached read should return the same object (by identity) without reloading
    again = _parse_prompt_file(path)
    assert again is entries


def test_parse_prompt_file_newline_json(tmp_path: Path):
    content = """
    ["overhead", "wide shot"]
    ["close up"]
    """.strip()
    path = tmp_path / "angles.json"
    path.write_text(content, encoding="utf-8")

    entries = _parse_prompt_file(path)

    assert entries == [["overhead", "wide shot"], ["close up"]]


def _build_library_payload(tmp_path: Path) -> str:
    prompt_file = tmp_path / "lighting.json"
    prompt_file.write_text(json.dumps([["soft light"], ["dramatic shadows"]]), encoding="utf-8")

    groups = _parse_prompt_file(prompt_file)

    payload = {
        "groups": [
            {
                "name": "lighting",
                "entries": groups,
            }
        ]
    }
    return json.dumps(payload)


def test_prompt_rolling_single_group(tmp_path: Path):
    payload = _build_library_payload(tmp_path)

    node = PromptRollingNode()
    result = node.roll(library_1=payload, weight_1=1.0, seed=42)

    assert len(result) == 1
    prompt = result[0]
    assert prompt in {"soft light", "dramatic shadows"}


def test_prompt_rolling_weights(tmp_path: Path):
    payload = {
        "groups": [
            {
                "name": "camera",
                "entries": [["35mm"], ["fish eye"]],
            },
            {
                "name": "lighting",
                "entries": [["soft"], ["hard"]],
            },
        ]
    }

    payload_json = json.dumps(payload)

    node = PromptRollingNode()
    result = node.roll(library_1=payload_json, weight_1=1.5, seed=5)

    prompt = result[0]
    assert "1.5" in prompt


def test_prompt_rolling_requires_library():
    node = PromptRollingNode()
    with pytest.raises(PromptRollingError):
        node.roll(seed=-1)


def test_text_preview_basic():
    """Test that Text Preview node returns both output and UI data"""
    node = TextPreviewNode()
    test_text = "This is a test prompt"
    
    result = node.preview_text(text=test_text)
    
    # Should return tuple: (output_string, ui_dict)
    assert isinstance(result, tuple)
    assert len(result) == 2
    
    output_text, ui_data = result
    
    # Check output passthrough
    assert output_text == test_text
    
    # Check UI data format
    assert isinstance(ui_data, dict)
    assert "ui" in ui_data
    assert "text" in ui_data["ui"]
    assert ui_data["ui"]["text"][0] == test_text


def test_text_preview_multiline():
    """Test Text Preview with multiline text"""
    node = TextPreviewNode()
    test_text = "Line 1\nLine 2\nLine 3"
    
    output_text, ui_data = node.preview_text(text=test_text)
    
    assert output_text == test_text
    assert ui_data["ui"]["text"][0] == test_text


def test_text_preview_empty():
    """Test Text Preview with empty string"""
    node = TextPreviewNode()
    
    output_text, ui_data = node.preview_text(text="")
    
    assert output_text == ""
    assert ui_data["ui"]["text"][0] == ""


def test_text_preview_long_text():
    """Test Text Preview with very long text"""
    node = TextPreviewNode()
    test_text = "word " * 1000  # 1000 words
    
    output_text, ui_data = node.preview_text(text=test_text)
    
    assert output_text == test_text
    assert ui_data["ui"]["text"][0] == test_text



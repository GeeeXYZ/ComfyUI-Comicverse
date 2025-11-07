import json
from pathlib import Path

import pytest

from prompt_loader_node import (
    PromptLibraryLoaderError,
    PromptLibraryLoaderNode,
    _parse_prompt_file,
)
from prompt_rolling_node import PromptRollingNode, PromptRollingError, _parse_library_payload


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



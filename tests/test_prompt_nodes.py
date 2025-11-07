import json
from pathlib import Path

import pytest

from prompt_loader_node import (
    PromptLibraryLoaderError,
    _parse_file_specs,
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


def test_parse_file_specs_requires_array():
    with pytest.raises(PromptLibraryLoaderError):
        _parse_file_specs("{}")


def _build_library_payload(tmp_path: Path) -> str:
    prompt_file = tmp_path / "lighting.json"
    prompt_file.write_text(json.dumps([["soft light"], ["dramatic shadows"]]), encoding="utf-8")

    spec_json = json.dumps([{ "name": "lighting", "path": str(prompt_file) }])
    specs = _parse_file_specs(spec_json)

    assert len(specs) == 1
    groups = _parse_prompt_file(specs[0].path)

    payload = {
        "groups": [
            {
                "name": specs[0].name,
                "entries": groups,
            }
        ]
    }
    return json.dumps(payload)


def test_prompt_rolling_single_group(tmp_path: Path):
    payload = _build_library_payload(tmp_path)

    node = PromptRollingNode()
    prompt, details_json = node.roll(library_1=payload, seed=42)

    assert prompt in {"soft light", "dramatic shadows"}

    details = json.loads(details_json)
    assert "seed" in details
    assert len(details["selections"]) == 1


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
    weights = json.dumps({"input_0": 1.5})

    node = PromptRollingNode()
    prompt, details_json = node.roll(library_1=payload_json, weights_json=weights, seed=5)

    assert "1.50" in prompt

    details = json.loads(details_json)
    assert details["selections"][0]["weight"] == pytest.approx(1.5)


def test_prompt_rolling_requires_library():
    node = PromptRollingNode()
    with pytest.raises(PromptRollingError):
        node.roll()



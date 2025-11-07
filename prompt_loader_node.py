"""
Prompt library loader node for ComicVerse custom nodes.

Reads user-specified JSON files that describe prompt groups and exposes a
normalized payload for downstream nodes (e.g. the prompt rolling node).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Sequence


@dataclass(frozen=True)
class PromptFileSpec:
    name: str
    path: Path


class PromptLibraryLoaderError(Exception):
    """Custom error so callers can distinguish parsing failures."""


# Cache parsed prompt files keyed by absolute path. The cached value stores the
# file mtime and the parsed prompt rows so we only incur IO when the file
# changes.
_PROMPT_FILE_CACHE: Dict[str, tuple[float, List[List[str]]]] = {}


def _normalize_prompt_entries(entries: Sequence[Any], *, source: str) -> List[List[str]]:
    """Ensure the parsed prompt entries are a list of list of strings.

    Each prompt record should be a sequence of strings (a "prompt group").
    Empty strings are filtered out. Raises PromptLibraryLoaderError if the
    format is invalid.
    """

    normalized: List[List[str]] = []
    for idx, record in enumerate(entries):
        if isinstance(record, (str, int, float)):
            # Single literal treated as a group of one prompt.
            item = str(record).strip()
            if item:
                normalized.append([item])
            continue

        if not isinstance(record, Sequence):
            raise PromptLibraryLoaderError(
                f"Unsupported entry type in '{source}' at index {idx}: {type(record).__name__}"
            )

        group: List[str] = []
        for prompt in record:
            text = str(prompt).strip()
            if text:
                group.append(text)
        if group:
            normalized.append(group)

    if not normalized:
        raise PromptLibraryLoaderError(f"No prompts found in '{source}'. Ensure the JSON contains non-empty strings.")

    return normalized


def _parse_prompt_file(path: Path) -> List[List[str]]:
    """Parse a prompt JSON file into a list of prompt groups."""

    try:
        mtime = path.stat().st_mtime
    except FileNotFoundError as exc:
        raise PromptLibraryLoaderError(f"Prompt file not found: {path}") from exc

    cache_key = str(path)
    cached = _PROMPT_FILE_CACHE.get(cache_key)
    if cached and cached[0] == mtime:
        return cached[1]

    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PromptLibraryLoaderError(f"Failed to read prompt file '{path}': {exc}") from exc

    raw_text = raw_text.strip()
    if not raw_text:
        raise PromptLibraryLoaderError(f"Prompt file '{path}' is empty.")

    data: Any
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        # Attempt to interpret as newline separated JSON arrays, e.g.
        # ["prompt A", "prompt B"]
        # ["prompt C"]
        rows: List[List[str]] = []
        for segment in raw_text.splitlines():
            segment = segment.strip()
            if not segment:
                continue
            try:
                parsed_row = json.loads(segment)
            except json.JSONDecodeError as exc:
                raise PromptLibraryLoaderError(
                    f"Failed to parse line '{segment}' in '{path}': {exc.msg}"
                ) from exc
            row_norm = _normalize_prompt_entries([parsed_row], source=str(path))
            rows.extend(row_norm)
        _PROMPT_FILE_CACHE[cache_key] = (mtime, rows)
        return rows

    if isinstance(data, list):
        normalized = _normalize_prompt_entries(data, source=str(path))
        _PROMPT_FILE_CACHE[cache_key] = (mtime, normalized)
        return normalized

    raise PromptLibraryLoaderError(
        f"Prompt file '{path}' must be a JSON array (found {type(data).__name__})."
    )


def _parse_file_specs(config_json: str) -> List[PromptFileSpec]:
    if not config_json:
        return []

    try:
        raw_specs = json.loads(config_json)
    except json.JSONDecodeError as exc:
        raise PromptLibraryLoaderError(f"Invalid loader configuration JSON: {exc.msg}") from exc

    if not isinstance(raw_specs, list):
        raise PromptLibraryLoaderError("Loader configuration must be a JSON array of file specs.")

    specs: List[PromptFileSpec] = []
    for idx, entry in enumerate(raw_specs):
        if not isinstance(entry, dict):
            raise PromptLibraryLoaderError(
                f"File spec at index {idx} must be an object with 'path' (and optional 'name')."
            )
        path_value = entry.get("path")
        if not path_value or not isinstance(path_value, str):
            raise PromptLibraryLoaderError(f"File spec at index {idx} is missing a string 'path'.")

        name_value = entry.get("name")
        if name_value is not None and not isinstance(name_value, str):
            raise PromptLibraryLoaderError(f"'name' in file spec {idx} must be a string if provided.")

        resolved_path = Path(path_value).expanduser().resolve()
        category_name = name_value.strip() if name_value else resolved_path.stem

        specs.append(PromptFileSpec(name=category_name, path=resolved_path))

    return specs


class PromptLibraryLoaderNode:
    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        return {
            "required": {
                "file_specs_json": (
                    "STRING",
                    {
                        "multiline": False,
                        "default": "[]",
                        "forceInput": False,
                        "tooltip": "JSON array of file specs: [{\"name\": \"camera\", \"path\": \"/path/to/camera.json\"}]",
                    },
                )
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("library_json", "summary")
    FUNCTION = "load_library"
    CATEGORY = "ComicVerse/Prompt"

    def load_library(self, file_specs_json: str) -> tuple[str, str]:
        specs = _parse_file_specs(file_specs_json)
        if not specs:
            raise PromptLibraryLoaderError("No prompt files provided. Configure at least one file.")

        groups: List[Dict[str, Any]] = []
        total_prompts = 0

        for spec in specs:
            entries = _parse_prompt_file(spec.path)
            total_prompts += len(entries)
            groups.append(
                {
                    "name": spec.name,
                    "path": str(spec.path),
                    "entries": entries,
                    "entry_count": len(entries),
                }
            )

        payload = {
            "groups": groups,
            "total_groups": len(groups),
            "total_entries": total_prompts,
            "version": 1,
        }

        summary_lines = [
            f"{group['name']}: {group['entry_count']} entries ({group['path']})" for group in groups
        ]
        summary = os.linesep.join(summary_lines)

        # Ensure ASCII characters remain untouched (e.g. Chinese prompts) by disabling ASCII escaping.
        return json.dumps(payload, ensure_ascii=False), summary


NODE_CLASS_MAPPINGS = {
    "PromptLibraryLoaderNode": PromptLibraryLoaderNode,
}


NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptLibraryLoaderNode": "Prompt Library Loader",
}



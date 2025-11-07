"""
Prompt library loader node for ComicVerse custom nodes.

Automatically loads JSON files from the library directory and provides
a dropdown menu for selection.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Sequence


class PromptLibraryLoaderError(Exception):
    """Custom error so callers can distinguish parsing failures."""


# Cache parsed prompt files keyed by absolute path. The cached value stores the
# file mtime and the parsed prompt rows so we only incur IO when the file
# changes.
_PROMPT_FILE_CACHE: Dict[str, tuple[float, List[List[str]]]] = {}


# Get the library directory path
def _get_library_dir() -> Path:
    """Get the path to the library directory."""
    current_file = Path(__file__).resolve()
    library_dir = current_file.parent / "library"
    return library_dir


def _scan_library_files() -> List[str]:
    """Scan the library directory and return a list of available library names."""
    library_dir = _get_library_dir()
    
    if not library_dir.exists():
        library_dir.mkdir(parents=True, exist_ok=True)
        return []
    
    json_files = sorted(library_dir.glob("*.json"))
    return [f.stem for f in json_files]


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
        # Attempt to interpret as newline separated JSON arrays
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


class PromptLibraryLoaderNode:
    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        # Scan available library files
        available_libraries = _scan_library_files()
        
        # Provide a default if no libraries found
        if not available_libraries:
            available_libraries = ["(no libraries found)"]
        
        return {
            "required": {
                "library_name": (
                    available_libraries,
                    {
                        "tooltip": "Select a prompt library from the library folder",
                    },
                )
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("library_json",)
    FUNCTION = "load_library"
    CATEGORY = "ComicVerse/Prompt"
    OUTPUT_NODE = False

    def load_library(self, library_name: str) -> tuple[str]:
        # Check for placeholder
        if library_name == "(no libraries found)":
            raise PromptLibraryLoaderError(
                "No library files found in the library directory. "
                "Please add JSON files to ComfyUI-ComicVerse/library/"
            )
        
        # Get the library file path
        library_dir = _get_library_dir()
        library_path = library_dir / f"{library_name}.json"
        
        if not library_path.exists():
            raise PromptLibraryLoaderError(f"Library file not found: {library_path}")
        
        # Parse the library file
        entries = _parse_prompt_file(library_path)
        
        # Build the output payload
        groups = [
            {
                "name": library_name,
                "path": str(library_path),
                "entries": entries,
                "entry_count": len(entries),
            }
        ]
        
        payload = {
            "groups": groups,
            "total_groups": 1,
            "total_entries": len(entries),
            "version": 1,
        }
        
        # Return JSON payload
        return (json.dumps(payload, ensure_ascii=False),)


NODE_CLASS_MAPPINGS = {
    "PromptLibraryLoaderNode": PromptLibraryLoaderNode,
}


NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptLibraryLoaderNode": "Prompt Library Loader (Comic)",
}



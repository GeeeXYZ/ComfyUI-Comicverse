"""
Prompt rolling node: combines random selections from prompt libraries with
user-specified weights to build a formatted prompt string.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


@dataclass
class PromptGroup:
    source_index: int
    group_index: int
    name: str
    entries: List[List[str]]


class PromptRollingError(Exception):
    pass


def _parse_library_payload(raw: Optional[str], index: int) -> List[PromptGroup]:
    if not raw:
        return []

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PromptRollingError(f"Input {index+1} is not valid JSON: {exc.msg}") from exc

    groups = data.get("groups") if isinstance(data, dict) else None
    if not isinstance(groups, list):
        raise PromptRollingError(f"Input {index+1} is missing 'groups' array.")

    parsed_groups: List[PromptGroup] = []
    for group_idx, group in enumerate(groups):
        if not isinstance(group, dict):
            raise PromptRollingError(
                f"Group {group_idx} in input {index+1} must be an object with 'entries'."
            )

        name = group.get("name") or f"group_{group_idx+1}"
        entries = group.get("entries")
        if not isinstance(entries, list) or not entries:
            raise PromptRollingError(
                f"Group '{name}' in input {index+1} has no entries to choose from."
            )

        normalized_entries: List[List[str]] = []
        for entry_idx, entry in enumerate(entries):
            if isinstance(entry, (str, int, float)):
                value = str(entry).strip()
                if value:
                    normalized_entries.append([value])
                continue

            if isinstance(entry, Sequence):
                texts = [str(item).strip() for item in entry if str(item).strip()]
                if texts:
                    normalized_entries.append(texts)
                    continue

            raise PromptRollingError(
                f"Invalid entry in group '{name}' (input {index+1}, item {entry_idx})."
            )

        if not normalized_entries:
            raise PromptRollingError(
                f"Group '{name}' in input {index+1} has only empty entries."
            )

        parsed_groups.append(
            PromptGroup(
                source_index=index,
                group_index=group_idx,
                name=str(name),
                entries=normalized_entries,
            )
        )

    return parsed_groups


def _parse_weights(raw: Optional[str]) -> Dict[str, float]:
    if not raw:
        return {}

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PromptRollingError(f"weights_json is invalid JSON: {exc.msg}") from exc

    weights: Dict[str, float] = {}

    if isinstance(data, dict):
        items = data.items()
    elif isinstance(data, list):
        items = []
        for idx, entry in enumerate(data):
            if isinstance(entry, dict) and "id" in entry and "weight" in entry:
                items.append((str(entry["id"]), entry["weight"]))
            else:
                raise PromptRollingError(
                    "weights_json list entries must include 'id' and 'weight'."
                )
    else:
        raise PromptRollingError("weights_json must be an object or array.")

    for key, value in items:
        try:
            weight = float(value)
        except (TypeError, ValueError):
            raise PromptRollingError(f"Weight for '{key}' must be numeric.") from None
        if weight <= 0:
            raise PromptRollingError(f"Weight for '{key}' must be positive.")
        weights[str(key)] = weight

    return weights


def _format_prompts(prompts: Sequence[str]) -> str:
    return ", ".join(prompts)


# Persistent state for sequential indices: unique_id -> current_index
_ROLLING_STATE: Dict[str, int] = {}

class PromptRollingNode:
    MAX_INPUTS = 8

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        required = {
            "mode": (
                ["random", "sequential"],
                {"default": "random", "tooltip": "Random: pick random entries. Sequential: cycle through all combinations."},
            ),
            "library_1": (
                "STRING",
                {
                    "multiline": False,
                    "forceInput": True,
                    "tooltip": "Connect a Prompt Library Loader output",
                },
            ),
            "weight_1": (
                "FLOAT",
                {
                    "default": 1.0,
                    "min": 0.0,
                    "max": 2.0,
                    "step": 0.1,
                    "tooltip": "Weight for library_1 prompts (1.0 = normal)",
                },
            ),
            "prompt_index": (
                "INT",
                {
                    "default": -1,
                    "min": -1,
                    "step": 1,
                    "tooltip": "For Sequential mode: -1 for auto, >=0 to lock specific index.",
                },
            ),
        }

        optional: Dict[str, Tuple[str, Dict[str, Any]]] = {}
        for i in range(2, cls.MAX_INPUTS + 1):
            optional[f"library_{i}"] = (
                "STRING",
                {
                    "multiline": False,
                    "forceInput": True,
                    "tooltip": f"Optional prompt library {i}",
                },
            )
            optional[f"weight_{i}"] = (
                "FLOAT",
                {
                    "default": 1.0,
                    "min": 0.0,
                    "max": 2.0,
                    "step": 0.1,
                    "tooltip": f"Weight for library_{i} prompts (1.0 = normal)",
                },
            )

        return {
            "required": required,
            "optional": optional,
            "hidden": {
                "unique_id": "UNIQUE_ID",
            },
        }

    RETURN_TYPES = ("STRING", "INT")
    RETURN_NAMES = ("output", "current_index")
    FUNCTION = "roll"
    CATEGORY = "ComicVerse/Prompt"

    @classmethod
    def IS_CHANGED(cls, unique_id: str, **kwargs: Any) -> float:
        # Always re-run
        return float("nan")

    def roll(self, mode: str, prompt_index: int = -1, unique_id: str = "", **kwargs: Any) -> Tuple[str, int]:
        # Collect connected libraries and their weights
        libraries_with_weights: List[Tuple[int, str, float]] = []
        
        for idx in range(self.MAX_INPUTS):
            lib_key = f"library_{idx + 1}"
            weight_key = f"weight_{idx + 1}"
            
            library_raw = kwargs.get(lib_key)
            if library_raw:
                weight = kwargs.get(weight_key, 1.0)
                libraries_with_weights.append((idx, library_raw, float(weight)))

        if not libraries_with_weights:
            raise PromptRollingError("No prompt libraries connected. Connect at least one loader output.")

        # Parse all groups
        all_groups: List[Tuple[PromptGroup, float]] = []
        for idx, library_raw, weight in libraries_with_weights:
            groups = _parse_library_payload(library_raw, idx)
            for group in groups:
                all_groups.append((group, weight))

        formatted_segments = []
        current_index = 0

        if mode == "random":
            # Random Mode Logic (Original Rolling)
            # We don't use prompt_index or state for random mode in this design
            # Just pure random selection
            rng = random.Random() # System time seed
            
            # If user wants a fixed seed, they should use the standard ComfyUI seed control?
            # But we removed the 'seed' input. So it's always random.
            
            for group, weight in all_groups:
                entry_index = rng.randrange(len(group.entries))
                entry = group.entries[entry_index]
                text = _format_prompts(entry)
                
                if abs(weight - 1.0) > 0.01:
                    formatted = f"({text}:{weight:.1f})"
                else:
                    formatted = text
                formatted_segments.append(formatted)
                
            # current_index is meaningless in random mode, return 0 or maybe a random hash?
            current_index = 0 

        else:
            # Sequential Mode Logic (From Queue)
            group_sizes = [len(g.entries) for g, _ in all_groups]
            total_combinations = 1
            for size in group_sizes:
                total_combinations *= size

            if total_combinations == 0:
                return ("", 0)

            if prompt_index >= 0:
                # Locked mode
                current_index = prompt_index % total_combinations
                _ROLLING_STATE[unique_id] = (current_index + 1) % total_combinations
            else:
                # Auto mode
                current_index = _ROLLING_STATE.get(unique_id, 0)
                _ROLLING_STATE[unique_id] = (current_index + 1) % total_combinations

            # Calculate indices (Mixed Radix)
            temp_index = current_index
            indices = []
            for i in range(len(group_sizes)):
                stride = 1
                for size in group_sizes[i+1:]:
                    stride *= size
                group_idx = (temp_index // stride) % group_sizes[i]
                indices.append(group_idx)

            for i, (group_info, weight) in enumerate(all_groups):
                group = group_info
                entry_idx = indices[i]
                entry = group.entries[entry_idx]
                text = _format_prompts(entry)
                
                if abs(weight - 1.0) > 0.01:
                    formatted = f"({text}:{weight:.1f})"
                else:
                    formatted = text
                formatted_segments.append(formatted)

        prompt_output = ", ".join(segment for segment in formatted_segments if segment)
        
        return (prompt_output, current_index)


NODE_CLASS_MAPPINGS = {
    "PromptRollingNode": PromptRollingNode,
}


NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptRollingNode": "Prompt Rolling | ComicVerse",
}



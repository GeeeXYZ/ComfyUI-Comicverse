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


class PromptRollingNode:
    MAX_INPUTS = 8

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        # Only define seed and first library+weight as required
        # Frontend will dynamically add more weight widgets as needed
        required = {
            "seed": (
                "INT",
                {
                    "default": -1,
                    "min": -1,
                    "max": 2**31 - 1,
                    "tooltip": "Random seed (-1 for random, same seed = same result)",
                    "control_after_generate": "randomize",
                },
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
        }

        # Library inputs 2-8 are optional (frontend adds inputs dynamically)
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
            # Also add optional weights (but frontend will manage them)
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
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("output",)
    FUNCTION = "roll"
    CATEGORY = "ComicVerse/Prompt"

    def roll(self, seed: int = -1, **kwargs: Any) -> Tuple[str]:
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

        # Setup random number generator
        rng = random.Random()
        if isinstance(seed, int) and seed >= 0:
            rng.seed(seed)
        else:
            actual_seed = rng.randrange(0, 2**63)
            rng.seed(actual_seed)

        # Select and format prompts
        formatted_segments = []
        for group, weight in all_groups:
            entry_index = rng.randrange(len(group.entries))
            entry = group.entries[entry_index]
            text = _format_prompts(entry)
            
            # Format with weight if not 1.0
            if abs(weight - 1.0) > 0.01:  # Use small epsilon for float comparison
                formatted = f"({text}:{weight:.1f})"
            else:
                formatted = text
            
            formatted_segments.append(formatted)

        prompt_output = ", ".join(segment for segment in formatted_segments if segment)
        
        return (prompt_output,)


NODE_CLASS_MAPPINGS = {
    "PromptRollingNode": PromptRollingNode,
}


NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptRollingNode": "Prompt Rolling | ComicVerse",
}



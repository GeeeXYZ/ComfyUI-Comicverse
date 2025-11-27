"""
Prompt queue node: outputs prompts sequentially from prompt libraries.
If multiple libraries or groups are provided, it generates combinations (Cartesian product)
and cycles through them one by one on each run.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

# Persistent state for queue indices: unique_id -> current_index
_QUEUE_STATE: Dict[str, int] = {}

@dataclass
class PromptGroup:
    source_index: int
    group_index: int
    name: str
    entries: List[List[str]]


class PromptQueueError(Exception):
    pass


def _parse_library_payload(raw: Optional[str], index: int) -> List[PromptGroup]:
    if not raw:
        return []

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PromptQueueError(f"Input {index+1} is not valid JSON: {exc.msg}") from exc

    groups = data.get("groups") if isinstance(data, dict) else None
    if not isinstance(groups, list):
        raise PromptQueueError(f"Input {index+1} is missing 'groups' array.")

    parsed_groups: List[PromptGroup] = []
    for group_idx, group in enumerate(groups):
        if not isinstance(group, dict):
            raise PromptQueueError(
                f"Group {group_idx} in input {index+1} must be an object with 'entries'."
            )

        name = group.get("name") or f"group_{group_idx+1}"
        entries = group.get("entries")
        if not isinstance(entries, list) or not entries:
            raise PromptQueueError(
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

            raise PromptQueueError(
                f"Invalid entry in group '{name}' (input {index+1}, item {entry_idx})."
            )

        if not normalized_entries:
            raise PromptQueueError(
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


def _format_prompts(prompts: Sequence[str]) -> str:
    return ", ".join(prompts)


class PromptQueueNode:
    MAX_INPUTS = 8

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        required = {
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

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("output",)
    FUNCTION = "process_queue"
    CATEGORY = "ComicVerse/Prompt"

    @classmethod
    def IS_CHANGED(cls, unique_id: str, **kwargs: Any) -> float:
        # Return a value that changes when the internal state changes, 
        # or float("nan") to force re-execution every time.
        # Since we want to advance the queue on every run, we force update.
        return float("nan")

    def process_queue(self, unique_id: str, **kwargs: Any) -> Tuple[str]:
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
            raise PromptQueueError("No prompt libraries connected. Connect at least one loader output.")

        # Parse all groups
        all_groups: List[Tuple[PromptGroup, float]] = []
        for idx, library_raw, weight in libraries_with_weights:
            groups = _parse_library_payload(library_raw, idx)
            for group in groups:
                all_groups.append((group, weight))

        if not all_groups:
             raise PromptQueueError("No prompt groups found in connected libraries.")

        # Calculate total combinations and group sizes
        group_sizes = [len(g.entries) for g, _ in all_groups]
        total_combinations = 1
        for size in group_sizes:
            total_combinations *= size

        if total_combinations == 0:
            return ("",)

        # Get current index for this node instance
        current_index = _QUEUE_STATE.get(unique_id, 0)
        
        # Calculate indices for each group based on current_index
        # We treat the groups as digits in a mixed-radix number system
        # The last group changes fastest (innermost loop)
        
        selected_entries = []
        temp_index = current_index % total_combinations # Wrap around
        
        # To match typical "odometer" order (last group changes fastest),
        # we process from last to first for remainder calculation, 
        # or we can do it from first to last if we want first group to be most significant.
        # Let's make the first group the most significant (changes slowest).
        # Example: Group A (2), Group B (2). Total 4.
        # 0: A0, B0
        # 1: A0, B1
        # 2: A1, B0
        # 3: A1, B1
        
        # We need to calculate the stride for each position.
        # For the i-th group, the stride is the product of sizes of all subsequent groups.
        
        indices = []
        for i in range(len(group_sizes)):
            # Stride is product of sizes[i+1:]
            stride = 1
            for size in group_sizes[i+1:]:
                stride *= size
            
            group_idx = (temp_index // stride) % group_sizes[i]
            indices.append(group_idx)

        # Construct the output
        formatted_segments = []
        for i, (group_info, weight) in enumerate(all_groups):
            group = group_info
            entry_idx = indices[i]
            entry = group.entries[entry_idx]
            text = _format_prompts(entry)
            
            # Format with weight if not 1.0
            if abs(weight - 1.0) > 0.01:
                formatted = f"({text}:{weight:.1f})"
            else:
                formatted = text
            
            formatted_segments.append(formatted)

        prompt_output = ", ".join(segment for segment in formatted_segments if segment)

        # Update state for next run
        _QUEUE_STATE[unique_id] = (current_index + 1) % total_combinations

        return (prompt_output,)


NODE_CLASS_MAPPINGS = {
    "PromptQueueNode": PromptQueueNode,
}


NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptQueueNode": "Prompt Queue | ComicVerse",
}

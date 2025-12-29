
import sys
import os
import json

# Add parent directory to path to import comicverse_nodes
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from comicverse_nodes import PromptStrengthSlider

def test_prompt_slider_zero_weight():
    slider = PromptStrengthSlider()
    
    # Case 1: Simple case with one 0 weight
    prompts = "cat, dog"
    strengths_json = json.dumps({
        "cat": 1.2,
        "dog": 0.0,
        "__prompts__": ["cat", "dog"]
    })
    
    result = slider.apply_strengths(prompts, strengths_json)
    print(f"Input: cat=1.2, dog=0.0")
    print(f"Output: {result[0]}")
    
    assert "(cat:1.2)" in result[0]
    assert "dog" not in result[0]
    
    # Case 2: All zero
    strengths_json_all_zero = json.dumps({
        "cat": 0.0,
        "dog": 0.0,
        "__prompts__": ["cat", "dog"]
    })
    result_all_zero = slider.apply_strengths(prompts, strengths_json_all_zero)
    print(f"Input: cat=0.0, dog=0.0")
    print(f"Output: '{result_all_zero[0]}'")
    
    assert result_all_zero[0] == ""

    # Case 3: Mixed
    strengths_json_mixed = json.dumps({
        "cat": 1.0,
        "dog": 0.0,
        "bird": 0.5,
        "__prompts__": ["cat", "dog", "bird"]
    })
    result_mixed = slider.apply_strengths("cat, dog, bird", strengths_json_mixed)
    print(f"Input: cat=1.0, dog=0.0, bird=0.5")
    print(f"Output: {result_mixed[0]}")
    
    assert "(cat:1.0)" in result_mixed[0]
    assert "(bird:0.5)" in result_mixed[0]
    assert "dog" not in result_mixed[0]

    print("\nAll tests passed!")

if __name__ == "__main__":
    test_prompt_slider_zero_weight()

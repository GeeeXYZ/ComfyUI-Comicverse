"""
Test suite for Comic Library Node index adjustment logic.
Verifies that selected image indices are correctly adjusted after deletions.
"""

import torch
import pytest
from unittest.mock import MagicMock, patch

# Mock PromptServer to avoid ComfyUI dependency
import sys
sys.modules['server'] = MagicMock()

from comicverse_nodes import ComicAssetLibraryNode, _LIBRARY_CACHE, _LIBRARY_HASHES


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear global cache before each test."""
    _LIBRARY_CACHE.clear()
    _LIBRARY_HASHES.clear()
    yield
    _LIBRARY_CACHE.clear()
    _LIBRARY_HASHES.clear()


def _create_test_images(count: int, start_value: float = 0.0):
    """Create test images with distinct pixel values for identification."""
    images = []
    for i in range(count):
        # Each image has a unique average value to distinguish them
        value = start_value + (i * 0.1)
        img = torch.full((1, 64, 64, 3), value, dtype=torch.float32)
        images.append(img)
    return images


def _get_image_value(tensor):
    """Extract the characteristic value from a test image."""
    return tensor[0, 0, 0, 0].item()


def test_index_adjustment_after_deletion():
    """Test that selected indices are correctly adjusted after deletion."""
    node = ComicAssetLibraryNode()
    
    # Step 1: Add 5 images (0.0, 0.1, 0.2, 0.3, 0.4)
    images = _create_test_images(5)
    batch = torch.cat(images, dim=0)
    
    result = node.run(
        output_count=2,
        selected_indices="2,4",  # Select images with values 0.2 and 0.4
        image_input_a=batch,
        unique_id="test1"
    )
    
    # Verify initial selection
    img1_value = _get_image_value(result[0])
    img2_value = _get_image_value(result[1])
    assert abs(img1_value - 0.2) < 0.01, f"Expected 0.2, got {img1_value}"
    assert abs(img2_value - 0.4) < 0.01, f"Expected 0.4, got {img2_value}"
    
    # Step 2: Delete indices 0 and 1, keep selection on 2 and 4
    # After deletion: [0.2, 0.3, 0.4] at indices [0, 1, 2]
    # Original selection [2, 4] should become [0, 2]
    result = node.run(
        output_count=2,
        selected_indices="2,4",  # Still referring to original indices
        pending_deletions="0,1",  # Delete first two images
        image_input_a=None,  # No new images
        unique_id="test1"
    )
    
    # After deletion and index adjustment, should still output same images
    img1_value = _get_image_value(result[0])
    img2_value = _get_image_value(result[1])
    assert abs(img1_value - 0.2) < 0.01, f"After deletion: Expected 0.2, got {img1_value}"
    assert abs(img2_value - 0.4) < 0.01, f"After deletion: Expected 0.4, got {img2_value}"


def test_index_adjustment_with_new_images():
    """Test index adjustment when deleting and adding images simultaneously."""
    node = ComicAssetLibraryNode()
    
    # Step 1: Add 5 images (0.0 to 0.4)
    images = _create_test_images(5)
    batch = torch.cat(images, dim=0)
    
    node.run(
        output_count=2,
        selected_indices="1,3",  # Select 0.1 and 0.3
        image_input_a=batch,
        unique_id="test2"
    )
    
    # Step 2: Delete index 0, add 2 new images (0.5, 0.6), keep selection on 1,3
    # After deletion: [0.1, 0.2, 0.3, 0.4]
    # After adding: [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
    # Original indices [1, 3] should adjust to [0, 2] (pointing to 0.1, 0.3)
    new_images = _create_test_images(2, start_value=0.5)
    new_batch = torch.cat(new_images, dim=0)
    
    result = node.run(
        output_count=2,
        selected_indices="1,3",
        pending_deletions="0",
        image_input_a=new_batch,
        unique_id="test2"
    )
    
    # Should output 0.1 and 0.3 (adjusted indices 0 and 2)
    img1_value = _get_image_value(result[0])
    img2_value = _get_image_value(result[1])
    assert abs(img1_value - 0.1) < 0.01, f"Expected 0.1, got {img1_value}"
    assert abs(img2_value - 0.3) < 0.01, f"Expected 0.3, got {img2_value}"


def test_deleted_index_removed_from_selection():
    """Test that deleted indices are removed from selection."""
    node = ComicAssetLibraryNode()
    
    # Add 5 images
    images = _create_test_images(5)
    batch = torch.cat(images, dim=0)
    
    node.run(
        output_count=3,
        selected_indices="1,2,3",
        image_input_a=batch,
        unique_id="test3"
    )
    
    # Delete index 2, which is in the selection
    # Selection [1, 2, 3] should become [0, 1] after adjustment
    result = node.run(
        output_count=3,
        selected_indices="1,2,3",
        pending_deletions="2",
        image_input_a=None,
        unique_id="test3"
    )
    
    # Should only get 2 valid images (index 2 was deleted)
    selected_count = result[6]  # Last return value is selected_count
    assert selected_count == 2, f"Expected 2 selected images, got {selected_count}"


def test_multiple_deletions_complex():
    """Test complex scenario with multiple deletions."""
    node = ComicAssetLibraryNode()
    
    # Add 10 images (0.0 to 0.9)
    images = _create_test_images(10)
    batch = torch.cat(images, dim=0)
    
    node.run(
        output_count=3,
        selected_indices="2,5,8",  # Select 0.2, 0.5, 0.8
        image_input_a=batch,
        unique_id="test4"
    )
    
    # Delete indices 0, 1, 4, 7
    # Original: [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    # After:    [0.2, 0.3, 0.5, 0.6, 0.8, 0.9]
    # Selection [2, 5, 8] should map to:
    #   - 2 -> 0 (two deletions before: 0,1)
    #   - 5 -> 2 (three deletions before: 0,1,4)
    #   - 8 -> 4 (four deletions before: 0,1,4,7)
    result = node.run(
        output_count=3,
        selected_indices="2,5,8",
        pending_deletions="0,1,4,7",
        image_input_a=None,
        unique_id="test4"
    )
    
    # Verify outputs are still 0.2, 0.5, 0.8
    img1_value = _get_image_value(result[0])
    img2_value = _get_image_value(result[1])
    img3_value = _get_image_value(result[2])
    assert abs(img1_value - 0.2) < 0.01, f"Expected 0.2, got {img1_value}"
    assert abs(img2_value - 0.5) < 0.01, f"Expected 0.5, got {img2_value}"
    assert abs(img3_value - 0.8) < 0.01, f"Expected 0.8, got {img3_value}"


def test_no_adjustment_when_no_deletion():
    """Test that indices are unchanged when there's no deletion."""
    node = ComicAssetLibraryNode()
    
    # Add 5 images
    images = _create_test_images(5)
    batch = torch.cat(images, dim=0)
    
    # First run: select indices 1, 3
    result1 = node.run(
        output_count=2,
        selected_indices="1,3",
        image_input_a=batch,
        unique_id="test5"
    )
    
    # Second run: no deletion, no new images
    result2 = node.run(
        output_count=2,
        selected_indices="1,3",
        pending_deletions="",
        image_input_a=None,
        unique_id="test5"
    )
    
    # Results should be identical
    assert torch.allclose(result1[0], result2[0]), "First image should be identical"
    assert torch.allclose(result1[1], result2[1]), "Second image should be identical"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


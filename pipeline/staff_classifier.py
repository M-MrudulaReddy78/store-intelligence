"""
Staff detection module.
Uses heuristics: uniform color detection, absence of shopping behavior,
or pre-defined uniform templates. For production, a dedicated classifier is recommended.
"""

import cv2
import numpy as np
from typing import List, Tuple

# Uniform color ranges in HSV (example for a retail chain)
UNIFORM_COLORS = {
    "red": ([0, 50, 50], [10, 255, 255]),
    "blue": ([100, 50, 50], [130, 255, 255]),
    "black": ([0, 0, 0], [180, 255, 50]),
}

# Simplified: if person wears a uniform color in the upper torso region
def is_staff(frame: np.ndarray, bbox: List[int], confidence_threshold=0.6) -> bool:
    """
    Determine if the person detected is a staff member.
    Returns True if uniform color dominates the upper body.
    """
    x1, y1, x2, y2 = map(int, bbox)
    height = y2 - y1
    # Upper half of bounding box (head and torso)
    upper_y2 = y1 + int(height * 0.6)
    roi = frame[y1:upper_y2, x1:x2]
    if roi.size == 0:
        return False

    # Convert to HSV for better color segmentation
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

    # Count uniform-colored pixels
    uniform_pixels = 0
    total_pixels = roi.shape[0] * roi.shape[1]
    for color, (lower, upper) in UNIFORM_COLORS.items():
        lower = np.array(lower, dtype=np.uint8)
        upper = np.array(upper, dtype=np.uint8)
        mask = cv2.inRange(hsv, lower, upper)
        uniform_pixels += cv2.countNonZero(mask)

    ratio = uniform_pixels / total_pixels if total_pixels > 0 else 0
    # If more than 30% of upper body matches uniform colors, classify as staff
    # and also require high detection confidence (since staff may be partially occluded)
    return ratio > 0.3 and confidence_threshold > 0.7

def is_staff_by_pose(pose_keypoints: List) -> bool:
    """
    Placeholder for future enhancement: use pose to detect employee badges or gestures.
    """
    # Not implemented yet – return False
    return False

# For testing / mock mode
def is_staff_mock(frame, bbox) -> bool:
    """Mock function that returns False for all (treat everyone as customer)."""
    return False
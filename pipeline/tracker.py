"""
Re-identification and tracking helper functions.
Uses bounding box overlap (IOU) and feature-based matching for improved tracking.
"""

import numpy as np
from collections import deque
from typing import List, Tuple, Dict, Optional
import cv2

class SimpleReID:
    """
    Lightweight Re-ID using color histograms and bounding box position.
    For production, replace with OSNet or similar deep learning model.
    """
    def __init__(self, iou_threshold=0.5, feature_distance_threshold=0.7, history_length=30):
        self.iou_threshold = iou_threshold
        self.feature_distance_threshold = feature_distance_threshold
        self.track_history = {}  # track_id -> deque of (frame_idx, bbox, color_hist)
        self.next_track_id = 0

    def _compute_color_histogram(self, frame: np.ndarray, bbox: List[int]) -> np.ndarray:
        """Extract normalized RGB histogram from the person region."""
        x1, y1, x2, y2 = map(int, bbox)
        roi = frame[y1:y2, x1:x2]
        if roi.size == 0:
            return np.zeros(96)  # 32 bins per channel
        hist = []
        for channel in range(3):
            h = cv2.calcHist([roi], [channel], None, [32], [0, 256])
            cv2.normalize(h, h, 0, 1, cv2.NORM_MINMAX)
            hist.append(h.flatten())
        return np.concatenate(hist)

    def _iou(self, bbox1: List[int], bbox2: List[int]) -> float:
        """Intersection over Union of two bounding boxes."""
        x1 = max(bbox1[0], bbox2[0])
        y1 = max(bbox1[1], bbox2[1])
        x2 = min(bbox1[2], bbox2[2])
        y2 = min(bbox1[3], bbox2[3])
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
        area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
        union = area1 + area2 - inter
        return inter / union if union > 0 else 0.0

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Cosine similarity between two feature vectors."""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return np.dot(a, b) / (norm_a * norm_b)

    def update(self, detections: List[np.ndarray], frame: np.ndarray, frame_idx: int) -> Dict[int, np.ndarray]:
        """
        Assign new detections to existing tracks or create new tracks.
        Returns mapping: track_id -> detection (bbox + confidence + class)
        """
        if len(detections) == 0:
            return {}

        # For each detection, compute features
        det_features = []
        for det in detections:
            bbox = det[:4]
            hist = self._compute_color_histogram(frame, bbox)
            det_features.append((bbox, det[4], hist))  # bbox, confidence, hist

        # Greedy assignment: match existing tracks by IOU + feature similarity
        assigned = {}
        unmatched_det_idx = set(range(len(det_features)))
        unmatched_track_ids = set(self.track_history.keys())

        for track_id, history in self.track_history.items():
            if not history:
                continue
            # Use the latest known bbox and feature
            last_bbox, last_hist = history[-1][1], history[-1][2]
            best_match = None
            best_score = -1
            for i, (det_bbox, _, det_hist) in enumerate(det_features):
                if i not in unmatched_det_idx:
                    continue
                iou = self._iou(last_bbox, det_bbox)
                feat_sim = self._cosine_similarity(last_hist, det_hist)
                # Weighted score: IOU more important for spatial continuity
                score = 0.6 * iou + 0.4 * feat_sim
                if score > best_score and score > self.iou_threshold:
                    best_score = score
                    best_match = i
            if best_match is not None:
                assigned[track_id] = det_features[best_match]
                unmatched_det_idx.discard(best_match)
                unmatched_track_ids.discard(track_id)

        # Create new tracks for unmatched detections
        new_track_map = {}
        for i in unmatched_det_idx:
            new_id = self.next_track_id
            self.next_track_id += 1
            new_track_map[new_id] = det_features[i]
            assigned[new_id] = det_features[i]

        # Update history
        for track_id, (bbox, conf, hist) in assigned.items():
            history = self.track_history.get(track_id, deque(maxlen=30))
            history.append((frame_idx, bbox, hist))
            self.track_history[track_id] = history

        # Remove tracks that haven't been updated for > 30 frames (disappeared)
        to_delete = []
        for track_id, history in self.track_history.items():
            if history and (frame_idx - history[-1][0]) > 30:
                to_delete.append(track_id)
        for track_id in to_delete:
            del self.track_history[track_id]

        # Build final result: track_id -> detection (bbox + conf + class)
        result = {}
        for track_id, (bbox, conf, _) in assigned.items():
            # Format: [x1, y1, x2, y2, conf, class_id] (class_id = 0 for person)
            result[track_id] = np.array([*bbox, conf, 0])
        return result
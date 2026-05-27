"""
Simple ByteTrack-like tracker using Kalman filters and IoU matching.
Requires: pip install lap
"""

import numpy as np
from scipy.optimize import linear_sum_assignment
from filterpy.kalman import KalmanFilter

class Track:
    def __init__(self, track_id, bbox, confidence, frame_idx):
        self.track_id = track_id
        self.bbox = bbox          # [x1, y1, x2, y2]
        self.confidence = confidence
        self.frame_idx = frame_idx
        self.age = 0
        self.hits = 1
        self.time_since_update = 0
        self.kalman = self._init_kalman(bbox)

    def _init_kalman(self, bbox):
        kf = KalmanFilter(dim_x=8, dim_z=4)
        dt = 1.0
        kf.F = np.array([[1,0,0,0,dt,0,0,0],
                         [0,1,0,0,0,dt,0,0],
                         [0,0,1,0,0,0,dt,0],
                         [0,0,0,1,0,0,0,dt],
                         [0,0,0,0,1,0,0,0],
                         [0,0,0,0,0,1,0,0],
                         [0,0,0,0,0,0,1,0],
                         [0,0,0,0,0,0,0,1]])
        kf.H = np.array([[1,0,0,0,0,0,0,0],
                         [0,1,0,0,0,0,0,0],
                         [0,0,1,0,0,0,0,0],
                         [0,0,0,1,0,0,0,0]])
        kf.R *= 10
        kf.P *= 1000
        x, y, w, h = self._bbox_to_xywh(bbox)
        kf.x[:4] = np.array([x, y, w, h])
        return kf

    def _bbox_to_xywh(self, bbox):
        x1, y1, x2, y2 = bbox
        w = x2 - x1
        h = y2 - y1
        return (x1 + w/2, y1 + h/2, w, h)

    def predict(self):
        self.kalman.predict()
        self.age += 1
        self.time_since_update += 1

    def update(self, bbox, confidence, frame_idx):
        x, y, w, h = self._bbox_to_xywh(bbox)
        self.kalman.update(np.array([x, y, w, h]))
        self.bbox = bbox
        self.confidence = confidence
        self.hits += 1
        self.time_since_update = 0
        self.frame_idx = frame_idx

    def get_estimate(self):
        state = self.kalman.x
        x, y, w, h = state[0], state[1], state[2], state[3]
        x1 = int(x - w/2)
        y1 = int(y - h/2)
        x2 = int(x + w/2)
        y2 = int(y + h/2)
        return np.array([x1, y1, x2, y2])

def iou(bbox1, bbox2):
    x1 = max(bbox1[0], bbox2[0])
    y1 = max(bbox1[1], bbox2[1])
    x2 = min(bbox1[2], bbox2[2])
    y2 = min(bbox1[3], bbox2[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area1 = (bbox1[2]-bbox1[0])*(bbox1[3]-bbox1[1])
    area2 = (bbox2[2]-bbox2[0])*(bbox2[3]-bbox2[1])
    union = area1 + area2 - inter
    return inter / union if union > 0 else 0

class ByteTracker:
    def __init__(self, track_high_thresh=0.5, track_low_thresh=0.1, iou_thresh=0.3, max_age=30, frame_rate=30):
        self.track_high_thresh = track_high_thresh
        self.track_low_thresh = track_low_thresh
        self.iou_thresh = iou_thresh
        self.max_age = max_age
        self.frame_rate = frame_rate
        self.next_id = 1
        self.tracks = []

    def update(self, detections, confidences, frame_idx):
        """
        detections: list of bboxes [x1,y1,x2,y2]
        confidences: list of conf scores
        """
        # Predict all existing tracks
        for t in self.tracks:
            t.predict()

        # Separate high and low score detections
        high_dets = []
        high_confs = []
        low_dets = []
        low_confs = []
        for bbox, conf in zip(detections, confidences):
            if conf >= self.track_high_thresh:
                high_dets.append(bbox)
                high_confs.append(conf)
            else:
                low_dets.append(bbox)
                low_confs.append(conf)

        # Associate high score detections with tracks
        matched, unmatched_tracks, unmatched_dets = self._match(high_dets, high_confs, self.tracks)

        # Update matched tracks
        for track_idx, det_idx in matched:
            self.tracks[track_idx].update(high_dets[det_idx], high_confs[det_idx], frame_idx)

        # Create new tracks for unmatched detections (high score)
        for det_idx in unmatched_dets:
            new_track = Track(self.next_id, high_dets[det_idx], high_confs[det_idx], frame_idx)
            self.tracks.append(new_track)
            self.next_id += 1

        # Now try to match remaining unmatched tracks with low score detections
        remaining_tracks = [self.tracks[i] for i in unmatched_tracks]
        if low_dets and remaining_tracks:
            matched_low, unmatched_tracks_low, unmatched_dets_low = self._match(low_dets, low_confs, remaining_tracks, iou_thresh=self.iou_thresh)
            # Convert indices back to original track list
            for track_idx, det_idx in matched_low:
                orig_track_idx = unmatched_tracks[track_idx]
                self.tracks[orig_track_idx].update(low_dets[det_idx], low_confs[det_idx], frame_idx)
            # Any remaining unmatched tracks are marked as lost
            for track_idx in unmatched_tracks_low:
                orig_track_idx = unmatched_tracks[track_idx]
                self.tracks[orig_track_idx].time_since_update += 1
        else:
            # All unmatched tracks increase their lost counter
            for track_idx in unmatched_tracks:
                self.tracks[track_idx].time_since_update += 1

        # Remove dead tracks
        self.tracks = [t for t in self.tracks if t.time_since_update <= self.max_age]

        return self.tracks

    def _match(self, detections, confidences, tracks, iou_thresh=None):
        if iou_thresh is None:
            iou_thresh = self.iou_thresh
        if not tracks or not detections:
            return [], list(range(len(tracks))), list(range(len(detections)))
        cost_matrix = np.zeros((len(tracks), len(detections)))
        for i, track in enumerate(tracks):
            pred_bbox = track.get_estimate()
            for j, det_bbox in enumerate(detections):
                cost_matrix[i, j] = 1 - iou(pred_bbox, det_bbox)
        row_indices, col_indices = linear_sum_assignment(cost_matrix)
        matched = []
        unmatched_tracks = []
        for i in range(len(tracks)):
            if i not in row_indices:
                unmatched_tracks.append(i)
        unmatched_dets = []
        for j in range(len(detections)):
            if j not in col_indices:
                unmatched_dets.append(j)
        for i, j in zip(row_indices, col_indices):
            if cost_matrix[i, j] <= 1 - iou_thresh:
                matched.append((i, j))
            else:
                unmatched_tracks.append(i)
                unmatched_dets.append(j)
        return matched, unmatched_tracks, unmatched_dets
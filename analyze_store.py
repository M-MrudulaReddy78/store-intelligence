"""
store-intelligence - Starter Analysis Script
Reads video clips, store layout, and POS transactions.
"""

import os
import json
import csv
import cv2
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

# Configuration
DATA_DIR = Path("data")
CLIPS_DIR = DATA_DIR / "clips"
LAYOUT_FILE = DATA_DIR / "store_layout.json"
POS_FILE = DATA_DIR / "pos_transactions.csv"

def load_layout():
    """Load store layout from JSON file."""
    if not LAYOUT_FILE.exists():
        print(f"Warning: {LAYOUT_FILE} not found.")
        return {}
    with open(LAYOUT_FILE, 'r') as f:
        return json.load(f)

def load_pos():
    """Load POS transactions into pandas DataFrame."""
    if not POS_FILE.exists():
        print(f"Warning: {POS_FILE} not found.")
        return pd.DataFrame()
    return pd.read_csv(POS_FILE)

def analyze_video(video_path, sample_rate=30):
    """
    Basic video analysis: frame count, motion detection (simplified).
    Returns: dict with video info.
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return {"error": "Cannot open video"}
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = total_frames / fps if fps > 0 else 0
    
    # Simple motion detection by frame differencing (every `sample_rate` frames)
    prev_gray = None
    motion_count = 0
    frame_idx = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % sample_rate == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if prev_gray is not None:
                diff = cv2.absdiff(prev_gray, gray)
                motion = np.mean(diff) > 5  # threshold
                if motion:
                    motion_count += 1
            prev_gray = gray
        frame_idx += 1
    
    cap.release()
    return {
        "total_frames": total_frames,
        "fps": fps,
        "duration_seconds": duration,
        "motion_frames_detected": motion_count,
        "motion_ratio": motion_count / max(1, frame_idx // sample_rate)
    }

def scan_clips():
    """Walk through clips/ folder and analyze all .mp4 files."""
    results = []
    mp4_files = list(CLIPS_DIR.rglob("*.mp4"))
    if not mp4_files:
        print("No .mp4 files found in", CLIPS_DIR)
        return results
    
    print(f"Found {len(mp4_files)} video clips. Analyzing...")
    for idx, video_path in enumerate(mp4_files, 1):
        print(f"[{idx}/{len(mp4_files)}] {video_path.name}")
        stats = analyze_video(video_path)
        stats["file_path"] = str(video_path)
        stats["relative_path"] = str(video_path.relative_to(CLIPS_DIR))
        results.append(stats)
    return results

def generate_summary(video_stats, pos_df, layout):
    """Print a summary of findings."""
    print("\n" + "="*50)
    print("STORE INTELLIGENCE SUMMARY")
    print("="*50)
    
    # Video summary
    if video_stats:
        total_videos = len(video_stats)
        avg_motion = np.mean([v.get("motion_ratio", 0) for v in video_stats])
        print(f"\n📹 Video Analysis:")
        print(f"   Total clips analyzed: {total_videos}")
        print(f"   Average motion ratio: {avg_motion:.2f}")
        print(f"   (Higher motion = more activity)")
    
    # POS summary
    if not pos_df.empty:
        print(f"\n💰 POS Transactions:")
        print(f"   Total rows: {len(pos_df)}")
        print(f"   Columns: {list(pos_df.columns)}")
        # If 'timestamp' column exists, show date range
        if 'timestamp' in pos_df.columns:
            try:
                pos_df['timestamp'] = pd.to_datetime(pos_df['timestamp'])
                print(f"   Date range: {pos_df['timestamp'].min()} to {pos_df['timestamp'].max()}")
            except:
                pass
        # If 'product_id' and 'quantity' exist
        if 'product_id' in pos_df.columns and 'quantity' in pos_df.columns:
            top_products = pos_df.groupby('product_id')['quantity'].sum().nlargest(3)
            print(f"   Top 3 products by quantity sold:")
            for prod, qty in top_products.items():
                print(f"      - {prod}: {qty}")
    
    # Layout summary
    if layout:
        print(f"\n🏪 Store Layout:")
        print(f"   Sections in layout: {list(layout.keys())}")
    
    print("\n" + "="*50)

def main():
    print("Starting Store Intelligence Analysis...\n")
    
    # Load data
    layout = load_layout()
    pos_df = load_pos()
    
    # Analyze videos
    video_stats = scan_clips()
    
    # Generate summary
    generate_summary(video_stats, pos_df, layout)
    
    # Optional: save detailed results to CSV
    if video_stats:
        output_file = "video_analysis_results.csv"
        pd.DataFrame(video_stats).to_csv(output_file, index=False)
        print(f"\n📁 Detailed video results saved to {output_file}")

if __name__ == "__main__":
    main()
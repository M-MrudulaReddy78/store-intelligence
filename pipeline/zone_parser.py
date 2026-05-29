"""
Parse store layout Excel file to extract zone polygons for each camera.
Assumes sheet contains: zone_id, camera_id, polygon_coordinates (list of x,y points)
or uses a simplified grid mapping.
"""

import pandas as pd
import json
from typing import Dict, List, Tuple, Optional
from pathlib import Path

def load_zones(excel_path: str, store_id: Optional[str] = None) -> Dict[str, List[Tuple[int, int]]]:
    """
    Load zone definitions from the store layout file.
    Returns a dictionary: zone_id -> list of (x,y) polygon points.

    Expected columns in the Excel sheet:
      - zone_id
      - camera_id
      - polygon (string "x1,y1 x2,y2 x3,y3 ..." or JSON)
    If not found, creates default zones based on typical store layout.
    """
    if not Path(excel_path).exists():
        print(f"Warning: {excel_path} not found. Using default zones.")
        return _default_zones()

    try:
        df = pd.read_excel(excel_path, sheet_name=0)
        zones = {}
        for _, row in df.iterrows():
            # Attempt to extract polygon
            poly_str = row.get("polygon") or row.get("coordinates")
            if not poly_str:
                continue
            # Parse different formats
            if isinstance(poly_str, str):
                if poly_str.startswith("[") or poly_str.startswith("{"):
                    # JSON format
                    points = json.loads(poly_str)
                else:
                    # Space-separated "x1,y1 x2,y2"
                    points = []
                    for pair in poly_str.split():
                        if ',' in pair:
                            x, y = map(int, pair.split(','))
                            points.append((x, y))
            else:
                continue
            zone_id = row.get("zone_id") or row.get("zone_name")
            if zone_id and len(points) >= 3:
                zones[zone_id] = points
        if zones:
            return zones
    except Exception as e:
        print(f"Error reading zones: {e}")

    return _default_zones()

def _default_zones() -> Dict[str, List[Tuple[int, int]]]:
    """Fallback zones when no layout file is provided."""
    return {
        "ENTRY_EXIT": [(50, 150), (300, 150), (300, 250), (50, 250)],
        "MAIN_FLOOR": [(50, 260), (500, 260), (500, 500), (50, 500)],
        "BILLING": [(500, 50), (700, 50), (700, 200), (500, 200)],
        "SKINCARE": [(200, 260), (350, 260), (350, 400), (200, 400)],
        "MAKEUP": [(360, 260), (500, 260), (500, 400), (360, 400)]
    }

def get_camera_zones(zones: Dict[str, List[Tuple[int, int]]], camera_id: str) -> Dict[str, List[Tuple[int, int]]]:
    """Filter zones that are relevant to a specific camera (if camera info present)."""
    # In a real implementation, you would have per-camera zone mapping.
    # Here we simply return all zones for simplicity.
    return zones
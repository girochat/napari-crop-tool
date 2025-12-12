# cropping/model.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import pandas as pd

from napari import Viewer
from napari.layers import Shapes


@dataclass
class CroppingModel:
    viewer: Viewer
    shapes_layer: Shapes
    scale: tuple
    out_dir: Path

    def __post_init__(self):
        # Configure shapes text labels
        self.shapes_layer.text = {
            "string": "{id}",
            "size": 12,
            "color": "white",
            "anchor": "upper_left",
            "translation": [0, 0],
        }

        # Compute default z range (in z-index units)
        min_z_um, max_z_um, _ = self.viewer.dims.range[-3]
        self.min_z = int(round(min_z_um / self.scale[0]))
        self.max_z = int(round(max_z_um / self.scale[0]))

    # ---- ROI helpers ----
    def num_rois(self) -> int:
        return len(self.shapes_layer.data)

    def get_selected_single_roi_index(self) -> int | None:
        sel = self.shapes_layer.selected_data
        if len(sel) != 1:
            return None
        return next(iter(sel))

    def get_z_start(self, idx: int) -> int:
        val = self.shapes_layer.properties["z_start_um"][idx]
        return self.min_z if np.isnan(val) else int(val / self.scale[0])

    def get_z_end(self, idx: int) -> int:
        val = self.shapes_layer.properties["z_end_um"][idx]
        return self.max_z if np.isnan(val) else int(val / self.scale[0])

    def set_z_start(self, idx: int, z_index: int):
        self.shapes_layer.properties["z_start_um"][idx] = z_index * self.scale[0]

    def set_z_end(self, idx: int, z_index: int):
        self.shapes_layer.properties["z_end_um"][idx] = z_index * self.scale[0]

    def clear_rois(self):
        self.shapes_layer.data = []
        self.shapes_layer.properties = {
            "id": [],
            "z_start_um": [],
            "z_end_um": [],
        }

    def sync_properties(self):
        """Ensure id / z_start_um / z_end_um arrays match current shapes."""
        n = self.num_rois()
        self.shapes_layer.properties = {
            "id": np.array([str(i) for i in range(n)], dtype=str),
            "z_start_um": np.array([self.get_z_start(i) for i in range(n)], dtype=float) * self.scale[0],
            "z_end_um": np.array([self.get_z_end(i) for i in range(n)], dtype=float) * self.scale[0],
        }

    # ---- saving ----
    def save_csv(self, out_path: Path, tag: str) -> Path:
        roi_df = pd.DataFrame(
            columns=["x_start_um", "y_start_um", "x_end_um", "y_end_um", "z_start_um", "z_end_um"]
        )

        for i, roi in enumerate(self.shapes_layer.data):
            z0 = self.get_z_start(i)
            z1 = self.get_z_end(i)
            roi_df.loc[i] = {
                "x_start_um": float(roi[:, 1].min()),
                "y_start_um": float(roi[:, 0].min()),
                "x_end_um": float(roi[:, 1].max()),
                "y_end_um": float(roi[:, 0].max()),
                "z_start_um": min(z0, z1),
                "z_end_um": max(z0, z1),
            }

        prefix = f"{tag}_roi_" if tag else "roi_"
        roi_df.index = [f"{prefix}{i:02}" for i in range(len(roi_df))]

        out_path.parent.mkdir(parents=True, exist_ok=True)
        roi_df.to_csv(out_path, index=True)
        return out_path


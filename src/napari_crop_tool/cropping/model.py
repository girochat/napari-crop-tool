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
            "translation": [0, 0, 0],
        }

        # Compute default range (in px index units)
        self.min_um = np.array([self.viewer.dims.range[i][0] 
                           for i in range(self.shapes_layer.ndim)])
        self.max_um = np.array([self.viewer.dims.range[i][1] 
                           for i in range(self.shapes_layer.ndim)])
        self.min_px = np.round(self.min_um / np.array(self.scale)).astype(int)
        self.max_px = np.round(self.max_um / np.array(self.scale)).astype(int)

    # ---- ROI helpers ----
    def num_rois(self) -> int:
        return len(self.shapes_layer.data)

    def get_selected_single_roi_index(self) -> int | None:
        sel = self.shapes_layer.selected_data
        if len(sel) != 1:
            return None
        return next(iter(sel))

    def get_track_axis(self, idx: int) -> int:
        val = self.shapes_layer.properties["track_axis"][idx]
        return -1 if np.isnan(val) else int(val)
    
    def get_scroll_start_px(self, idx: int) -> int | float:
        curr_axis = self.get_track_axis(idx)
        val = self.shapes_layer.properties["start_um"][idx]
        return (self.min_px[curr_axis] if np.isnan(val) 
                else int(val / self.scale[curr_axis]))

    def get_scroll_end_px(self, idx: int) -> int | float:
        curr_axis = self.get_track_axis(idx)
        val = self.shapes_layer.properties["end_um"][idx]
        return (self.max_px[curr_axis] if np.isnan(val) 
                else int(val / self.scale[curr_axis]))

    def set_scroll_start_um(self, idx: int, curr_index: int):
        curr_axis = self.get_track_axis(idx)
        self.shapes_layer.properties["start_um"][idx] = curr_index

    def set_scroll_end_um(self, idx: int, curr_index: int):
        curr_axis = self.get_track_axis(idx)
        self.shapes_layer.properties["end_um"][idx] = curr_index

    def clear_rois(self):
        self.shapes_layer.data = []
        self.shapes_layer.properties = {
            "id": np.array([], dtype=str),
            "start_um": np.array([], dtype=float),
            "end_um": np.array([], dtype=float),
            "track_axis" : np.array([], dtype=int)
        }

    def sync_properties(self):
        """Ensure id / z_start_um / z_end_um arrays match current shapes."""
        n = self.num_rois()
        self.shapes_layer.properties = {
            "id": np.array([str(i) for i in range(n)], dtype=str),
            "start_um": (np.array([self.get_scroll_start_px(i) for i in range(n)], 
                                    dtype=float) * self.scale[0]),
            "end_um": (np.array([self.get_scroll_end_px(i) for i in range(n)], 
                                  dtype=float) * self.scale[0]),
            "track_axis": (np.array([self.get_track_axis(i) for i in range(n)], 
                                  dtype=int)),
        }

    # ---- saving ----
    def save_csv(self, out_path: Path, tag: str) -> Path:
        roi_df = pd.DataFrame(
            columns=["x_start_um", "y_start_um", "x_end_um", "y_end_um", 
                     "z_start_um", "z_end_um"]
        )

        id_to_axis = {0: "z", 1: "y", 2: "x"}
        for i, roi in enumerate(self.shapes_layer.data):
            roi_dict = {}
            scroll_axis = self.shapes_layer.properties["track_axis"][i]
            for axis in (0, 1, 2):
                if axis == scroll_axis:
                    start_um = self.get_scroll_start_px(i) * self.scale[scroll_axis]
                    end_um = self.get_scroll_end_px(i) * self.scale[scroll_axis]
                    start_um = min(start_um, end_um)
                    end_um = max(start_um, end_um)
                else:
                    start_um = roi[:, axis].min()
                    end_um = roi[:, axis].max()
                
                roi_dict[f"{id_to_axis[axis]}_start_um"] = np.round(start_um, 3)
                roi_dict[f"{id_to_axis[axis]}_end_um"] = np.round(end_um, 3)
            roi_df.loc[i] = roi_dict

        prefix = f"{tag}_roi_" if tag else "roi_"
        roi_df.index = [f"{prefix}{i:02}" for i in range(len(roi_df))]

        out_path.parent.mkdir(parents=True, exist_ok=True)
        roi_df.to_csv(out_path, index=True)
        return out_path


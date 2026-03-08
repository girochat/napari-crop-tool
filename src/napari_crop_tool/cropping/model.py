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
        val = self.shapes_layer.properties["start_idx"][idx]
        return (self.min_px[curr_axis] if np.isnan(val) 
                else int(val / self.scale[curr_axis]))

    def get_scroll_end_px(self, idx: int) -> int | float:
        curr_axis = self.get_track_axis(idx)
        val = self.shapes_layer.properties["end_idx"][idx]
        return (self.max_px[curr_axis] if np.isnan(val) 
                else int(val / self.scale[curr_axis]))
    
    def get_scroll_start_um(self, idx: int) -> int | float:
        curr_axis = self.get_track_axis(idx)
        val = self.shapes_layer.properties["start_idx"][idx]
        return (self.min_um[curr_axis] if np.isnan(val) 
                else val)

    def get_scroll_end_um(self, idx: int) -> int | float:
        curr_axis = self.get_track_axis(idx)
        val = self.shapes_layer.properties["end_idx"][idx]
        return (self.max_um[curr_axis] if np.isnan(val) 
                else val)

    def set_scroll_start_um(self, idx: int, curr_index: int):
        props = dict(self.shapes_layer.properties)
        start_idx = props["start_idx"].copy()
        start_idx[idx] = curr_index
        props["start_idx"] = start_idx
        self.shapes_layer.properties = props

    def set_scroll_end_um(self, idx: int, curr_index: int):
        props = dict(self.shapes_layer.properties)
        end_idx = props["end_idx"].copy()
        end_idx[idx] = curr_index
        props["end_idx"] = end_idx
        self.shapes_layer.properties = props

    def clear_rois(self):
        self.shapes_layer.selected_data = set()
        self.shapes_layer.data = []
        #self.shapes_layer.properties = {
        #    "id": np.array([], dtype=str),
        #    "start_idx": np.array([], dtype=float),
        #    "end_idx": np.array([], dtype=float),
        #    "track_axis" : np.array([], dtype=float)
        #}

    def delete_roi(self, idx: int):
        data = list(self.shapes_layer.data)

        if idx < 0 or idx >= len(data):
            return

        del data[idx]
        self.shapes_layer.data = data
        self.sync_properties()

    def set_rectangle_size(self, idx: int, size_x: float | None = None, size_y: float | None = None):
        data = list(self.shapes_layer.data)
        roi = np.array(data[idx], dtype=float)
        curr_axis = self.get_track_axis(idx)
        axis1 = self.viewer.dims.order[-2]
        axis2 = self.viewer.dims.order[-1]

        if roi.shape[0] != 4:
            raise ValueError("Selected ROI is not a rectangle.")

        # assuming vertices define an axis-aligned rectangle
        y_min = roi[:, axis1].min()
        y_max = roi[:, axis1].max()
        x_min = roi[:, axis2].min()
        x_max = roi[:, axis2].max()

        if size_y is None:
            size_y = y_max - y_min
        if size_x is None:
            size_x = x_max - x_min

        curr_axis = self.get_track_axis(idx)
        slice_idx = self.viewer.dims.current_step[curr_axis]

        new_roi = roi.copy()

        # keep other dims unchanged, replace Y/X box
        # axis order assumed Z,Y,X for 3D
        new_roi[:, curr_axis] = slice_idx

        # rectangle corners
        # top-left, top-right, bottom-right, bottom-left
        new_roi[0, axis1] = y_min
        new_roi[0, axis2] = x_min

        new_roi[1, axis1] = y_min
        new_roi[1, axis2] = x_min + size_x

        new_roi[2, axis1] = y_min + size_y
        new_roi[2, axis2] = x_min + size_x

        new_roi[3, axis1] = y_min + size_y
        new_roi[3, axis2] = x_min

        data[idx] = new_roi
        self.shapes_layer.data = data
        self.shapes_layer.selected_data = {idx}

    def sync_properties(self):
        """Ensure id / start_idx / end_idx arrays match current shapes."""
        n = self.num_rois()
        self.shapes_layer.properties = {
            "id": np.array([str(i) for i in range(n)], dtype=str),
            "start_idx": (np.array([self.get_scroll_start_um(i) for i in range(n)], 
                                    dtype=float)),
            "end_idx": (np.array([self.get_scroll_end_um(i) for i in range(n)], 
                                  dtype=float)),
            "track_axis": (np.array([self.get_track_axis(i) for i in range(n)], 
                                  dtype=float)),
        }

    # ---- saving ----
    def save_csv(self, out_path: Path, tag: str) -> Path:
        roi_df = pd.DataFrame(
            columns=["x_start", "y_start", "x_end", "y_end", 
                     "z_start", "z_end"]
        )

        id_to_axis = {0: "z", 1: "y", 2: "x"}
        for i, roi in enumerate(self.shapes_layer.data):
            roi_dict = {}
            scroll_axis = self.shapes_layer.properties["track_axis"][i]
            for axis in (0, 1, 2):
                if axis == scroll_axis:
                    start_um = self.get_scroll_start_um(i)
                    end_um = self.get_scroll_end_um(i)
                else:
                    start_um = roi[:, axis].min()
                    end_um = roi[:, axis].max()
                
                roi_dict[f"{id_to_axis[axis]}_start"] = np.round(min(start_um, end_um), 3)
                roi_dict[f"{id_to_axis[axis]}_end"] = np.round(max(start_um, end_um), 3)
            roi_df.loc[i] = roi_dict

        prefix = f"{tag}_roi_" if tag else "roi_"
        roi_df.index = [f"{prefix}{i:02}" for i in range(len(roi_df))]

        out_path.parent.mkdir(parents=True, exist_ok=True)
        roi_df.to_csv(out_path, index=True)
        return out_path
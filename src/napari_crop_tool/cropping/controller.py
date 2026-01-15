# cropping/controller.py
from __future__ import annotations
from pathlib import Path
from magicgui.widgets import Label

from .model import CroppingModel
from .gui import CroppingGUI

from napari.utils.notifications import (
    show_info,
    show_warning,
    show_error,
)

class CroppingController:
    """Wiring (events + callbacks) for ROI cropping."""
    def __init__(
        self, 
        model: CroppingModel, 
        gui: CroppingGUI
    ):
        self.model = model
        self.gui = gui

        # Wire napari + gui events
        self.model.shapes_layer.events.data.connect(self.update_rois)
        self.model.viewer.dims.events.point.connect(self._project_shapes)
        self.gui.set_start_btn.clicked.connect(self.on_set_start)
        self.gui.set_stop_btn.clicked.connect(self.on_set_stop)
        self.gui.clear_rois_btn.clicked.connect(self.on_clear_rois)
        self.gui.save_btn.clicked.connect(self.on_save)

        # Initial paint
        self.update_rois()

    def _project_shapes(self):
        curr_shapes_data = self.model.shapes_layer.data
        n = self.model.num_rois()
        curr_axis = self.model.viewer.dims.order[0]
        for i in range(n):
            scroll_roi_axis = self.model.get_track_axis(i)
            if curr_axis == scroll_roi_axis:
                slice_idx = self.model.viewer.dims.current_step[curr_axis]
                curr_shapes_data[i][:,curr_axis] = slice_idx        
        self.model.shapes_layer.data = curr_shapes_data

    def update_rois(self, *args):
        n = self.model.num_rois()

        if len(self.gui.rois_gui) < n:
            n_new_rois = n - len(self.gui.rois_gui)
            scroll_axis = self.model.viewer.dims.order[0]
            for i in range(1, n_new_rois+1):
                self.model.shapes_layer.properties["track_axis"][-i] = scroll_axis
                self.model.shapes_layer.properties["end_um"][-i] = self.model.max_um[scroll_axis]
                self.model.shapes_layer.properties["start_um"][-i] = self.model.min_um[scroll_axis]

        # Ensure we have enough labels
        while len(self.gui.rois_gui) < n:
            self.gui.rois_gui.append(Label())

        while len(self.gui.rois_gui) > n:
            self.gui.rois_gui.pop()        
            
        # Keep properties consistent
        self.model.sync_properties()

        # Update display text
        idx_to_axis = {0: "Z", 1: "Y", 2: "X"}
        for i in range(n):

            curr_axis = self.model.get_track_axis(i)
            axis = idx_to_axis[curr_axis]
            self.gui.rois_gui[i].value = (
                f"<b>ROI {i:02}</b>: "
                f"{axis} start={self.model.get_scroll_start_px(i)}, "
                f"{axis} end={self.model.get_scroll_end_px(i)}"
            )

    def on_set_start(self):
        idx = self.model.get_selected_single_roi_index()
        if idx is None:
            show_warning("Select exactly one cropping box.")
            return
        
        curr_axis = self.model.get_track_axis(idx)
        slice_idx = self.model.viewer.dims.current_step[curr_axis]
        self.model.set_scroll_start_um(idx, slice_idx)
        self.update_rois()

    def on_set_stop(self):
        idx = self.model.get_selected_single_roi_index()
        if idx is None:
            show_warning("Select exactly one cropping box.")
            return
        
        curr_axis = self.model.get_track_axis(idx)
        slice_idx = self.model.viewer.dims.current_step[curr_axis]
        self.model.set_scroll_end_um(idx, slice_idx)
        self.update_rois()

    def on_clear_rois(self):
        self.model.clear_rois()
        show_info("ROI list cleared!")

    def on_save(self):
        if self.model.num_rois() == 0:
            show_warning("No cropping box drawn!")
            return

        out_path = Path(self.gui.file_edit.value)
        if out_path.suffix.lower() != ".csv":
            show_warning("Only CSV saving is implemented for now.")
            return

        saved = self.model.save_csv(out_path, self.gui.tag_edit.value)
        show_info(f"ROI coordinates saved to {saved.name}!")

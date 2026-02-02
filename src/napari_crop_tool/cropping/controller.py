# cropping/controller.py
from __future__ import annotations
from pathlib import Path

from .model import CroppingModel
from .gui import CroppingGUIQt

from napari.utils.notifications import (
    show_info,
    show_warning
)

class CroppingController:
    """Wiring (events + callbacks) for ROI cropping."""
    def __init__(
        self, 
        model: CroppingModel, 
        gui: CroppingGUIQt,
    ):
        self.model = model
        self.gui = gui
        self.last_selected = set()

        # Wire napari + gui events
        self.model.shapes_layer.events.data.connect(self.update_rois)
        self.model.shapes_layer.events.data.connect(self._keep_last_selected)
        self.model.viewer.dims.events.point.connect(self._project_shapes)
        self.gui.btn_set_start.clicked.connect(self.on_set_start)
        self.gui.btn_set_stop.clicked.connect(self.on_set_stop)
        self.gui.btn_clear_rois.clicked.connect(self.on_clear_rois)
        self.gui.btn_save.clicked.connect(self.on_save)

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
        self.model.shapes_layer.selected_data = self.last_selected

    def _keep_last_selected(self, *args):
        if self.model.shapes_layer.selected_data != set():
            self.last_selected = set(self.model.shapes_layer.selected_data)

    def update_rois(self, *args):
        n = self.model.num_rois()

        if (self.gui.roi_list_layout.count()-1) < n:
            n_new_rois = n - (self.gui.roi_list_layout.count()-1)
            scroll_axis = self.model.viewer.dims.order[0]
            for i in range(1, n_new_rois+1):
                self.model.shapes_layer.properties["track_axis"][-i] = scroll_axis
                self.model.shapes_layer.properties["end_idx"][-i] = self.model.max_um[scroll_axis]
                self.model.shapes_layer.properties["start_idx"][-i] = self.model.min_um[scroll_axis]   
            
        # Keep properties consistent
        self.model.sync_properties()

        # Update display text
        idx_to_axis = {0: "Z", 1: "Y", 2: "X"}
        roi_list = []
        for i in range(n):

            curr_axis = self.model.get_track_axis(i)
            axis = idx_to_axis[curr_axis]
            roi_list.append(
                f"<b>ROI {i:02}</b>: "
                f"{axis} start={self.model.get_scroll_start_um(i)}, "
                f"{axis} end={self.model.get_scroll_end_um(i)}"
            )
        self.gui.set_roi_labels(roi_list)

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
        self.last_selected = set()
        self.model.clear_rois()
        show_info("ROI list cleared!")

    def on_save(self):
        if self.model.num_rois() == 0:
            show_warning("No cropping box drawn!")
            return

        out_path = Path(self.gui.text_file.text())
        if out_path.suffix.lower() != ".csv":
            show_warning("Only CSV saving is implemented for now.")
            return

        saved = self.model.save_csv(out_path, self.gui.text_tag.text())
        show_info(f"ROI coordinates saved to {saved.name}!")
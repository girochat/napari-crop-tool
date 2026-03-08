# cropping/controller.py
from __future__ import annotations
from pathlib import Path
from contextlib import contextmanager

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
        self.selected_roi_idx: int | None = None
        self._restoring_selection = False
        self._updating_list_selection = False
        self._suspend_roi_sync = False
        self._prev_num_rois = self.model.num_rois()

        # Wire napari + gui events
        self.model.shapes_layer.events.data.connect(self._on_shapes_data_changed)
        self.model.viewer.dims.events.point.connect(self._project_shapes)
        self.gui.btn_set_start.clicked.connect(self.on_set_start)
        self.gui.btn_set_stop.clicked.connect(self.on_set_stop)
        self.gui.btn_clear_rois.clicked.connect(self.on_clear_rois)
        self.gui.btn_save.clicked.connect(self.on_save)
        self.gui.roi_selected.connect(self.on_roi_selected_from_list)
        self.gui.delete_selected_clicked.connect(self.on_delete_selected)
        self.gui.set_rectangle_size_clicked.connect(self.on_set_rectangle_size)
        self.model.shapes_layer.events.highlight.connect(self._on_shapes_highlight_changed)

        # Initial paint
        self.update_rois()

    @contextmanager
    def _suspend_sync(self):
        old = self._suspend_roi_sync
        self._suspend_roi_sync = True
        try:
            yield
        finally:
            self._suspend_roi_sync = old

    def _on_shapes_data_changed(self, *args):
        if self._suspend_roi_sync:
            return
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
        with self._suspend_sync():    
            self.model.shapes_layer.data = curr_shapes_data
        self._apply_selected_roi()
        self.model.shapes_layer.refresh()

    def _apply_selected_roi(self):
        if self._restoring_selection:
            return

        self._restoring_selection = True
        try:
            n = self.model.num_rois()
            idx = self.selected_roi_idx

            if idx is None or idx < 0 or idx >= n:
                self.selected_roi_idx = None
                self.model.shapes_layer.selected_data = set()
                self.gui.set_selected_roi_row(None)
                return

            self.model.shapes_layer.selected_data = {idx}
            self.gui.set_selected_roi_row(idx)
        finally:
            self._restoring_selection = False

    def _set_selected_roi(self, idx: int | None):
        self.selected_roi_idx = idx
        self._apply_selected_roi()

    def _on_shapes_highlight_changed(self, event=None):
        if self._restoring_selection:
            return

        sel = set(self.model.shapes_layer.selected_data)

        # user clicked a ROI on the canvas
        if len(sel) == 1:
            idx = next(iter(sel))
            self.selected_roi_idx = idx
            self.gui.set_selected_roi_row(idx)
            return

        # napari cleared selection (e.g. click outside / mouse leaves / redraw)
        if len(sel) == 0 and self.selected_roi_idx is not None:
            self._apply_selected_roi()

    def update_rois(self, *args):
        n = self.model.num_rois()
        scroll_axis = self.model.viewer.dims.order[0]

        props = dict(self.model.shapes_layer.properties)
        if (self.gui.roi_list.count()) < n:
            n_new_rois = n - (self.gui.roi_list.count())
            scroll_axis = self.model.viewer.dims.order[0]
            props = dict(self.model.shapes_layer.properties)
            track_axis = props["track_axis"].copy()
            start_idx = props["start_idx"].copy()
            end_idx = props["end_idx"].copy()
            id_track = props["id"].copy()
            for i in range(1, n_new_rois+1):
                id_track[-i] = f"{n_new_rois + i}"
                track_axis[-i] = scroll_axis
                start_idx[-i] = self.model.min_um[scroll_axis]
                end_idx[-i] = self.model.max_um[scroll_axis]

            props["id"] = id_track
            props["track_axis"] = track_axis
            props["start_idx"] = start_idx
            props["end_idx"] = end_idx

            self.model.shapes_layer.properties = props

        self.model.sync_properties()

        idx_to_axis = {0: "Z", 1: "Y", 2: "X"}
        roi_list = []
        for i in range(n):
            curr_axis = self.model.get_track_axis(i)
            axis = idx_to_axis[curr_axis]
            roi_list.append(
                f"ROI {i:02}: "
                f"{axis} start={self.model.get_scroll_start_um(i)}, "
                f"{axis} end={self.model.get_scroll_end_um(i)}"
            )
        self.gui.set_roi_labels(roi_list)

        # if a new ROI was just created, select the newest one
        if n > self._prev_num_rois:
            self.selected_roi_idx = n - 1

        # if selected ROI got deleted, clamp it
        if self.selected_roi_idx is not None and self.selected_roi_idx >= n:
            self.selected_roi_idx = n - 1 if n > 0 else None

        self._prev_num_rois = n
        self._apply_selected_roi()

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

        out_path = Path(self.gui.txt_file.text())
        if out_path.suffix.lower() != ".csv":
            show_warning("Only CSV saving is implemented for now.")
            return

        saved = self.model.save_csv(out_path, self.gui.txt_tag.text())
        show_info(f"ROI coordinates saved to {saved.name}!")

    def on_roi_selected_from_list(self, row: int):
        if self._restoring_selection:
            return
        if 0 <= row < self.model.num_rois():
            self._set_selected_roi(row)

    def on_delete_selected(self):
        idx = self.selected_roi_idx
        if idx is None:
            show_warning("Select exactly one ROI to delete.")
            return
        
        n_before = self.model.num_rois()
        if n_before <= 1:
            new_idx = None
        elif idx < n_before - 1:
            new_idx = idx
        else:
            new_idx = n_before - 2

        # Clear controller + napari selection BEFORE removing data
        self.selected_roi_idx = None
        self._restoring_selection = True
        try:
            self.model.shapes_layer.selected_data = set()
            self.gui.set_selected_roi_row(None)
        finally:
            self._restoring_selection = False

        # Delete ROI
        with self._suspend_sync():
            self.model.delete_roi(idx)

        # Choose new selection after deletion
        self.selected_roi_idx = new_idx

        self.update_rois()
        self._apply_selected_roi()
        self.model.shapes_layer.refresh()

    def on_set_rectangle_size(self):
        idx = self.model.get_selected_single_roi_index()
        if idx is None:
            show_warning("Select exactly one ROI.")
            return

        try:
            size_x, size_y = self.gui.get_requested_rectangle_size()
        except ValueError:
            show_warning("Rectangle size must be numeric.")
            return

        if size_x is None and size_y is None:
            show_warning("Enter at least one size.")
            return

        try:
            self.model.set_rectangle_size(idx, size_x=size_x, size_y=size_y)
        except ValueError as e:
            show_warning(str(e))
            return

        self.update_rois()
        show_info(f"Updated ROI {idx:02} size.")
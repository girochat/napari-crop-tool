# cropping/controller.py
from __future__ import annotations
from pathlib import Path
import numpy as np
from contextlib import contextmanager
from qtpy.QtWidgets import QMessageBox

from .model import CroppingModel
from .gui import CroppingGUIQt

from napari.utils.notifications import (
    show_info,
    show_warning
)

# Axis letters used in the ROI list labels (3D layers).
_AXIS_NAMES = {0: "Z", 1: "Y", 2: "X"}


class CroppingController:
    """Wiring (events + callbacks) for ROI cropping.

    Selection policy
    ----------------
    `self.selected_roi_idx` is the single source of truth for "which ROI is
    the user working on".  It is pushed to the shapes layer and to the list
    widget by `_apply_selected_roi()`.

    The layer is kept at a *single* selection at all times.  This is not just
    cosmetic: `Shapes.interaction_box()` returns None when two or more shapes
    are selected and none of them lies in the currently displayed slice, while
    `selected_data` stays non-empty.  napari's own mouse-press handler then
    does `layer._selected_box[Box.CENTER]` and raises
    `TypeError: 'NoneType' object is not subscriptable`.  A single-element
    selection always yields a valid box.
    """

    def __init__(
        self,
        model: CroppingModel,
        gui: CroppingGUIQt,
        data_boundary: tuple,
    ):
        self.model = model
        self.gui = gui
        self.data_boundary = data_boundary
        self.selected_roi_idx: int | None = None
        self._restoring_selection = False
        self._suspend_roi_sync = False
        self._prev_num_rois = self.model.num_rois()

        # Wire napari + gui events
        self.model.shapes_layer.events.data.connect(self._on_shapes_data_changed)
        self.model.shapes_layer.events.highlight.connect(self._on_shapes_highlight_changed)
        self.model.viewer.dims.events.point.connect(self._project_shapes)
        self.gui.btn_set_start.clicked.connect(self.on_set_start)
        self.gui.btn_set_stop.clicked.connect(self.on_set_stop)
        self.gui.btn_clear_rois.clicked.connect(self.on_clear_rois)
        self.gui.btn_save.clicked.connect(self.on_save)
        self.gui.roi_selected.connect(self.on_roi_selected_from_list)
        self.gui.delete_selected_clicked.connect(self.on_delete_selected)
        self.gui.set_rectangle_size_clicked.connect(self.on_set_rectangle_size)
        self.model.shapes_layer.events.mode.connect(self._fix_cursor)

        # Initial paint
        self.update_rois()


    def dispose(self):
        """Disconnect from napari so a closed session stops receiving events."""
        try:
            self.model.viewer.dims.events.point.disconnect(self._project_shapes)
            self.model.shapes_layer.events.data.disconnect(self._on_shapes_data_changed)
            self.model.shapes_layer.events.highlight.disconnect(
                self._on_shapes_highlight_changed
            )
            self.model.shapes_layer.events.mode.disconnect(self._fix_cursor)
        except (TypeError, ValueError, RuntimeError):
            # Layer already removed / emitter already gone.
            pass

    # ---------- re-entrancy guards ----------
    @contextmanager
    def _suspend_sync(self):
        """Ignore layer events caused by own edits.

        Covers both `events.data` and `events.highlight`: rebuilding the shape
        data resets napari's selection. This should not be mistaken for the 
        user deselecting an ROI.
        """
        old = self._suspend_roi_sync
        self._suspend_roi_sync = True
        try:
            yield
        finally:
            self._suspend_roi_sync = old

    def _fix_cursor(self, event=None):
        if self.model.shapes_layer.cursor == 'cross':
            self.model.shapes_layer.cursor = 'crosshair'

    # ---------- selection ----------
    def _apply_selected_roi(self):
        """Push `self.selected_roi_idx` to the layer and the list widget."""
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

            # Always a single index
            self.model.shapes_layer.selected_data = {idx}
            self.gui.set_selected_roi_row(idx)
        finally:
            self._restoring_selection = False

    def _set_selected_roi(self, idx: int | None):
        self.selected_roi_idx = idx
        self._apply_selected_roi()

    def _on_shapes_highlight_changed(self, event=None):
        """Follow the canvas selection; only intervene on multi-selections."""
        if self._restoring_selection or self._suspend_roi_sync:
            return
        # While a shape is being drawn the selection belongs to napari's
        # creation generator; touching it here breaks the gesture.
        if self.model.shapes_layer._is_creating:
            return

        sel = set(self.model.shapes_layer.selected_data)

        # napari allows multi-selection (rubber band, Shift+click, "A").
        # but this plugin is single-ROI because a multi
        # selection whose shapes are all off-slice breaks napari's own
        # mouse handling.
        if len(sel) > 1:
            idx = self.selected_roi_idx if self.selected_roi_idx in sel else min(sel)
            self.selected_roi_idx = int(idx)
            self._apply_selected_roi()
            return

        # User clicked an ROI on the canvas.
        if len(sel) == 1:
            idx = int(next(iter(sel)))
            if idx != self.selected_roi_idx:
                self.selected_roi_idx = idx
                self.gui.set_selected_roi_row(idx)
            return

        # User deselected (click on empty canvas, Escape)
        if self.selected_roi_idx is not None:
            self.selected_roi_idx = None
            self.gui.set_selected_roi_row(None)

    # ---------- layer sync ----------
    def _on_shapes_data_changed(self, *args):
        if self._suspend_roi_sync:
            return
        self.update_rois()

    def _project_shapes(self, event=None):
        """Move every ROI tracking the scrolled axis onto the current slice."""
        layer = self.model.shapes_layer
        if self._suspend_roi_sync or self.model.num_rois() == 0:
            return
            
        # Never rebuild the data while napari is mid-gesture
        if layer._is_creating or layer._is_moving:
            return

        curr_shapes_data = self.model.shapes_layer.data
        curr_axis = self.model.viewer.dims.order[0]
        slice_idx = layer.world_to_data(self.model.viewer.dims.point)[curr_axis]

        moved = False
        for i in range(self.model.num_rois()):
            if self.model.get_track_axis(i) == curr_axis:
                curr_shapes_data[i][:, curr_axis] = slice_idx
                moved = True

        if not moved:
            return

        with self._suspend_sync():
            self.model.shapes_layer.data = curr_shapes_data
        self._apply_selected_roi()
        self.model.shapes_layer.refresh()

    def update_rois(self, *args):
        n = self.model.num_rois()
        scroll_axis = self.model.viewer.dims.order[0]

        # Stamp defaults on ROIs that were just drawn on the canvas.
        # The reference is the painted list, not `_prev_num_rois`.
        props = dict(self.model.shapes_layer.properties)
        if (self.gui.roi_list.count()) < n:
            n_new_rois = n - (self.gui.roi_list.count())
            scroll_axis = self.model.viewer.dims.order[0]
            props = dict(self.model.shapes_layer.properties)
            track_axis = props["track_axis"].copy()
            start_idx = props["start_idx"].copy()
            end_idx = props["end_idx"].copy()
            id_track = props["id"].copy()
            for i in range(1, n_new_rois + 1):
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

        # Ensure drawn ROI is among target layer bounds
        hi = self.data_boundary
        data = self.model.shapes_layer.data
        clipped = [np.clip(d, (0, 0, 0), hi) for d in data]
        if any(not np.array_equal(a, b) for a, b in zip(data, clipped)):
            with self._suspend_sync():
                self.model.shapes_layer.data = clipped

        roi_list = []
        for i in range(n):
            curr_axis = self.model.get_track_axis(i)
            axis = _AXIS_NAMES.get(curr_axis, f"axis {curr_axis}")
            roi_list.append(
                f"ROI {i:02}:\n"
                f"    {axis} slice: {self.model.get_scroll_start_px(i):d}-"
                f"{self.model.get_scroll_end_px(i):d} "
                f"    (in world units: {self.model.get_scroll_start_um(i):.2f}-"
                f"{self.model.get_scroll_end_um(i):.2f})"
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

    # ---------- actions ----------
    def on_set_start(self):
        idx = self.selected_roi_idx
        if idx is None:
            show_warning("Select exactly one cropping box.")
            return

        curr_axis = self.model.get_track_axis(idx)
        slice_idx = self.model.viewer.dims.point[curr_axis]
        self.model.set_scroll_start_um(idx, slice_idx)
        self.update_rois()

    def on_set_stop(self):
        idx = self.selected_roi_idx
        if idx is None:
            show_warning("Select exactly one cropping box.")
            return

        curr_axis = self.model.get_track_axis(idx)
        slice_idx = self.model.viewer.dims.point[curr_axis]
        self.model.set_scroll_end_um(idx, slice_idx)
        self.update_rois()

    def on_clear_rois(self):
        self.selected_roi_idx = None

        with self._suspend_sync():
            self.model.clear_rois()

        self.update_rois()
        self.model.shapes_layer.refresh()
        show_info("ROI list cleared!")

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

        # Drop the napari selection *before* removing the shape, so no stale
        # index survives the data change.
        with self._suspend_sync():
            self.model.shapes_layer.selected_data = set()
            self.model.delete_roi(idx)

        self.selected_roi_idx = new_idx

        self.update_rois()
        self.model.shapes_layer.refresh()
        show_info(f"ROI {idx:02} deleted!")

    def on_set_rectangle_size(self):
        idx = self.selected_roi_idx
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
            with self._suspend_sync():
                self.model.set_rectangle_size(idx, size_x=size_x, size_y=size_y)
        except ValueError as e:
            show_warning(str(e))
            return

        self.update_rois()
        self.model.shapes_layer.refresh()
        show_info(f"Updated ROI {idx:02} size.")

    def on_roi_selected_from_list(self, row: int):
        if self._restoring_selection or self._suspend_roi_sync:
            return
        if 0 <= row < self.model.num_rois():
            self._set_selected_roi(row)

    def on_save(self):
        if self.model.num_rois() == 0:
            show_warning("No cropping box drawn!")
            return

        out_path = Path(self.gui.txt_file.text())
        if out_path.suffix.lower() != ".csv":
            show_warning("Only CSV saving is implemented for now.")
            return

        if out_path.exists():
            reply = QMessageBox.question(
                self.gui,
                "Overwrite file?",
                f"File '{out_path.name}' already exists.\n\n"
                "Do you want to overwrite it?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        saved = self.model.save_csv(out_path, self.gui.txt_tag.text())
        show_info(f"ROI coordinates saved to {saved.name}!")
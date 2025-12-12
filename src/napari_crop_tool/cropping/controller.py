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
        self.gui.set_start_btn.clicked.connect(self.on_set_start)
        self.gui.set_stop_btn.clicked.connect(self.on_set_stop)
        self.gui.clear_rois_btn.clicked.connect(self.on_clear_rois)
        self.gui.save_btn.clicked.connect(self.on_save)

        # Initial paint
        self.update_rois()

    def update_rois(self, *args):
        n = self.model.num_rois()

        # Ensure we have enough labels
        while len(self.gui.rois_gui) < n:
            self.gui.rois_gui.append(Label())

        while len(self.gui.rois_gui) > n:
            self.gui.rois_gui.pop()

        # Keep properties consistent
        self.model.sync_properties()

        # Update display text
        for i in range(n):
            self.gui.rois_gui[i].value = (
                f"<b>ROI {i:02}</b>: "
                f"Z start={self.model.get_z_start(i)}, "
                f"Z end={self.model.get_z_end(i)}"
            )

    def on_set_start(self):
        idx = self.model.get_selected_single_roi_index()
        if idx is None:
            show_warning("Select exactly one cropping box.")
            return

        z = self.model.viewer.dims.current_step[-3]
        self.model.set_z_start(idx, z)
        self.update_rois()

    def on_set_stop(self):
        idx = self.model.get_selected_single_roi_index()
        if idx is None:
            show_warning("Select exactly one cropping box.")
            return

        z = self.model.viewer.dims.current_step[-3]
        self.model.set_z_end(idx, z)
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
        #self.gui.set_message(f"Saved ROI coordinates to {saved.name}")
        show_info(f"ROI coordinates saved to {saved.name}!")

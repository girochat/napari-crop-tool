# layer_selection/controller.py
from __future__ import annotations

from pathlib import Path
import numpy as np
from napari import Viewer
from napari.layers import Layer, Image, Labels

from .model import LayerSelectionModel
from .gui import LayerSelectionGUIQt
from .._utils import _get_scale_from_layer

from ..cropping.model import CroppingModel
from ..cropping.gui import CroppingGUIQt
from ..cropping.controller import CroppingController

class LayerSelectionControllerQt():

    def __init__(self, viewer: Viewer):
        self.viewer = viewer
        self.model = LayerSelectionModel(viewer=viewer)
        self.layer_gui = LayerSelectionGUIQt()

        self.cropping_gui = CroppingGUIQt()
        self.cropping_controller: CroppingController | None = None

        # GUI events
        self.layer_gui.btn_confirm.clicked.connect(self.on_confirm)
        self.layer_gui.btn_reset.clicked.connect(self.on_reset)

        # Viewer events: keep choices in sync
        layers = viewer.layers
        layers.events.inserted.connect(self.refresh_layer_choices)
        layers.events.removed.connect(self.refresh_layer_choices)
        layers.events.moved.connect(self.refresh_layer_choices)
        layers.events.reordered.connect(self.refresh_layer_choices)
        layers.events.changed.connect(self.refresh_layer_choices)

        self.refresh_layer_choices()

    # ---------- actions ----------
    def on_confirm(self, _=None):
        selected: Layer | None = self.layer_gui.selected_layer()
        if selected is None:
            return

        self.model.target_layer = selected

        self.layer_gui.set_status("Target layer selected! Press 'Reset' to change layer.")
        self.layer_gui.set_confirm_state(visible=False, enabled=False)
        self.layer_gui.set_reset_state(visible=True, enabled=True)

        self._enter_cropping_session()

    def on_reset(self, _=None):
        self.layer_gui.set_status("Select a target layer to crop.")
        self.layer_gui.set_confirm_state(visible=True, 
                                         enabled=(self.layer_gui.layer_list.count() > 0 and 
                                                  self.layer_gui.layer_list.currentIndex() >= 0))
        self.layer_gui.set_reset_state(visible=False, enabled=False)

        self._exit_cropping_session()

    # ---------- viewer sync ----------
    def refresh_layer_choices(self, _=None):
        combo = self.layer_gui.layer_list

        # try keep same object selected
        prev_layer = self.layer_gui.selected_layer()

        combo.blockSignals(True)
        combo.clear()

        for layer in self.viewer.layers:
            if isinstance(layer, (Image, Labels)):
                combo.addItem(layer.name, layer)

        # restore selection by identity
        if prev_layer is not None:
            for i in range(combo.count()):
                if combo.itemData(i) is prev_layer:
                    combo.setCurrentIndex(i)
                    break

        combo.blockSignals(False)
        self.layer_gui.btn_confirm.setEnabled(combo.count() > 0 and combo.currentIndex() >= 0)

    # ---------- session lifecycle ----------
    def _enter_cropping_session(self):
        assert self.model.target_layer is not None
        layer = self.model.target_layer

        # Create shapes layer tailored to dimensionality
        props = (
            {"track_axis": np.array([], dtype=int),
            "start_idx": np.array([], dtype=float), 
            "end_idx": np.array([], dtype=float), 
            "id": np.array([], dtype=str)}
            if layer.ndim > 2
            else {"id": np.array([], dtype=str)}
        )
        self.model.shapes_layer = self.model.viewer.add_shapes(
            ndim=layer.ndim,
            name="Cropping ToolBox",
            properties=props,
        )
    
        scale = _get_scale_from_layer(layer)
        out_dir = Path(layer.source.path) if getattr(layer, "source", None) \
                   else Path.cwd()

        self.cropping_gui.set_output_path(Path(out_dir, "roi_coords.csv"))
        self.cropping_gui.set_cropping_enabled(True)

        cropping_model = CroppingModel(
            viewer=self.model.viewer,
            shapes_layer=self.model.shapes_layer,
            scale=scale,
            out_dir=out_dir,
        )
        self.cropping_controller = CroppingController(
            cropping_model, 
            self.cropping_gui)

    def _exit_cropping_session(self):
        self.cropping_gui.set_cropping_enabled(False)
        self.cropping_gui.clear_roi_labels()

        self.model.remove_shapes_if_any()
        self.model.clear_session_state()
        self.cropping_controller = None

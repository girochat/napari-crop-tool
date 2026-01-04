# layer_selection/controller.py
from __future__ import annotations

from pathlib import Path
import numpy as np
from napari import Viewer
from napari.layers import Layer

from .model import LayerSelectionModel
from .gui import LayerSelectionGUI
from .._utils import _layer_choices, _get_scale_from_layer

from ..cropping.model import CroppingModel
from ..cropping.gui import CroppingGUI
from ..cropping.controller import CroppingController

class LayerSelectionController():
    """
    Wires viewer events + GUI events, and spawns a cropping session.
    """

    def __init__(self, viewer: Viewer):
        self.viewer = viewer
        self.model = LayerSelectionModel(viewer=viewer)
        self.gui = LayerSelectionGUI(viewer=viewer, layer_choices=_layer_choices)

        self._cropping_gui: CroppingGUI | None = None
        self._cropping_controller: CroppingController | None = None

        # GUI events
        self.gui.btn_confirm.changed.connect(self.on_confirm)
        self.gui.btn_reset.changed.connect(self.on_reset)

        # Viewer events: keep choices in sync
        layers = viewer.layers
        layers.events.inserted.connect(self.refresh_layer_choices)
        layers.events.removed.connect(self.refresh_layer_choices)
        layers.events.moved.connect(self.refresh_layer_choices)
        layers.events.reordered.connect(self.refresh_layer_choices)
        layers.events.changed.connect(self.refresh_layer_choices)

    # ---------- viewer sync ----------
    def refresh_layer_choices(self, _=None):
        self.gui.layer_list.reset_choices()

        # If we are in selection mode, keep confirm enabled/disabled correct
        if self.gui.btn_confirm.visible:
            self.gui.btn_confirm.enabled = (self.gui.layer_list.value is not None)
        else:
            # In cropping mode: if user changed layer list, require reset
            self.gui.set_status("Layer choice changed. Press 'Reset' to change layer.")
            has_choice = (self.gui.layer_list.value is not None)
            self.gui.set_reset_state(visible=has_choice, enabled=has_choice)

    # ---------- actions ----------
    def on_confirm(self, _=None):
        selected: Layer | None = self.gui.layer_list.value
        if selected is None:
            return

        self.model.target_layer = selected

        self.gui.set_status("Target layer selected! Press 'Reset' to change layer.")
        self.gui.set_confirm_state(visible=False, enabled=False)
        self.gui.set_reset_state(visible=True, enabled=True)

        self._enter_cropping_session()

    def on_reset(self, _=None):
        self.gui.set_status("Select a target layer to crop.")
        self.gui.set_confirm_state(visible=True, enabled=(self.gui.layer_list.value is not None))
        self.gui.set_reset_state(visible=False, enabled=False)

        self._exit_cropping_session()

    # ---------- session lifecycle ----------
    def _enter_cropping_session(self):
        assert self.model.target_layer is not None
        layer = self.model.target_layer

        # Create shapes layer tailored to dimensionality
        props = (
            {"track_axis": np.array([], dtype=int),
            "start_um": np.array([], dtype=float), 
            "end_um": np.array([], dtype=float), 
            "id": np.array([], dtype=str)}
            if layer.ndim > 2
            else {"id": np.array([], dtype=str)}
        )
        self.model.shapes_layer = self.model.viewer.add_shapes(
            ndim=layer.ndim,
            name="Cropping Box",
            properties=props,
        )
    
        scale = _get_scale_from_layer(layer)
        out_dir = Path(layer.source.path).parent

        cropping_model = CroppingModel(
            viewer=self.model.viewer,
            shapes_layer=self.model.shapes_layer,
            scale=scale,
            out_dir=out_dir,
        )
        cropping_gui = CroppingGUI(out_dir=out_dir)
        cropping_controller = CroppingController(cropping_model, cropping_gui)

        self._cropping_gui = cropping_gui
        self._cropping_controller = cropping_controller

        self.gui.extend([self.gui.separator, cropping_gui.container])

    def _exit_cropping_session(self):
        # remove cropping GUI from parent GUI
        if self._cropping_gui is not None:
            self.gui.remove(self._cropping_gui.container)
            self._cropping_gui = None
            self._cropping_controller = None

        # remove shapes + clear model state
        self.model.remove_shapes_if_any()
        self.model.clear_session_state()

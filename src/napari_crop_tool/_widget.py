from collections.abc import Sequence
from typing import Any

from magicgui.widgets import Container, ComboBox, Button, Label
from napari import Viewer
from napari.layers import Image, Labels, Layer, Shapes
from pathlib import Path
import numpy as np
from qtpy.QtWidgets import QPushButton, QToolButton

from ._utils import build_cropping_widget, _get_scale_from_layer, _layer_choices

class LayerChoiceWidget(ComboBox):
    def __init__(self, 
                 viewer: Viewer, 
                 choices: Sequence[dict[str, Layer]] = None,
                 **base_widget_kwargs: dict[str, Any]):
        self.viewer = viewer
        super().__init__(choices=choices, **base_widget_kwargs)


class CropToolWidget(Container):
    def __init__(self, viewer: Viewer):
        super().__init__(layout="vertical")
        self.viewer = viewer
        self.target_layer: Layer | None = None
        self.shapes_layer: Shapes | None = None
        self.cropping_ui: Container | None = None

        # Static UIs
        self.header = Label(value="<b>Layer Selection</b>")
        self.status = Label(value="Select a target layer to crop.")
        self.space = Label(value="---------------------")

        # Control UIs
        self.layer_list = LayerChoiceWidget(
            viewer=self.viewer,
            name="layers",
            label="Target layer", 
            choices=_layer_choices)
        
        self.btn_confirm = Button(label="Confirm", 
                                  enabled=(self.layer_list.value != None))
        self.btn_reset = Button(label="Reset", enabled=False, visible=False)

        self.selection_ui = Container(widgets = [self.layer_list, 
                                         self.btn_confirm, 
                                         self.btn_reset], 
                              layout="vertical")

        self.btn_confirm.changed.connect(self._on_confirm)
        self.btn_reset.changed.connect(self._on_reset)

        # Keep layer choices in sync with the viewer
        self.viewer.layers.events.inserted.connect(self._refresh_layer_choices)
        self.viewer.layers.events.removed.connect(self._refresh_layer_choices)
        self.viewer.layers.events.moved.connect(self._refresh_layer_choices)
        self.viewer.layers.events.reordered.connect(self._refresh_layer_choices)
        self.viewer.layers.events.changed.connect(self._refresh_layer_choices)

        # Assemble widgets
        self.extend([self.header, self.status, self.selection_ui])

    # ----------- switching UI methods ----------
    def _enter_layer_selection(self):
        
        # Clean up shapes & embedded UI
        self._remove_shapes_if_any()
        self.remove(self.cropping_ui)
        self.cropping_ui = None
        self.target_layer = None
        self.btn_reset.enabled = False
        self.btn_reset.visible = False
        self.btn_confirm.enabled = (self.layer_list.value != None)

    def _enter_cropping(self):
        assert self.target_layer is not None

        # Make shapes tailored to target dimensionality
        scale = _get_scale_from_layer(self.target_layer)
        props = {"z_start_um": [], 
                 "z_end_um": [], 
                 "id": np.array([], dtype=str)} if self.target_layer.ndim > 2 else {"id": np.array([], dtype=str)}
        self.shapes_layer = self.viewer.add_shapes(name="Cropping Box", 
                                                   properties=props)

        # Get default output directory
        out_dir = Path(self.target_layer.source.path).parent

        # Get magicgui container for cropping widget
        self.cropping_ui = build_cropping_widget(self.viewer, 
                                                 self.shapes_layer, 
                                                 scale, 
                                                 out_dir)
        
        self.extend([self.space, self.cropping_ui])
        
        #self.cropping_ui = self.viewer.window.add_dock_widget(cropping_ui, 
        #                                          name="Cropping Toolbox",
        #                                          tabify=True,
        #                                          area="right")

    # ---------- button handler methods ----------
    def _on_confirm(self, _=None):
        selected = self.layer_list.value

        # If no layer selected, do nothing
        if selected is None:
            return
        
        self.target_layer = selected
        self.status.value = "Target layer selected! Press 'Reset' to change layer."
        self.btn_confirm.enabled = False
        self.btn_confirm.visible = False
        self.btn_reset.visible = True
        self.btn_reset.enabled = True
        self._enter_cropping()

    def _on_reset(self, _=None):
        #self.viewer.window.remove_dock_widget(self.cropping_ui)
        #self.remove(self.cropping_ui)
        #self.cropping_ui = None
        self.status.value = "Select a target layer to crop."
        self.btn_confirm.enabled = True
        self.btn_confirm.visible = True
        self.btn_reset.enabled = False
        self.btn_reset.visible = False
        self._enter_layer_selection()

    # ---------- helper methods ----------
    def _remove_shapes_if_any(self):
        if self.shapes_layer is not None and self.shapes_layer in self.viewer.layers:
            self.viewer.layers.remove(self.shapes_layer)
        self.shapes_layer = None

    def _refresh_layer_choices(self, _=None):
        self.layer_list.reset_choices()
        if self.btn_confirm.visible:
            self.btn_confirm.enabled = (self.layer_list.value != None)
        else:
            self.status.value = "Layer choice changed. Press 'Reset' to change layer."
            self.btn_reset.visible = (self.layer_list.value != None)
            self.btn_reset.enabled = (self.layer_list.value != None)

from collections.abc import Sequence
from typing import Any

from magicgui.widgets import Container, ComboBox, Button, Label
from napari import Viewer
from napari.layers import Image, Labels, Layer, Shapes
from pathlib import Path

from ._utils import build_cropping_widget, _get_scale_from_layer, _layer_choices

class LayerChoiceWidget(ComboBox):
    def __init__(self, 
                 viewer: Viewer, 
                 choices: Sequence[dict[str, Layer]] = None,
                 **base_widget_kwargs: dict[str, Any]):
        self.viewer = viewer
        super().__init__(choices=choices, **base_widget_kwargs)


class CropRoiWidget(Container):
    def __init__(self, viewer: Viewer):
        super().__init__(layout="vertical")
        self.viewer = viewer
        self.target_layer: Layer | None = None
        self.shapes_layer: Shapes | None = None
        self.cropping_ui: Container | None = None

        # Static UIs
        self.header = Label(value="<b>Crop ROI Tool</b>")
        self.status = Label(value="Select a target layer to crop.")
        self.space = Label(value="-------------------")

        # Control UIs
        self.layer_list = LayerChoiceWidget(
            viewer=self.viewer,
            name="layers",
            label="Target layer", 
            choices=_layer_choices)
        
        self.btn_confirm = Button(label="Confirm", 
                                  enabled=(self.layer_list.value != None))
        self.btn_reset = Button(label="Reset", enabled=False)

        self.body = Container(widgets = [self.layer_list, 
                                         self.btn_confirm, 
                                         self.btn_reset, 
                                         self.space], 
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
        self.extend([self.header, self.status, self.body])

    # ----------- switching UI methods ----------
    def _enter_layer_selection(self):
        
        # Clean up shapes & embedded UI
        self._remove_shapes_if_any()
        self.body.remove(self.cropping_ui)
        self.target_layer = None
        self.btn_reset.enabled = False
        self.btn_confirm.enabled = (self.layer_list.value != None)

    def _enter_cropping(self):
        assert self.target_layer is not None

        # Make shapes tailored to target dimensionality
        scale = _get_scale_from_layer(self.target_layer)
        props = {"z_start_um": [], "z_end_um": []} if self.target_layer.ndim > 2 else {}
        self.shapes_layer = self.viewer.add_shapes(name="Cropping Box", 
                                                   properties=props)
        self.btn_confirm.enabled = False

        # Get default output directory
        out_dir = Path(self.target_layer.source.path).parent

        # Get magicgui container for cropping widget
        self.cropping_ui = build_cropping_widget(self.viewer, 
                                                 self.shapes_layer, 
                                                 scale, 
                                                 out_dir)
        
        dock = self.viewer.window.add_dock_widget(self.cropping_ui, 
                                                  name="Cropping Toolbox")
        dock.setFloating(True)   # immediately pop it out
        dock.raise_()

        #self.cropping_ui.show()
        #self.body.append(self.cropping_ui)

    # ---------- button handler methods ----------
    def _on_confirm(self, _=None):
        selected = self.layer_list.value

        # If no layer selected, do nothing
        if selected is None:
            return
        
        self.target_layer = selected
        self.status.value = "Target layer selected! Press 'Reset' to change layer."
        self.btn_confirm.enabled = False
        self.btn_reset.enabled = True
        self._enter_cropping()

    def _on_reset(self, _=None):
        self.status.value = "Select a target layer to crop."
        self.btn_confirm.enabled = True
        self.btn_reset.enabled = False
        self._enter_layer_selection()

    # ---------- helper methods ----------
    def _remove_shapes_if_any(self):
        if self.shapes_layer is not None and self.shapes_layer in self.viewer.layers:
            self.viewer.layers.remove(self.shapes_layer)
        self.shapes_layer = None

    def _refresh_layer_choices(self, _=None):
        self.layer_list.reset_choices()
        self.btn_confirm.enabled = (self.layer_list.value != None)
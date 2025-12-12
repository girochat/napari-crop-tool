# layer_selection/gui.py
from magicgui.widgets import Container, ComboBox, Button, Label
from napari import Viewer
from collections.abc import Sequence
from napari.layers import Layer
from typing import Any

class LayerSelectionGUI(Container):
    """GUI only (magicgui widgets)."""
    def __init__(self, viewer: Viewer, layer_choices):
        super().__init__(layout="vertical")
        self.viewer = viewer

        self.header = Label(value="<b>Layer Selection</b>")
        self.status = Label(value="Select a target layer to crop.")
        self.separator = Label(value="---------------------------")

        self.layer_list = LayerChoiceWidget(
            name="layers",
            label="Target layer",
            choices=layer_choices,
            viewer=self.viewer,
        )

        self.btn_confirm = Button(label="Confirm", 
                                  enabled=(self.layer_list.value is not None))
        self.btn_reset = Button(label="Reset", 
                                enabled=False, visible=False)

        #self.controls = Container(
        #    widgets=[self.layer_list, self.btn_confirm, self.btn_reset],
        #    layout="vertical"
        #)
        self.extend([self.header, self.status, 
                     self.layer_list, self.btn_confirm, self.btn_reset])

    # Small GUI helpers (practical MVC)
    def set_status(self, text: str):
        self.status.value = text

    def set_confirm_state(self, *, visible: bool, enabled: bool):
        self.btn_confirm.visible = visible
        self.btn_confirm.enabled = enabled

    def set_reset_state(self, *, visible: bool, enabled: bool):
        self.btn_reset.visible = visible
        self.btn_reset.enabled = enabled


class LayerChoiceWidget(ComboBox):
    def __init__(self, 
                 viewer: Viewer, 
                 choices: Sequence[dict[str, Layer]] = None,
                 **base_widget_kwargs: dict[str, Any]):
        self.viewer = viewer
        super().__init__(choices=choices, **base_widget_kwargs)
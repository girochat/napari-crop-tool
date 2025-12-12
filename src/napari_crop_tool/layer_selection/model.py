# layer_selection/model.py
from __future__ import annotations
from dataclasses import dataclass
from napari import Viewer
from napari.layers import Layer, Shapes

@dataclass
class LayerSelectionModel:
    """State for the layer-selection + session lifecycle."""
    viewer: Viewer
    target_layer: Layer | None = None
    shapes_layer: Shapes | None = None

    def clear_session_state(self):
        self.target_layer = None
        self.shapes_layer = None

    def remove_shapes_if_any(self):
        if self.shapes_layer is not None and self.shapes_layer in self.viewer.layers:
            self.viewer.layers.remove(self.shapes_layer)
        self.shapes_layer = None

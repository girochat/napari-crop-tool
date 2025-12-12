# widget.py
from napari import Viewer
from magicgui.widgets import Container
from .layer_selection.controller import LayerSelectionController

class MainGUI(Container):
    def __init__(self, viewer: Viewer):
        super().__init__(layout="vertical")
        self.viewer = viewer
        self.start_controller = LayerSelectionController(viewer)
        self.extend([self.start_controller.gui])

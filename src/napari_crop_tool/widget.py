from qtpy.QtWidgets import (
    QWidget, QVBoxLayout
)

from napari import Viewer
from .layer_selection.controller import LayerSelectionControllerQt


class MainWidgetQt(QWidget):
    def __init__(self, viewer: Viewer):
        super().__init__()
        self.viewer = viewer
        self.entry_controller = LayerSelectionControllerQt(viewer)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 10)
        layout.addWidget(self.entry_controller.layer_gui)
        layout.addWidget(self.entry_controller.cropping_gui, stretch=1)

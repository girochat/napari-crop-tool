from qtpy.QtWidgets import (
    QWidget, QVBoxLayout
)

from napari import Viewer
from napari.settings import get_settings
from .layer_selection.controller import LayerSelectionControllerQt


class MainWidgetQt(QWidget):
    def __init__(self, viewer: Viewer):
        super().__init__()
        self.viewer = viewer
        self.entry_controller = LayerSelectionControllerQt(viewer)

        # Save current napari highlight setting
        highlight_settings = get_settings().appearance.highlight
        self._previous_highlight_color = (
            highlight_settings.highlight_color
        )

        # Use transparent value for highlight color (avoid big anisotropic displays)
        highlight_settings.highlight_color = [0, 0, 0, 0]

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 10)
        layout.addWidget(self.entry_controller.layer_gui)
        layout.addWidget(self.entry_controller.cropping_gui, stretch=1)

    def closeEvent(self, event):
        """Restore napari highlight settings on close."""
        highlight_settings = get_settings().appearance.highlight
        highlight_settings.highlight_color = self._previous_highlight_color
        super().closeEvent(event)
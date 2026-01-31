# layer_selection/gui.py
from __future__ import annotations

from qtpy.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QComboBox,
    QPushButton, QSizePolicy
)
from qtpy.QtCore import Signal

class LayerSelectionGUIQt(QWidget):  

    confirm_clicked = Signal()
    reset_clicked = Signal()

    def __init__(self):#, viewer: Viewer, layer_choices):
        super().__init__()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        
        # ---------- Section 1: Layer Selection ----------
        self.grp_layer = QGroupBox("Layer Selection")
        layer_layout = QVBoxLayout(self.grp_layer)

        self.lbl_status = QLabel("Select a target layer to crop.")
        self.lbl_status.setWordWrap(True)

        self.layer_list = QComboBox()
        self.layer_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        btn_row = QHBoxLayout()
        self.btn_confirm = QPushButton("Confirm")
        self.btn_reset = QPushButton("Reset")
        self.btn_reset.setVisible(False)  # only visible after confirm
        btn_row.addWidget(self.btn_confirm)
        btn_row.addWidget(self.btn_reset)
        btn_row.addStretch(1)

        layer_layout.addWidget(self.lbl_status)
        layer_layout.addWidget(self.layer_list)
        layer_layout.addLayout(btn_row)

        root.addWidget(self.grp_layer)

        self.btn_confirm.clicked.connect(self.confirm_clicked)
        self.btn_reset.clicked.connect(self.reset_clicked)

    def set_status(self, text: str) -> None:
        self.lbl_status.setText(text)

    def set_confirm_state(self, *, visible: bool, enabled: bool) -> None:
        self.btn_confirm.setVisible(visible)
        self.btn_confirm.setEnabled(enabled)

    def set_reset_state(self, *, visible: bool, enabled: bool) -> None:
        self.btn_reset.setVisible(visible)
        self.btn_reset.setEnabled(enabled)

    def selected_layer(self):
        i = self.layer_list.currentIndex()
        if i < 0:
            return None
        return self.layer_list.itemData(i)
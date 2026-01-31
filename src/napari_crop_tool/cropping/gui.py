# cropping/gui.py
from __future__ import annotations

from pathlib import Path
from typing import Optional
from qtpy.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QScrollArea, QLineEdit, QFileDialog, QSizePolicy
)
from qtpy.QtCore import Qt, Signal

class CroppingGUIQt(QWidget):

    set_start_clicked = Signal()
    set_stop_clicked = Signal()
    clear_rois_clicked = Signal()
    save_clicked = Signal()


    def __init__(self, out_dir: Optional[Path] = None):
        super().__init__()

        self.out_dir = out_dir

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # ---------- Section 2: ROI Cropping ----------
        self.grp_roi = QGroupBox("ROI Cropping")
        roi_layout = QVBoxLayout(self.grp_roi)

        # Scroll area for ROI list
        self.roi_list_container = QWidget()
        self.roi_list_layout = QVBoxLayout(self.roi_list_container)
        self.roi_list_layout.setContentsMargins(0, 0, 0, 0)
        self.roi_list_layout.setSpacing(4)
        self.roi_list_layout.addStretch(1)  # keeps ROIs pinned at top

        self.roi_scroll = QScrollArea()
        self.roi_scroll.setWidgetResizable(True)
        self.roi_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.roi_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.roi_scroll.setWidget(self.roi_list_container)

        roi_buttons_row = QHBoxLayout()
        self.btn_set_start = QPushButton("Set Slice Start from Cursor")
        self.btn_set_stop = QPushButton("Set Slice End from Cursor")
        roi_buttons_row.addWidget(self.btn_set_start)
        roi_buttons_row.addWidget(self.btn_set_stop)

        self.btn_clear_rois = QPushButton("Clear ROI list")

        roi_layout.addWidget(self.roi_scroll, stretch=1)
        roi_layout.addLayout(roi_buttons_row)
        roi_layout.addWidget(self.btn_clear_rois)

        # ---------- Section 3: Saving ----------# 
        self.grp_save = QGroupBox("Saving")
        save_layout = QVBoxLayout(self.grp_save)

        self.txt_tag = QLineEdit()
        self.txt_tag.setPlaceholderText("ROI Tag (optional)")

        file_row = QHBoxLayout()
        self.txt_file = QLineEdit()
        self.btn_browse = QPushButton("Browse…")
        self.btn_browse.setFixedWidth(90)
        file_row.addWidget(self.txt_file, stretch=1)
        file_row.addWidget(self.btn_browse)

        self.btn_save = QPushButton("Save")

        save_layout.addWidget(QLabel("ROI Tag (optional)"))
        save_layout.addWidget(self.txt_tag)
        save_layout.addWidget(QLabel("Output CSV"))
        save_layout.addLayout(file_row)
        save_layout.addWidget(self.btn_save)

        root.addWidget(self.grp_roi, stretch=1)
        root.addWidget(self.grp_save)

        self.set_cropping_enabled(False)

        # Wire UI signals -> panel signals (controller handles logic)
        self.btn_set_start.clicked.connect(self.set_start_clicked)
        self.btn_set_stop.clicked.connect(self.set_stop_clicked)
        self.btn_clear_rois.clicked.connect(self.clear_rois_clicked)
        self.btn_save.clicked.connect(self.save_clicked)
        self.btn_browse.clicked.connect(self._browse_csv)

    def get_tag(self) -> str:
        return self.txt_tag.text().strip()

    def get_output_path(self) -> Path:
        return Path(self.txt_file.text()).expanduser()

    def set_output_path(self, p: Path) -> None:
        self.txt_file.setText(str(p))

    def set_cropping_enabled(self, enabled: bool) -> None:
        self.grp_roi.setEnabled(enabled)
        self.grp_save.setEnabled(enabled)

    def clear_roi_labels(self) -> None:
        # remove all labels except the final stretch
        while self.roi_list_layout.count() > 1:
            item = self.roi_list_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def set_roi_labels(self, roi_lines: list[str]) -> None:
        self.clear_roi_labels()
        for roi in roi_lines:
            lab = QLabel(roi)
            lab.setTextFormat(Qt.RichText)
            lab.setWordWrap(True)
            lab.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.roi_list_layout.insertWidget(self.roi_list_layout.count() - 1, lab)

    def _browse_csv(self) -> None:
        start = self.txt_file.text().strip() or str(Path.home())
        fn, _ = QFileDialog.getSaveFileName(self, "Save ROI CSV", start, "CSV (*.csv)")
        if fn:
            if not fn.lower().endswith(".csv"):
                fn += ".csv"
            self.txt_file.setText(fn)
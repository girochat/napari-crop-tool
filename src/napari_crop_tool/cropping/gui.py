# cropping/gui.py
from __future__ import annotations

from pathlib import Path
from typing import Optional
from qtpy.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QLineEdit, QFileDialog, 
    QListWidget, QListWidgetItem
)
from qtpy.QtCore import Signal

class CroppingGUIQt(QWidget):

    set_start_clicked = Signal()
    set_stop_clicked = Signal()
    clear_rois_clicked = Signal()
    save_clicked = Signal()
    roi_selected = Signal(int)
    delete_selected_clicked = Signal()
    set_rectangle_size_clicked = Signal()


    def __init__(self, out_dir: Optional[Path] = None):
        super().__init__()

        self.out_dir = out_dir

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # ------ ROI Cropping Section ----------
        self.grp_roi = QGroupBox("ROI Cropping")
        roi_layout = QVBoxLayout(self.grp_roi)

        # Scroll area for ROI list
        self.roi_list = QListWidget()
        self.roi_list.setSelectionMode(QListWidget.SingleSelection)
        roi_layout.addWidget(self.roi_list, stretch=1)

        # ROI set start/end buttons
        roi_buttons_row = QHBoxLayout()
        self.btn_set_start = QPushButton("Set Slice Start from Cursor")
        self.btn_set_stop = QPushButton("Set Slice End from Cursor")
        roi_buttons_row.addWidget(self.btn_set_start)
        roi_buttons_row.addWidget(self.btn_set_stop)

        # ROI delete button
        edit_row = QHBoxLayout()
        self.btn_delete_selected = QPushButton("Delete selected ROI")
        edit_row.addWidget(self.btn_delete_selected)

        # ROI size buttons
        size_row = QHBoxLayout()
        self.txt_size_x = QLineEdit()
        self.txt_size_y = QLineEdit()
        self.txt_size_x.setPlaceholderText(f"Horizontal size")
        self.txt_size_y.setPlaceholderText(f"Vertical size")
        self.btn_set_rectangle_size = QPushButton("Set auto rectangle size")
        size_row.addWidget(self.txt_size_x)
        size_row.addWidget(self.txt_size_y)
        size_row.addWidget(self.btn_set_rectangle_size)

        # Clear ROI list button
        self.btn_clear_rois = QPushButton("Clear ROI list")

        roi_layout.addLayout(roi_buttons_row)
        roi_layout.addLayout(edit_row)
        roi_layout.addLayout(size_row)
        roi_layout.addWidget(self.btn_clear_rois)

        # ---------- Saving Section --------- 
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
        self.roi_list.currentRowChanged.connect(self.roi_selected)
        self.btn_delete_selected.clicked.connect(self.delete_selected_clicked)
        self.btn_set_rectangle_size.clicked.connect(self.set_rectangle_size_clicked)

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
        self.roi_list.clear()

    def set_roi_labels(self, roi_lines: list[str]) -> None:
        current_row = self.roi_list.currentRow()
        self.roi_list.blockSignals(True)
        self.roi_list.clear()
        for roi in roi_lines:
            item = QListWidgetItem(roi)
            #item.setText(roi)
            self.roi_list.addItem(item)
        if 0 <= current_row < self.roi_list.count():
            self.roi_list.setCurrentRow(current_row)
        self.roi_list.blockSignals(False)

    def set_selected_roi_row(self, idx: int | None) -> None:
        self.roi_list.blockSignals(True)
        if idx is None or idx < 0 or idx >= self.roi_list.count():
            self.roi_list.clearSelection()
            self.roi_list.setCurrentRow(-1)
        else:
            self.roi_list.setCurrentRow(idx)
            item = self.roi_list.item(idx)
            if item is not None:
                self.roi_list.scrollToItem(item)
        self.roi_list.blockSignals(False)

    def get_requested_rectangle_size(self) -> tuple[float | None, float | None]:
        def _parse(lineedit: QLineEdit):
            txt = lineedit.text().strip()
            if not txt:
                return None
            return float(txt)

        return (_parse(self.txt_size_x), _parse(self.txt_size_y))

    def _browse_csv(self) -> None:
        start = self.txt_file.text().strip() or str(Path.home())
        fn, _ = QFileDialog.getSaveFileName(self, "Save ROI CSV", start, "CSV (*.csv)")
        if fn:
            if not fn.lower().endswith(".csv"):
                fn += ".csv"
            self.txt_file.setText(fn)
# cropping/gui.py
from pathlib import Path
from magicgui.widgets import Container, Label, LineEdit, FileEdit, PushButton


class CroppingGUI():
    """GUI only (widgets)."""
    def __init__(self, out_dir: Path):
        self.rois_gui = Container()

        self.roi_title = Label(value="<b>ROI Cropping</b>")
        self.set_start_btn = PushButton(label="Set Slice Start from Cursor")
        self.set_stop_btn = PushButton(label="Set Slice End from Cursor")
        self.clear_rois_btn = PushButton(label="Clear ROI list")

        self.separator = Label(value="---------------------------")

        self.save_title = Label(value="<b>Saving</b>")
        self.tag_edit = LineEdit(value="", label="ROI Tag (optional)")
        self.file_edit = FileEdit(mode="w", value=Path(out_dir, "roi_coords.csv"))
        self.save_btn = PushButton(label="Save")

        self.container = Container(
            widgets=[
                Container(
                    widgets=[
                        self.roi_title,
                        self.rois_gui],
                    layout="vertical"
                ),
                Container(
                    widgets=[
                        self.set_start_btn, self.set_stop_btn], 
                    layout="horizontal",
                ),
                Container(
                    widgets=[
                        self.clear_rois_btn,
                        self.separator,
                        self.save_title,
                        self.tag_edit,
                        self.file_edit,
                        self.save_btn],
                    layout="vertical",
                )
            ],
            layout="vertical",
        )


from typing import Optional
from magicgui.widgets import Container, PushButton, Label
from napari import Viewer
from napari.layers import Shapes, Layer
import numpy as np

def build_cropping_widget(
        viewer: Viewer,
        shapes_layer: Shapes,
        scale: tuple) -> Container:
    """
    Build a cropping widget for selecting one or several region of interest (ROI) 
    in the image.

    Parameters:
        viewer (Viewer): The napari viewer instance.
        shapes_layer (Shapes): The napari shapes layer instance.
        scale (tuple): The scale of the image.

    Returns:
        Container: The cropping widget container.
    """
    
    # State to store current slicing axis and shape range records
    saved_state = {
        "rois": {},
    }
    min_z_um, max_z_um, _ = viewer.dims.range[0]
    min_z = round(min_z_um / scale[0])
    max_z = round(max_z_um / scale[0])

    # UI elements
    get_slice_btn = PushButton(label="Get Z Slice Range")
    slice_label = Label(value="Current Z slice range:")
    start_label = Label(value=f"Z start:")
    stop_label = Label(value=f"Z end:")
    set_start_btn = PushButton(label="Set Z Start from Cursor")
    set_stop_btn = PushButton(label="Set Z End from Cursor")
    confirm_btn = PushButton(label="Confirm", visible=False)
    reset_btn = PushButton(label="Reset", visible=False)
    save_btn = PushButton(label="Save Crop Coordinates (All)")
    message_label = Label(value=f"")

    # Get current slice range when get button is clicked
    def on_get_slice_clicked():
        message_label.value = ""
        if len(shapes_layer.data) == 0:
            message_label.value = "No cropping box drawn!"
            return
        selected_rois = shapes_layer.selected_data
        if len(selected_rois) == 0:
            message_label.value = "No cropping box selected!"
            return
        if len(selected_rois) > 1:
            message_label.value = "Please select only one cropping box!"
            return
        shape_idx = list(selected_rois)[0]
        setattr(get_slice_btn, "shape_idx", shape_idx)
        if np.isnan(shapes_layer.properties["z_start_um"][shape_idx]):
            shapes_layer.properties["z_start_um"][shape_idx] = min_z_um
            shapes_layer.properties["z_end_um"][shape_idx] = max_z_um
        start_label.value = f"Z start: {int(shapes_layer.properties['z_start_um'][shape_idx] / scale[0])}"
        stop_label.value = f"Z end: {int(shapes_layer.properties['z_end_um'][shape_idx] / scale[0])}"

    get_slice_btn.changed.connect(on_get_slice_clicked)

    # Assign slice start/stop from current slider
    def on_set_start():
        message_label.value = ""
        value = viewer.dims.current_step[0]
        selected_rois = shapes_layer.selected_data
        if len(selected_rois) == 0:
            message_label.value = "\nNo cropping box selected!"
            restart_slice()
            return
        if len(selected_rois) > 1:
            message_label.value = "\nPlease select only one cropping box!"
            restart_slice()
            return
        shape_idx = getattr(get_slice_btn, "shape_idx")
        shapes_layer.properties["z_start_um"][shape_idx] = value * scale[0]
        start_label.value = f"Z start: {int(shapes_layer.properties['z_start_um'][shape_idx] / scale[0])}"
        set_start_btn.enabled = False
        if not (set_start_btn.enabled) and not (set_stop_btn.enabled):
            reset_btn.visible = True
            confirm_btn.visible = True

    def on_set_stop():
        message_label.value = ""
        value = viewer.dims.current_step[0]
        selected_rois = shapes_layer.selected_data
        if len(selected_rois) == 0:
            message_label.value = "\nNo cropping box selected!"
            restart_slice()
            return
        if len(selected_rois) > 1:
            message_label.value = "\nPlease select only one cropping box!"
            restart_slice()
            return
        shape_idx = getattr(get_slice_btn, "shape_idx")
        shapes_layer.properties["z_end_um"][shape_idx] = value * scale[0]
        stop_label.value = f"Z end: {int(shapes_layer.properties['z_end_um'][shape_idx] / scale[0])}"
        set_stop_btn.enabled = False
        if not (set_start_btn.enabled) and not (set_stop_btn.enabled):
            confirm_btn.visible = True
            reset_btn.visible = True

    def restart_slice():
        start_label.value = f"Z start:"
        stop_label.value = f"Z end:"
        set_stop_btn.enabled = True
        set_start_btn.enabled = True
        setattr(get_slice_btn, "shape_idx", None)
        confirm_btn.visible = False
        reset_btn.visible = False

    # Confirm the current slice range on confirm button click
    def on_confirm():
        message_label.value = ""
        selected_rois = shapes_layer.selected_data
        if len(selected_rois) == 0:
            message_label.value = "\nNo cropping box selected!"
            restart_slice()
            return
        if len(selected_rois) > 1:
            message_label.value = "\nPlease select only one cropping box!"
            restart_slice()
            return
        restart_slice()

    # Re-enable the start/stop buttons to reset the slice range
    def reset_slice():
        shape_idx = getattr(get_slice_btn, "shape_idx")
        start_label.value = f"Z start: {int(shapes_layer.properties['z_start_um'][shape_idx] / scale[0])}"
        stop_label.value = f"Z end: {int(shapes_layer.properties['z_end_um'][shape_idx] / scale[0])}"
        set_start_btn.enabled = True
        set_stop_btn.enabled = True

    set_start_btn.clicked.connect(on_set_start)
    set_stop_btn.clicked.connect(on_set_stop)
    confirm_btn.clicked.connect(on_confirm)
    reset_btn.clicked.connect(reset_slice)

    # Save the currently selected shape and slice range on save button click
    def on_save():
        if len(shapes_layer.data) == 0:
            print("No cropping box drawn!")
            return

        for shape_idx in range(len(shapes_layer.data)):
            #shape_idx = list(selected)[0]
            roi = shapes_layer.data[shape_idx]
            if np.isnan(shapes_layer.properties["z_start_um"][shape_idx]):
                z_start = min_z
            else:
                z_start = shapes_layer.properties["z_start_um"][shape_idx]
            if np.isnan(shapes_layer.properties["z_end_um"][shape_idx]):
                z_end = max_z
            else:
                z_end = shapes_layer.properties["z_end_um"][shape_idx]
            roi_data = {
                "x_start_um": min(roi[:,1]), 
                "y_start_um": min(roi[:,0]),
                "x_end_um": max(roi[:,1]), 
                "y_end_um": max(roi[:,0]),
                "z_start_um": z_start,
                "z_end_um": z_end
            }

            # Save/update in session memory
            saved_state["rois"][shape_idx] = roi_data

    save_btn.clicked.connect(on_save)

    # Compose everything in a single container widget
    crop_widget = Container(
        widgets=[
            Container(
                widgets=[ 
                    get_slice_btn,
                    Container(widgets=[
                        slice_label,
                        start_label,
                        stop_label,
                        set_start_btn,
                        set_stop_btn,
                        confirm_btn,
                        reset_btn],
                        layout="vertical",
                        ),
                    save_btn]),
            message_label
        ],
        layout="vertical",
        labels=True,
    )
    crop_widget.rois = saved_state["rois"]

    return crop_widget

def _get_scale_from_layer(
    layer: Layer
) -> tuple:
    """
    Returns a full-length scale tuple (z,y,x) for 3D or (y,x) for 2D.
    Falls back to ones if scale isn't set.
    """
    scale = getattr(layer, "scale", None)
    if scale is None:
        data_ndim = getattr(layer, "ndim", 2)
        return tuple([1.0] * data_ndim)
    
    return tuple(float(s) for s in scale)

def define_crop_on_layer(
    viewer: Viewer,
    target_layer: Layer,
    shapes_name: str = "Cropping Box",
) -> Container:
    """
    Attach the cropping shapes + widget to the running viewer, using the
    scale and dimensionality of the selected target_layer.
    """

    # Determine the reference scale from the selected layer
    scale = _get_scale_from_layer(target_layer)
    
    # Create one shapes layer for drawing crop boxes (XY rectangles)
    shapes_layer = viewer.add_shapes(
        name=shapes_name, 
        properties={
            "z_start_um": [], 
            "z_end_um": []
        } if target_layer.ndim > 2 else {}
    )

    # Build and dock cropping widget
    widget = build_cropping_widget(
        viewer, 
        shapes_layer, 
        scale
    )
    viewer.window.add_dock_widget(
        widget, 
        name="Cropping Toolbox", 
        area="right"
    )
    return widget
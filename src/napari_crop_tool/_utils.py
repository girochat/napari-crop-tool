import numpy as np
import pandas as pd
from pathlib import Path
from magicgui.widgets import Container, Label, PushButton, FileEdit, LineEdit
from napari import Viewer
from napari.layers import Image, Labels, Layer, Shapes
from collections.abc import Sequence

def _layer_choices(widget) -> Sequence[dict[str, Layer]]:
    pairs = []
    if len(widget.viewer.layers) == 0:
        pairs.append(("- - -", None))
    else:
        for layer in widget.viewer.layers:
            if isinstance(layer, Image | Labels):
                pairs.append((layer.name, layer))
    return pairs

def build_cropping_widget(
    viewer: Viewer, 
    shapes_layer: Shapes, 
    scale: tuple,
    out_dir: str
) -> Container:
    """Build a cropping widget.

    The cropping widget allows the user to define one or several region of interests
    (ROI) in the image for which the cropping coordinates will be saved.

    Parameters:
        viewer (Viewer): The napari viewer instance.
        shapes_layer (Shapes): The napari shapes layer instance.
        scale (tuple): The scale of the image.
        out_dir (str): The default output directory for saving the cropped coordinates.

    Returns:
        Container: The cropping widget container.
    """
    saved_n = 0
    shapes_layer.text = {
        "string": "{id}", 
        "size": 12,
        "color": "white",
        "anchor": "upper_left",
        "translation": [0, 0],
        }

    min_z_um, max_z_um, _ = viewer.dims.range[-3]
    min_z = round(min_z_um / scale[0])
    max_z = round(max_z_um / scale[0])

    # UI elements
    rois_gui = Container()
    roi_title = Label(value="<b>ROI Cropping</b>")
    set_start_btn = PushButton(label="Set Z Start from Cursor")
    set_stop_btn = PushButton(label="Set Z End from Cursor")
    space_label = Label(value="---------------------")
    save_title = Label(value="<b>Saving</b>")
    file_edit = FileEdit(mode="w", value=Path(out_dir, "roi_coords.csv"))
    file_edit.min_width = 100
    #save_coords_btn = PushButton(label="Save ROI coordinates (CSV)")
    #save_image_btn = PushButton(label="Save ROI cropped image(s) (PNG, TIFF, JPEG...)")
    tag_edit = LineEdit(value="", label="ROI Tag (e.g. DEJ, muscle...) (optional)")
    tag_edit.min_width = 100
    save_btn = PushButton(label="Save")
    message_label = Label(value="")

    def update_roi_gui():
        n = len(shapes_layer.data)
        n_saved_rois = len(rois_gui)
        if n == n_saved_rois:
            pass
        else:
            props = dict(shapes_layer.properties)
            ids = []
            z_starts = []
            z_ends = []
            for shape_idx in range(len(shapes_layer.data)):
                ids.append(str(shape_idx))
                print(shapes_layer.properties)
                if np.isnan(shapes_layer.properties["z_start_um"][shape_idx]):
                    z_starts.append(min_z)
                else:
                    z_starts.append(int(shapes_layer.properties["z_start_um"][shape_idx] / scale[0]))

                if np.isnan(shapes_layer.properties["z_end_um"][shape_idx]):
                    z_ends.append(max_z)
                else:
                    z_ends.append(int(shapes_layer.properties["z_end_um"][shape_idx] / scale[0]))
                if len(rois_gui) > shape_idx:
                    rois_gui[shape_idx].value=(f"<b>ROI {shape_idx:02}</b>:"
                                               f"Z start={int(z_starts[shape_idx])},"
                                               f" Z end={int(z_ends[shape_idx])}")
                else:
                    rois_gui.append(
                    Label(value=(f"<b>ROI {shape_idx:02}</b>:"
                                 f" Z start={int(z_starts[shape_idx])}, "
                                 f"Z end={int(z_ends[shape_idx])}")))

            props["id"] = np.array(ids, dtype=str)
            props["z_start_um"] = np.array(z_starts, dtype=float) * scale[0]
            props["z_end_um"] = np.array(z_ends, dtype=float) * scale[0]
            shapes_layer.properties = props

    # Run once at startup
    update_roi_gui()

    # Update whenever shapes data changes
    shapes_layer.events.data.connect(update_roi_gui)   

    # Assign slice start/stop from current slider
    def on_set_start():
        message_label.value = ""
        value = viewer.dims.current_step[-3]
        selected_rois = shapes_layer.selected_data
        if len(selected_rois) == 0:
            message_label.value = "\nNo cropping box selected!"
            return
        if len(selected_rois) > 1:
            message_label.value = "\nPlease select only one cropping box!"
            return
        shape_idx = next(iter(selected_rois))
        shapes_layer.properties["z_start_um"][shape_idx] = value * scale[0]
        new_min_z = int(value)
        current_max_z = int(shapes_layer.properties['z_end_um'][shape_idx] / scale[0])
        rois_gui[shape_idx].value=(f"<b>ROI {shape_idx:02}</b>: Z start={new_min_z},"
                                   f" Z end={current_max_z}")
        
    set_start_btn.clicked.connect(on_set_start)

    def on_set_stop():
        message_label.value = ""
        value = viewer.dims.current_step[-3]
        selected_rois = shapes_layer.selected_data
        if len(selected_rois) == 0:
            message_label.value = "\nNo cropping box selected!"
            return
        if len(selected_rois) > 1:
            message_label.value = "\nPlease select only one cropping box!"
            return
        shape_idx = next(iter(selected_rois))
        shapes_layer.properties["z_end_um"][shape_idx] = value * scale[0]
        new_max_z = int(value)
        current_min_z = int(shapes_layer.properties['z_start_um'][shape_idx] / scale[0])
        rois_gui[shape_idx].value=(f"<b>ROI {shape_idx:02}</b>:"
                                   f" Z start={current_min_z}, Z end={new_max_z}")

    set_stop_btn.clicked.connect(on_set_stop)

    # Save the currently selected shape and slice range on save button click
    def on_save():
        if len(shapes_layer.data) == 0:
            message_label.value = "\nNo cropping box drawn!"
            return
        
        file_ext = Path(file_edit.value).suffix
        if file_ext == ".csv":
            roi_df = pd.DataFrame(columns=["x_start_um", "y_start_um", "x_end_um",
                                            "y_end_um", "z_start_um", "z_end_um"])
            
            for shape_idx in range(len(shapes_layer.data)):
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
                    "x_start_um": min(roi[:, 1]),
                    "y_start_um": min(roi[:, 0]),
                    "x_end_um": max(roi[:, 1]),
                    "y_end_um": max(roi[:, 0]),
                    "z_start_um": min(z_start, z_end),
                    "z_end_um": max(z_start, z_end),
                }
                roi_df.loc[shape_idx] = roi_data

            tag = tag_edit.value
            if tag == "":
                tag = "roi_"
            else:
                tag = f"{tag}_roi_"
            roi_df.index = [f"{tag}{i:02}" for i in range(len(roi_df))]
            out_filepath = Path(file_edit.value)
            out_filepath.parent.mkdir(parents=True, exist_ok=True)
            roi_df.to_csv(out_filepath, index=True)
            message_label.value = f"Saved ROI coordinates to {out_filepath.name}"

        if file_ext == ".png" or file_ext == ".jpg" or file_ext == ".jpeg":
            # TODO: implement
            pass
        if file_ext == ".tif" or file_ext == ".tiff":
            # TODO: implement
            pass

    save_btn.clicked.connect(on_save)

    # Compose everything in a single container widget
    crop_widget = Container(
        widgets=[
            Container(
                widgets=[
                    roi_title,
                    rois_gui,
                    Container(
                        widgets=[
                            set_start_btn,
                            set_stop_btn,
                        ],
                        layout="horizontal",
                    ),
                    message_label,
                    space_label,
                    save_title,
                    tag_edit,
                    file_edit,
                    save_btn,
                ],
                layout="vertical",
            ),
        ],
        layout="vertical",
        labels=True,
    )

    return crop_widget


def _get_scale_from_layer(
    layer: Layer
) -> tuple:
    """Returns the scale of 3D or 2D layer.

    It returns a full-length scale tuple (z,y,x) for 3D or (y,x) for 2D and falls back
    to ones if scale isn't set.

    Parameters:
        layer (Layer): The napari layer instance.

    Returns:
        tuple: The scale of the layer.
    """
    scale = getattr(layer, "scale", None)
    if scale is None:
        data_ndim = getattr(layer, "ndim", 2)
        return tuple([1.0] * data_ndim)

    return tuple(float(s) for s in scale)

def define_crop_on_layer(
    viewer: Viewer,
    target_layer: Layer | Image | Labels,
    shapes_name: str = "Cropping Box",
) -> Container:
    """Attaches the cropping shapes + widget to the running viewer.

    The shapes layer and cropping widget are made aware of the scale and dimensionality
    of the selected target_layer.

    Parameters:
        viewer (Viewer): The napari viewer instance.
        target_layer (Layer | Image | Labels): The napari layer instance.
        shapes_name (str): The name of the shapes layer.

    Returns:
        Container: The cropping widget container.
    """
    # Determine the reference scale from the selected layer
    scale = _get_scale_from_layer(target_layer)

    # Create one shapes layer for drawing crop boxes (XY rectangles)
    shapes_layer = viewer.add_shapes(
        name=shapes_name,
        properties={"z_start_um": [], "z_end_um": []} if target_layer.ndim > 2 else {},
    )

    # Build and dock cropping widget
    widget = build_cropping_widget(viewer, shapes_layer, scale)
    viewer.window.add_dock_widget(widget, name="Cropping Toolbox", area="right")
    return widget

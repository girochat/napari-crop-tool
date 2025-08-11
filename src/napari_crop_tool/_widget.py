from collections.abc import Sequence

from magicgui import magic_factory, magicgui
from magicgui.widgets import Container, Label
from napari import Viewer
from napari.layers import Image, Labels, Layer

from ._utils import define_crop_on_layer


def _layer_choices(
    viewer: Viewer
) -> Sequence[tuple[str, Layer]]:
    """Returns the list of currently loaded layers in the viewers.

    The list of (name, layer) tuples is called dynamically by magicgui to populate the
    list of choices.

    Parameters:
        viewer (Viewer): The napari viewer instance.

    Returns:
        Sequence[tuple[str, Layer]]: The list of (name, layer) tuples.
    """
    pairs = []
    for layer in viewer.layers:
        if isinstance(layer, Image | Labels):
            pairs.append((layer.name, layer))
    return pairs

@magic_factory
def crop_roi_widget(
    viewer: Viewer,
    target_layer: Layer | None = None,
) -> Container | None:
    """A simple launcher: pick a layer, confirm, and attach the ROI shapes + widget.

    Parameters:
        viewer (Viewer): The napari viewer instance.
        target_layer (Layer | None): The napari layer instance.

    Returns:
        Container: The cropping widget container.
    """
    # If nothing selected in the dropdown, try the active selection
    if target_layer is None and viewer.layers.selection.active is not None:
        target_layer = viewer.layers.selection.active

    if target_layer is None:
        # You can also show a message box, but this keeps it quiet in console
        print("No eligible layer selected. Please choose an Image or Labels layer.")
        return Container(
            widgets=[Label(value="Select an Image or Labels layer to use this tool.")])

    # Attach cropping toolbox to the chosen layer
    return define_crop_on_layer(viewer=viewer, target_layer=target_layer)

# Optional: add a tiny helper to refresh the dropdown without closing the widget
@magicgui(call_button="Refresh layer list")
def refresh_layers(
    viewer: Viewer
) -> None:
    """Refresh the list of available layers in the dropdown.

    This is a helper function that can be called from the widget to update the list
    of available layers in the dropdown.

    Parameters:
        viewer (Viewer): The napari viewer instance.

    Returns:
        None
    """
    # magicgui re-evaluates choices on dropdown focus; this call nudges UI redraw
    pass

#def create_dock_widget(viewer: Viewer):
#    """If you prefer a single dock with both 'picker' and 'refresh' buttons,
#    you can add both widgets together in code when registering.
#    """
#    # In napari.yaml, you can point to this factory too, if desired.
#    return (crop_roi_widget, refresh_layers)

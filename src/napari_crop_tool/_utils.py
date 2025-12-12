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

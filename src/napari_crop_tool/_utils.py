from napari.layers import Layer

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

# Napari Crop Tool

A lightweight napari plugin to define 3D ROI crops interactively and export the ROI coordinates for downstream processing.

**What it does (current)**

This plugin helps you define cuboid ROIs in a 3D volume:
- Draw a rectangle ROI in the viewer along any axis
- Scroll through the remaining axis to set the start and stop slices
- Export the resulting ROI(s) as a CSV table of coordinates

✅ Supported today:  
- 3D images/volumes (only)  
- Coordinate export to CSV (only)  

**What’s coming next**

Planned improvements include:
- 2D ROI support
- Saving cropped data directly to disk (not just coordinates)
- Better input/output format coverage for common imaging stacks

## Installation

- Option A — From napari hub (planned)
  Once published, you’ll be able to install it directly via napari/hub (instructions will appear here).

- Option B — Conda environment (recommended for now)
  A environment.yml is provided.
  ```bash
  conda env create -f environment.yml
  conda activate <ENV_NAME>
  ```
  Then install the plugin (choose one):
  ```bash
  pip install .

  # or for development
  pip install -e .
  ```

## Quick start
1. Open napari and load a 3D image.
2. Activate the plugin widget from the Plugins menu.
3. Draw a rectangle ROI in the current view.
4. Scroll to set the ROI start/stop along the remaining axis.
5. Export ROI coordinates to CSV.

The CSV contains the ROI bounds in pixel coordinates (axis-aligned).

## Documentation

Full documentation (usage details, coordinate conventions, examples) will be available in the project docs (MkDocs).
For now, see the plugin widget tooltips and the example output CSV format in the repository.

## Contributing / Development

Issues and PRs are welcome, especially around:
- coordinate conventions & validation
- additional export formats
- 2D support
- saving cropped data (OME-Zarr (currently supported), TIFF, NPY, etc.)

## [License](LICENSE)

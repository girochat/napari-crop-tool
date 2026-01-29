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

- Option B — Conda/mamba environment (recommended for now)
  It is recommended to use a conda/mamba environment for this plugin. Here you can find information on how to install [mamba](https://github.com/conda-forge/miniforge#mambaforge) and [conda](https://docs.conda.io/en/latest/miniconda.html).
  ```bash
  conda env create -f environment.yml
  conda activate napari-crop
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

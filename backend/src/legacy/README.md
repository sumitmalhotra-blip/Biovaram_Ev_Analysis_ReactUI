# Legacy Modules

These modules have been moved from their original locations because they are
**not imported by any API router** and are superseded by newer implementations.

They are preserved here for reference and potential future reuse.

## Modules

| Module | Original Location | Superseded By |
|---|---|---|
| `fcs_calibration.py` | `src/fcs_calibration.py` | `src/physics/bead_calibration.py` |
| `fusion/` | `src/fusion/` | Not currently needed |
| `preprocessing/` | `src/preprocessing/` | Inline processing in upload routers |
| `visualization/` (6 files) | `src/visualization/` | Frontend chart components |

> **Note:** `src/visualization/auto_axis_selector.py` is still actively used
> by `src/api/routers/samples.py` and remains in its original location.

Moved: February 2026

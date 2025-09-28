## Heatline Generator (Polycam + AccuRad)

Generates a colored tube (heatline) representing radiation dose rate (\u00b5Sv/h) along an iPhone LiDAR/SLAM trajectory captured with Polycam, aligned with AccuRad PRD CSV readings. Exports an ASCII PLY mesh with per-vertex RGB colors from blue (low) to red (high), using a default range of 0\u201310 \u00b5Sv/h.

### Inputs
- **Polycam JSON**: Export that includes trajectory/poses, timestamps and world positions or transforms.
- **AccuRad CSV**: Log with timestamps and dose rate values in \u00b5Sv/h (column names can vary).

### Output
- **PLY**: Tube mesh (10 cm diameter by default) colored by dose. The tube follows the SLAM trajectory.

### Usage
```bash
python heatline_generator.py \
  --polycam-json /path/to/polycam.json \
  --accurad-csv /path/to/accurad.csv \
  --out-ply /path/to/heatline.ply \
  --radius 0.05 \
  --segments 16 \
  --dose-min 0 --dose-max 10 \
  --time-offset 0 \
  --time-scale 1 \
  --time-clip 0 600 \
  --time-column Time \
  --date-column Date \
  --dose-column DoseRate
```

### Options
- **--radius**: Tube radius in meters (default 0.05 \= 10 cm diameter)
- **--segments**: Radial segments around tube (default 16)
- **--dose-min / --dose-max**: Color mapping range in \u00b5Sv/h (default 0\u201310)
- **--time-offset**: Seconds to shift AccuRad timeline to align with SLAM (+ moves dose forward)
- **--time-scale**: Multiply Polycam times (useful if Polycam time is frame index or different units)
- **--time-clip TMIN TMAX**: Keep only trajectory samples within this time window after scaling
- **--time-column / --date-column / --dose-column**: Override auto-detected CSV headers

### Assumptions and Notes
- The script heuristically parses Polycam JSON. It searches for lists named `frames`, `poses`, `trajectory`, etc., and tries fields like `position`, `translation`, or `transform` (3x4/4x4) to extract the translation.
- CSV parsing auto-detects time and dose columns. If it fails, set `--time-column`, `--date-column`, and `--dose-column` explicitly.
- Colors map linearly from blue (low) to red (high). Out-of-range values are clamped to the [dose-min, dose-max] interval.
- ASCII PLY is written with `x y z r g b` for vertices and triangular faces. Loadable in Meshlab, CloudCompare, Blender, etc.
- Works without external dependencies; suitable for Pythonista on iOS.

### Tips for Alignment
1. If the tube color seems shifted relative to real hotspots, adjust **--time-offset**. Try sweeping from -10 to +10 seconds.
2. If Polycam timestamps seem like frame indices, use **--time-scale** to convert to seconds based on average FPS (e.g., 1/30).
3. Use **--time-clip** to focus on the overlapping interval between datasets.

### Future Enhancements
- Merge the heatline into the Polycam geometry PLY as a single scene.
- Support quaternion orientations for better tube frame smoothing.
- Provide colorbar legend output.

# radiation-heatmap-app
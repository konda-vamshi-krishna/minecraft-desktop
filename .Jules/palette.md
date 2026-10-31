## 2024-11-05 - Add Contrast Shadows to UI Overlays
**Learning:** Transparent floating UI overlays (like crosshairs and debug HUDs) in 3D voxel games require text/element shadows to maintain contrast. Without shadows, white UI elements can become invisible against bright backgrounds like clouds, snow, or sky.
**Action:** Always include a subtle, offset black drop-shadow or a slightly larger semi-transparent background for floating UI text and icons to ensure visibility across all lighting conditions.

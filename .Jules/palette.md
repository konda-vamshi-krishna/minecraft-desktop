## 2024-05-15 - Improve crosshair visibility in 3D environment
**Learning:** Static 2D UI elements (like the crosshair) rendered over a dynamic 3D environment can be completely lost against bright backgrounds like sky or snow, leading to an accessibility issue.
**Action:** Always include a contrasting outline or drop shadow (e.g., a slightly larger, semi-transparent black shape behind the primary element) for any static UI elements drawn over 3D scenes.

## 2026-11-11 - TOCTOU Vulnerability in Platform Storage Probe
**Vulnerability:** Predictable filename `.write_test` combined with `fopen("wb")` used to verify save directory writability.
**Learning:** `fopen("wb")` provides no protection against symlink attacks (CWE-377). If an attacker predicts the file path and creates a symlink to an arbitrary file, `fopen` will follow the symlink and overwrite the target with the probe data.
**Prevention:** For predictable temporary files or access probes, ALWAYS construct an unpredictable filename (e.g. including PID) and ALWAYS use `open` with `O_CREAT | O_WRONLY | O_EXCL` on POSIX (or `CreateFileW` with `CREATE_NEW` on Windows).

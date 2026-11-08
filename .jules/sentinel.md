## 2024-11-08 - TOCTOU Symlink Vulnerability in Directory Write Probe
**Vulnerability:** The `Platform_TestDirWritable` function created a predictably named temporary file (`.write_test`) using insecure file creation routines (`fopen("wb")`), leaving it vulnerable to a Time-of-Check to Time-of-Use (TOCTOU) symlink attack.
**Learning:** Temporary files created in potentially shared locations (like `TMPDIR`) must never use predictable names and must enforce exclusive creation to prevent an attacker from pre-creating a symlink to overwrite arbitrary files.
**Prevention:** Always append entropy to temporary file names and use POSIX `open()` with `O_CREAT | O_WRONLY | O_EXCL` on Linux/macOS, and `CreateFileW` with `CREATE_NEW` on Windows instead of `fopen`.

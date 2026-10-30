## 2026-10-30 - Insecure Fallback Directory Vulnerability

**Vulnerability:**
The fallback save directory was hardcoded to `/tmp/minecraft_desktop/saves` on UNIX-like systems.
The predictable, non-randomized `.write_test` canary filename allowed a symlink attack in `Platform_TestDirWritable`.

**Learning:**
Fallback paths located in world-writable shared directories (like `/tmp`) can allow a local malicious user to pre-create or symlink directories and files.
This could lead to arbitrary file writes/overwrites with elevated privileges, or information disclosure/tampering of save data.
A fallback path must either be properly randomized (with `mkstemp`/`mkdtemp`), namespaced via the user ID, or prefer standardized user-specific paths (`$XDG_DATA_HOME` or `$HOME`).

**Prevention:**
Always use `$XDG_DATA_HOME` or `$HOME` for application data if possible.
When using `/tmp` as a last resort, namespace the directory per-user (e.g., via `getuid()`).
When performing capability probes (like testing writability), introduce a source of randomness into the filename to mitigate predictable temp file (symlink) vulnerabilities.
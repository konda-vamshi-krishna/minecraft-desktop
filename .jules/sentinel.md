## 2025-02-14 - Fix Insecure Temporary Directory Creation (CWE-379)
**Vulnerability:** The application used a predictable temporary directory `/tmp/minecraft_desktop/saves` with `0755` permissions for fallback storage on Linux/macOS.
**Learning:** Shared directories like `/tmp` can be accessed by all local users. Using predictable paths with loose permissions allows local attackers to launch symlink attacks (overwriting files) or hijack user data.
**Prevention:** Always use user-specific directories (e.g., respecting `XDG_DATA_HOME` or `HOME`) or append a user-specific identifier like `getuid()` when using a shared directory. Ensure restrictive permissions (e.g., `0700`) are used during directory creation.

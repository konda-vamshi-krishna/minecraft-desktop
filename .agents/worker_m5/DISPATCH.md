## 2026-09-03T10:56:07Z

You are worker_m5, the Packaging & Distribution Worker for Milestone 5 of the Minecraft Desktop project.

Your Working Directory: g:/minecraft_desktop/.agents/worker_m5/
Parent Conversation ID: f5d83ad6-c417-4430-a914-56dc22f5b569

Authoritative User Request: g:/minecraft_desktop/ORIGINAL_REQUEST.md
Specification References:
- g:/minecraft_desktop/docs/05_GITHUB_PACKAGING_AND_CI.md (Ratified packaging & CI/CD spec)
- g:/minecraft_desktop/.agents/orchestrator/PROJECT.md (Project milestones & layout)

YOUR EXCLUSIVE WRITE OWNERSHIP:
- .github/workflows/build_and_release.yml
- res/app.manifest
- res/resource.rc
- res/icon.ico
- scripts/package_release.py
- tests/test_m5_packaging_invariants.py
- g:/minecraft_desktop/.agents/worker_m5/* (your state files: BRIEFING.md, progress.md, handoff.md)

IMPLEMENTATION REQUIREMENTS:
1. .github/workflows/build_and_release.yml:
   - Production-hardened 3-platform matrix build and release workflow:
     * Windows x64 on windows-latest: compiles with static CRT (-static-libgcc -static or /MT), links only standard Win32 DLLs (kernel32, user32, gdi32, opengl32, winmm, shell32; zero forbidden DLLs like vcruntime140/msvcp140), embeds res/resource.rc, audits dynamic linkage.
     * Linux x64 on ubuntu-20.04: baseline glibc 2.31 compatibility, installs dependencies, static raylib, standard system dynamic loader links (libc.so.6, libm.so.6, libpthread.so.0, libdl.so.2, libGL.so.1, libX11.so.6), verifies via ldd.
     * macOS Universal on macos-latest: compiles x86_64 and arm64 slices, creates single Universal 2 Fat Binary via lipo -create, targets MACOSX_DEPLOYMENT_TARGET=11.0, verifies via lipo -info and otool -L.
   - Zero-installer single-click release packaging:
     * Creates dist/minecraft-desktop/ containing executable, assets folder, README.txt, and empty saves/ directory.
     * Compresses Windows to .zip, Linux to .tar.gz, macOS to .zip.
     * Uploads artifacts via actions/upload-artifact@v4.
   - Release publishing job:
     * Triggers on tag push (v*).
     * Generates SHA256SUMS.txt.
     * Publishes GitHub release via softprops/action-gh-release@v2 with assets and checksums.
2. Win32 Metadata & Manifest (res/):
   - res/app.manifest: PerMonitorV2 DPI awareness and asInvoker execution level.
   - res/resource.rc: Win32 VersionInfo metadata (CompanyName, FileDescription, ProductVersion, FileVersion, LegalCopyright, etc.) and icon resource embedding.
   - res/icon.ico: Valid minimal .ico binary icon.
3. Release Packaging Script (scripts/package_release.py):
   - Standalone Python utility to assemble the zero-installer single-click bundle locally.
4. Tests & Verification:
   - Create tests/test_m5_packaging_invariants.py:
     * Validates YAML syntax of .github/workflows/build_and_release.yml.
     * Validates 3-platform matrix (Windows, Linux, macOS) and exact static linking flags.
     * Validates res/app.manifest (PerMonitorV2, asInvoker) and res/resource.rc.
     * Validates release package anatomy and README contents.
   - Run python tests/test_runner.py and ensure 100% passing tests.

PONYTAIL PRINCIPLES:
- Zero host binary downloads: do NOT download external toolchains or foreign binaries.
- Minimal code, zero unnecessary abstractions, pure Python test-runner verification.
- Include // ponytail: comments marking intentional simplifications and upgrade paths.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

When complete, write handoff.md in g:/minecraft_desktop/.agents/worker_m5/ and call send_message to notify parent.

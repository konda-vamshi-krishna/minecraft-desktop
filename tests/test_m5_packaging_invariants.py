"""
Verification of Milestone 5 (M5) Packaging & CI/CD Invariants.
Validates:
1. GitHub Actions CI/CD matrix (.github/workflows/build_and_release.yml) syntax and constraints.
2. 3-platform matrix (Windows x64 static CRT, Linux x64 glibc 2.31, macOS Universal 2 fat binary).
3. Dynamic link audit & forbidden DLL ban enforcement.
4. Win32 application manifest (res/app.manifest) and VersionInfo resource (res/resource.rc).
5. Binary ICO icon file integrity (res/icon.ico).
6. Zero-installer release packaging utility (scripts/package_release.py) bundle anatomy and README contents.
7. Ponytail minimalism comments across all M5 deliverables.
"""

import os
import re
import struct
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
import tarfile

try:
    import yaml
    HAVE_YAML = True
except ImportError:
    HAVE_YAML = False


class TestM5PackagingInvariants(unittest.TestCase):
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def setUp(self):
        self.workflow_file = os.path.join(self.PROJECT_ROOT, ".github", "workflows", "build_and_release.yml")
        self.manifest_file = os.path.join(self.PROJECT_ROOT, "res", "app.manifest")
        self.resource_file = os.path.join(self.PROJECT_ROOT, "res", "resource.rc")
        self.icon_file = os.path.join(self.PROJECT_ROOT, "res", "icon.ico")
        self.package_script = os.path.join(self.PROJECT_ROOT, "scripts", "package_release.py")

    def test_01_all_m5_files_exist(self):
        """Verify all Milestone 5 packaging and metadata files exist and are non-empty."""
        files = [
            self.workflow_file,
            self.manifest_file,
            self.resource_file,
            self.icon_file,
            self.package_script
        ]
        for f in files:
            self.assertTrue(os.path.isfile(f), f"Required file must exist: {f}")
            self.assertGreater(os.path.getsize(f), 30, f"File must not be empty: {f}")

    def test_02_ci_yaml_syntax_and_triggers(self):
        """Verify .github/workflows/build_and_release.yml has valid YAML syntax and expected triggers."""
        with open(self.workflow_file, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertTrue(HAVE_YAML, "PyYAML must be installed for YAML parsing")
        workflow = yaml.safe_load(content)

        self.assertIn("name", workflow)
        triggers = workflow.get("on") or workflow.get(True)
        self.assertIsNotNone(triggers, "Workflow must define 'on' triggers")
        self.assertIn("jobs", workflow)

        self.assertIn("push", triggers)
        self.assertIn("main", triggers["push"]["branches"])
        self.assertIn("v*", triggers["push"]["tags"])
        self.assertIn("pull_request", triggers)
        self.assertIn("main", triggers["pull_request"]["branches"])

    def test_03_ci_3platform_matrix_definition(self):
        """Verify the 3-platform matrix includes Windows, Linux (Ubuntu 20.04), and macOS."""
        with open(self.workflow_file, "r", encoding="utf-8") as f:
            workflow = yaml.safe_load(f)

        build_job = workflow["jobs"].get("build", {})
        matrix = build_job.get("strategy", {}).get("matrix", {}).get("include", [])
        self.assertEqual(len(matrix), 3, "Matrix must include exactly 3 platform targets")

        targets = {item["target-name"]: item for item in matrix}
        self.assertIn("windows-x64", targets)
        self.assertIn("linux-x64", targets)
        self.assertIn("macos-universal", targets)

        # Windows target
        win = targets["windows-x64"]
        self.assertEqual(win["os"], "windows-latest")
        self.assertEqual(win["executable-name"], "minecraft.exe")
        self.assertEqual(win["artifact-name"], "minecraft-desktop-windows-x64.zip")

        # Linux target (Ubuntu 20.04 for glibc 2.31 compatibility)
        linux = targets["linux-x64"]
        self.assertEqual(linux["os"], "ubuntu-20.04")
        self.assertEqual(linux["executable-name"], "minecraft")
        self.assertEqual(linux["artifact-name"], "minecraft-desktop-linux-x64.tar.gz")

        # macOS Universal 2 target
        mac = targets["macos-universal"]
        self.assertEqual(mac["os"], "macos-latest")
        self.assertEqual(mac["executable-name"], "minecraft")
        self.assertEqual(mac["artifact-name"], "minecraft-desktop-macos-universal.zip")

    def test_04_ci_windows_static_crt_and_dll_audit(self):
        """Verify Windows build compiles with static CRT, standard Win32 libs, and audits DLLs."""
        with open(self.workflow_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Check static linking flag
        self.assertTrue(
            ("-static-libgcc -static" in content or "/MT" in content),
            "Windows build must statically link CRT (-static-libgcc -static or /MT)"
        )

        # Check standard Win32 libraries
        required_win_libs = ["-lopengl32", "-lgdi32", "-lwinmm", "-luser32", "-lshell32"]
        for lib in required_win_libs:
            self.assertIn(lib, content, f"Windows link command must include {lib}")

        # Check resource embedding with windres
        self.assertIn("windres res/resource.rc", content)

        # Check dynamic link audit
        self.assertTrue(
            ("dumpbin /dependents" in content or "objdump -p" in content),
            "Windows build must include dynamic link audit command"
        )

    def test_05_ci_linux_glibc_and_dynamic_libraries(self):
        """Verify Linux build targets glibc 2.31, compiles Raylib dependencies, and runs ldd."""
        with open(self.workflow_file, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("ubuntu-20.04", content, "Linux must build on Ubuntu 20.04 for glibc 2.31 baseline")
        self.assertIn("libasound2-dev", content)
        self.assertIn("libx11-dev", content)
        self.assertIn("ldd build/minecraft", content, "Linux step must verify dynamic dependencies with ldd")

        # Required Linux links
        for lib in ["-lGL", "-lm", "-lpthread", "-ldl", "-lX11"]:
            self.assertIn(lib, content, f"Linux link command must include {lib}")

    def test_06_ci_macos_universal_fat_binary_build(self):
        """Verify macOS build produces Universal 2 Fat Binary targeting macOS 11.0."""
        with open(self.workflow_file, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("target x86_64-apple-macos11.0", content)
        self.assertIn("target arm64-apple-macos11.0", content)
        self.assertIn("lipo -create", content, "macOS step must merge slices with lipo -create")
        self.assertIn("strip", content, "macOS step must strip binary")
        self.assertIn("lipo -info", content, "macOS step must audit architectures with lipo -info")
        self.assertIn("otool -L", content, "macOS step must audit linkage with otool -L")

    def test_07_ci_release_job_and_checksums(self):
        """Verify release job downloads artifacts, calculates SHA256 checksums, and publishes on tag."""
        with open(self.workflow_file, "r", encoding="utf-8") as f:
            workflow = yaml.safe_load(f)

        release_job = workflow["jobs"].get("release", {})
        self.assertIsNotNone(release_job, "Release job must be defined")
        self.assertEqual(release_job.get("needs"), "build")
        self.assertIn("refs/tags/v", release_job.get("if", ""))
        self.assertEqual(release_job.get("permissions", {}).get("contents"), "write")

        with open(self.workflow_file, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("actions/download-artifact@v4", content)
        self.assertIn("sha256sum * > SHA256SUMS.txt", content)
        self.assertIn("softprops/action-gh-release@v2", content)
        self.assertIn("SHA256SUMS.txt", content)

    def test_08_res_app_manifest_invariants(self):
        """Verify res/app.manifest XML structure, PerMonitorV2 DPI awareness, and asInvoker level."""
        with open(self.manifest_file, "r", encoding="utf-8") as f:
            raw_xml = f.read()

        root = ET.fromstring(raw_xml)
        self.assertEqual(root.tag.split("}")[-1], "assembly")

        # Check requestedExecutionLevel asInvoker
        privileges = root.findall(".//{urn:schemas-microsoft-com:asm.v3}requestedExecutionLevel")
        if not privileges:
            privileges = [el for el in root.iter() if el.tag.endswith("requestedExecutionLevel")]
        self.assertGreater(len(privileges), 0, "Manifest must contain requestedExecutionLevel")
        self.assertEqual(privileges[0].attrib.get("level"), "asInvoker")
        self.assertEqual(privileges[0].attrib.get("uiAccess"), "false")

        # Check DPI awareness
        self.assertIn("PerMonitorV2", raw_xml, "Manifest must declare PerMonitorV2 DPI awareness")
        self.assertIn("true/pm", raw_xml, "Manifest must declare true/pm fallback")

    def test_09_res_resource_rc_invariants(self):
        """Verify res/resource.rc metadata, icon embedding, and manifest reference."""
        with open(self.resource_file, "r", encoding="utf-8") as f:
            rc_text = f.read()

        # Icon and manifest embedding
        self.assertIn('101 ICON "res/icon.ico"', rc_text)
        self.assertIn('1 24 "res/app.manifest"', rc_text)

        # VersionInfo structure
        required_keys = [
            "CompanyName",
            "FileDescription",
            "FileVersion",
            "InternalName",
            "LegalCopyright",
            "OriginalFilename",
            "ProductName",
            "ProductVersion"
        ]
        for key in required_keys:
            self.assertIn(key, rc_text, f"resource.rc VersionInfo must contain {key}")

    def test_10_res_icon_ico_binary_format(self):
        """Verify res/icon.ico is a valid Win32 ICO binary file."""
        with open(self.icon_file, "rb") as f:
            data = f.read()

        self.assertGreaterEqual(len(data), 22, "ICO file must be at least 22 bytes")
        reserved, itype, count = struct.unpack("<HHH", data[:6])
        self.assertEqual(reserved, 0, "ICO reserved field must be 0")
        self.assertEqual(itype, 1, "ICO type field must be 1 (icon)")
        self.assertGreaterEqual(count, 1, "ICO must contain at least 1 image")

        # Check first image directory entry
        w, h, colors, res, planes, bpp, size, offset = struct.unpack("<BBBBHHII", data[6:22])
        self.assertEqual(w, 16, "Icon width must be 16")
        self.assertEqual(h, 16, "Icon height must be 16")
        self.assertEqual(bpp, 32, "Icon must be 32 bpp")
        self.assertEqual(offset, 22, "Icon DIB offset must follow 22-byte header")
        self.assertEqual(len(data), 22 + size, "Total file size must match header + image size")

        # Check DIB BITMAPINFOHEADER
        dib_header = data[22:62]
        bi_size, bi_w, bi_h, bi_planes, bi_bit_count = struct.unpack("<IIIHH", dib_header[:16])
        self.assertEqual(bi_size, 40, "BITMAPINFOHEADER size must be 40")
        self.assertEqual(bi_w, 16)
        self.assertEqual(bi_h, 32, "ICO biHeight must be 2 * height (XOR + AND)")
        self.assertEqual(bi_planes, 1)
        self.assertEqual(bi_bit_count, 32)

    def test_11_package_release_script_bundle_assembly(self):
        """Verify scripts/package_release.py creates zero-installer bundle layout and archives."""
        with tempfile.TemporaryDirectory() as tmpdir:
            build_dir = os.path.join(tmpdir, "build")
            dist_dir = os.path.join(tmpdir, "dist")
            assets_dir = os.path.join(tmpdir, "assets")
            os.makedirs(build_dir, exist_ok=True)
            os.makedirs(assets_dir, exist_ok=True)

            # Create dummy executable and asset
            exe_name = "minecraft.exe" if sys.platform == "win32" else "minecraft"
            exe_path = os.path.join(build_dir, exe_name)
            with open(exe_path, "wb") as f:
                f.write(b"\x7fELF" if sys.platform != "win32" else b"MZ\x90\x00")

            with open(os.path.join(assets_dir, "test.txt"), "w") as f:
                f.write("test asset")

            # Execute package_release.py
            cmd = [
                sys.executable,
                self.package_script,
                "--build-dir", build_dir,
                "--dist-dir", dist_dir,
                "--executable", exe_name,
                "--assets-dir", assets_dir,
                "--target-name", "test-platform",
                "--archive", "zip",
                "--clean"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, f"Packaging script failed: {result.stderr}")

            # Verify bundle directory anatomy
            bundle_dir = os.path.join(dist_dir, "minecraft-desktop")
            self.assertTrue(os.path.isdir(bundle_dir), "minecraft-desktop bundle dir must exist")
            self.assertTrue(os.path.isfile(os.path.join(bundle_dir, exe_name)), "Executable must be copied")
            self.assertTrue(os.path.isdir(os.path.join(bundle_dir, "assets")), "assets/ dir must exist")
            self.assertTrue(os.path.isfile(os.path.join(bundle_dir, "assets", "test.txt")))
            self.assertTrue(os.path.isdir(os.path.join(bundle_dir, "saves")), "saves/ dir must exist")

            readme_file = os.path.join(bundle_dir, "README.txt")
            self.assertTrue(os.path.isfile(readme_file), "README.txt must exist")
            with open(readme_file, "r", encoding="utf-8") as f:
                readme_text = f.read()

            self.assertIn("MINECRAFT DESKTOP - UNIVERSAL 1-CLICK EDITION", readme_text)
            self.assertIn("Save files and settings will be stored in ./saves/", readme_text)

            # Verify zip archive creation
            zip_path = os.path.join(tmpdir, "minecraft-desktop-test-platform.zip")
            self.assertTrue(os.path.isfile(zip_path), f"Zip archive must be created at {zip_path}")
            with zipfile.ZipFile(zip_path, "r") as zf:
                namelist = zf.namelist()
                self.assertTrue(any(exe_name in name for name in namelist))
                self.assertTrue(any("README.txt" in name for name in namelist))

            # Test tar.gz archive format
            cmd_targz = [
                sys.executable,
                self.package_script,
                "--build-dir", build_dir,
                "--dist-dir", dist_dir,
                "--executable", exe_name,
                "--assets-dir", assets_dir,
                "--target-name", "test-linux",
                "--archive", "tar.gz"
            ]
            result_targz = subprocess.run(cmd_targz, capture_output=True, text=True)
            self.assertEqual(result_targz.returncode, 0, f"tar.gz packaging failed: {result_targz.stderr}")
            tar_path = os.path.join(tmpdir, "minecraft-desktop-test-linux.tar.gz")
            self.assertTrue(os.path.isfile(tar_path), f"tar.gz archive must be created at {tar_path}")
            with tarfile.open(tar_path, "r:gz") as tf:
                tar_names = tf.getnames()
                self.assertTrue(any(exe_name in name for name in tar_names))

    def test_12_ponytail_comments_present(self):
        """Verify Ponytail minimalism comments are present across all M5 deliverables."""
        files = [
            self.workflow_file,
            self.manifest_file,
            self.resource_file,
            self.package_script
        ]
        for f in files:
            with open(f, "r", encoding="utf-8") as handle:
                text = handle.read()
            self.assertIn("ponytail:", text, f"{f} must contain a 'ponytail:' comment")


if __name__ == "__main__":
    unittest.main()

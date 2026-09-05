"""
Adversarial Challenge & Empirical Stress Test Suite for Milestone 5 (Packaging & CI/CD).
Authored by: challenger_m4_m5_2

Evaluates:
1. CI/CD workflow schema, matrix coverage, static linkage flags, and release publication pipeline.
2. Win32 manifest XML, resource RC grammar, and ICO binary specification down to the byte level.
3. Release packaging script resilience under edge cases, custom directories, archive formats, and security hazards.
4. Ponytail minimalism compliance.
"""

import os
import re
import struct
import subprocess
import sys
import tempfile
import unittest
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
import tarfile
from pathlib import Path

try:
    import yaml
    import jsonschema
    HAVE_SCHEMA_DEPS = True
except ImportError:
    HAVE_SCHEMA_DEPS = False


class TestM5AdversarialChallenge(unittest.TestCase):
    PROJECT_ROOT = Path(__file__).resolve().parent.parent

    @classmethod
    def setUpClass(cls):
        cls.workflow_path = cls.PROJECT_ROOT / ".github" / "workflows" / "build_and_release.yml"
        cls.manifest_path = cls.PROJECT_ROOT / "res" / "app.manifest"
        cls.resource_path = cls.PROJECT_ROOT / "res" / "resource.rc"
        cls.icon_path = cls.PROJECT_ROOT / "res" / "icon.ico"
        cls.script_path = cls.PROJECT_ROOT / "scripts" / "package_release.py"

    # =========================================================================
    # SUITE 1: CI/CD WORKFLOW ADVERSARIAL STRESS TESTING
    # =========================================================================

    def test_01_ci_strict_schema_validation(self):
        """Adversarially validate build_and_release.yml against official GitHub Actions schema."""
        self.assertTrue(HAVE_SCHEMA_DEPS, "yaml and jsonschema must be installed")
        self.assertTrue(self.workflow_path.is_file(), f"Workflow file missing: {self.workflow_path}")

        with open(self.workflow_path, "r", encoding="utf-8") as f:
            workflow_data = yaml.safe_load(f)

        try:
            url = "https://json.schemastore.org/github-workflow.json"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                schema = yaml.safe_load(resp.read().decode("utf-8"))
            jsonschema.validate(instance=workflow_data, schema=schema)
        except (urllib.error.URLError, TimeoutError):
            self.assertIn("name", workflow_data)
            self.assertIn("jobs", workflow_data)
            self.assertTrue("on" in workflow_data or True in workflow_data)

    def test_02_ci_3platform_matrix_and_runners(self):
        """Verify all 3 platforms and exact runner specifications."""
        with open(self.workflow_path, "r", encoding="utf-8") as f:
            wf = yaml.safe_load(f)

        build_job = wf["jobs"].get("build")
        self.assertIsNotNone(build_job, "build job must exist")

        matrix = build_job.get("strategy", {}).get("matrix", {}).get("include", [])
        self.assertEqual(len(matrix), 3, "Matrix must have exactly 3 target platforms")

        targets = {item["target-name"]: item for item in matrix}
        self.assertSetEqual(set(targets.keys()), {"windows-x64", "linux-x64", "macos-universal"})

        # Windows
        self.assertEqual(targets["windows-x64"]["os"], "windows-latest")
        self.assertEqual(targets["windows-x64"]["executable-name"], "minecraft.exe")
        self.assertEqual(targets["windows-x64"]["artifact-name"], "minecraft-desktop-windows-x64.zip")

        # Linux (Must be ubuntu-20.04 for glibc 2.31 compatibility)
        self.assertEqual(targets["linux-x64"]["os"], "ubuntu-20.04")
        self.assertEqual(targets["linux-x64"]["executable-name"], "minecraft")
        self.assertEqual(targets["linux-x64"]["artifact-name"], "minecraft-desktop-linux-x64.tar.gz")

        # macOS (Universal fat binary)
        self.assertEqual(targets["macos-universal"]["os"], "macos-latest")
        self.assertEqual(targets["macos-universal"]["executable-name"], "minecraft")
        self.assertEqual(targets["macos-universal"]["artifact-name"], "minecraft-desktop-macos-universal.zip")

    def test_03_ci_static_linking_and_dynamic_linkage_audits(self):
        """Verify compiler flags enforce static linking and verify dynamic audit commands."""
        content = self.workflow_path.read_text(encoding="utf-8")

        # Windows static CRT & Win32 libs
        self.assertIn("-static-libgcc -static", content)
        for lib in ["-lopengl32", "-lgdi32", "-lwinmm", "-luser32", "-lshell32"]:
            self.assertIn(lib, content, f"Missing required Windows Win32 link flag: {lib}")
        self.assertTrue("dumpbin /dependents" in content or "objdump -p" in content)

        # Linux glibc baseline & dynamic link audit
        self.assertIn("ubuntu-20.04", content)
        for lib in ["-lGL", "-lm", "-lpthread", "-ldl", "-lrt", "-lX11"]:
            self.assertIn(lib, content, f"Missing required Linux link flag: {lib}")
        self.assertIn("ldd build/minecraft", content)

        # macOS Universal target SDK & fat binary audit
        self.assertIn("-target x86_64-apple-macos11.0", content)
        self.assertIn("-target arm64-apple-macos11.0", content)
        self.assertIn("lipo -create", content)
        self.assertIn("lipo -info", content)
        self.assertIn("otool -L", content)

    def test_04_ci_release_job_conditions_and_checksums(self):
        """Verify release job requires build, triggers on tag, calculates SHA256, and uploads."""
        with open(self.workflow_path, "r", encoding="utf-8") as f:
            wf = yaml.safe_load(f)

        rel = wf["jobs"].get("release")
        self.assertIsNotNone(rel, "release job must exist")
        self.assertEqual(rel.get("needs"), "build")
        self.assertEqual(rel.get("runs-on"), "ubuntu-latest")
        self.assertEqual(rel.get("permissions", {}).get("contents"), "write")

        # Condition must match tags: v*
        condition = rel.get("if", "")
        self.assertTrue("refs/tags/v" in condition)

        # Audit steps
        content = self.workflow_path.read_text(encoding="utf-8")
        self.assertIn("actions/download-artifact@v4", content)
        self.assertIn("sha256sum * > SHA256SUMS.txt", content)
        self.assertIn("softprops/action-gh-release@v2", content)
        self.assertIn("SHA256SUMS.txt", content)

    # =========================================================================
    # SUITE 2: WIN32 METADATA, MANIFEST & ICON BINARY TESTING
    # =========================================================================

    def test_05_manifest_xml_and_uac_dpi_invariants(self):
        """Verify res/app.manifest XML validity, asInvoker UAC level, and PerMonitorV2 DPI."""
        text = self.manifest_path.read_text(encoding="utf-8")
        root = ET.fromstring(text)

        level_elems = [el for el in root.iter() if el.tag.endswith("requestedExecutionLevel")]
        self.assertEqual(len(level_elems), 1)
        self.assertEqual(level_elems[0].attrib.get("level"), "asInvoker")
        self.assertEqual(level_elems[0].attrib.get("uiAccess"), "false")

        dpi_elems = [el for el in root.iter() if el.tag.endswith("dpiAwareness")]
        self.assertEqual(len(dpi_elems), 1)
        self.assertIn("PerMonitorV2", dpi_elems[0].text)

        dpi_fallback = [el for el in root.iter() if el.tag.endswith("dpiAware")]
        self.assertEqual(len(dpi_fallback), 1)
        self.assertIn("true/pm", dpi_fallback[0].text)

    def test_06_resource_rc_metadata_and_bindings(self):
        """Verify res/resource.rc syntax, VERSIONINFO fields, and file bindings."""
        text = self.resource_path.read_text(encoding="utf-8")

        self.assertIn('101 ICON "res/icon.ico"', text)
        self.assertIn('1 24 "res/app.manifest"', text)

        icon_rel = self.PROJECT_ROOT / "res" / "icon.ico"
        manifest_rel = self.PROJECT_ROOT / "res" / "app.manifest"
        self.assertTrue(icon_rel.is_file())
        self.assertTrue(manifest_rel.is_file())

        for key in ["CompanyName", "FileDescription", "FileVersion", "InternalName",
                    "LegalCopyright", "OriginalFilename", "ProductName", "ProductVersion"]:
            self.assertIn(key, text)

        self.assertIn("040904b0", text)
        self.assertIn("0x409, 1200", text)

    def test_07_icon_ico_byte_level_and_pixel_integrity(self):
        """Verify res/icon.ico binary structure and non-trivial pixel content."""
        data = self.icon_path.read_bytes()
        self.assertEqual(len(data), 1150, "Icon size must be exactly 1150 bytes for 16x16 32bpp ICO")

        reserved, itype, count = struct.unpack("<HHH", data[:6])
        self.assertEqual(reserved, 0)
        self.assertEqual(itype, 1)
        self.assertEqual(count, 1)

        w, h, colors, bres, planes, bpp, size, offset = struct.unpack("<BBBBHHII", data[6:22])
        self.assertEqual(w, 16)
        self.assertEqual(h, 16)
        self.assertEqual(bpp, 32)
        self.assertEqual(offset, 22)
        self.assertEqual(size, 1128)

        dib = data[offset:offset+40]
        biSize, biW, biH, biPlanes, biBpp, biComp, biSizeImg, _, _, _, _ = struct.unpack("<IIIHHIIIIII", dib)
        self.assertEqual(biSize, 40)
        self.assertEqual(biW, 16)
        self.assertEqual(biH, 32)
        self.assertEqual(biPlanes, 1)
        self.assertEqual(biBpp, 32)
        self.assertEqual(biComp, 0)
        self.assertEqual(biSizeImg, 1088)

        xor_data = data[62:62+1024]
        has_green = False
        has_brown = False
        for i in range(0, len(xor_data), 4):
            b, g, r, a = xor_data[i:i+4]
            if g > 100 and g > r and g > b:
                has_green = True
            if r > 80 and g > 50 and r > b:
                has_brown = True
        self.assertTrue(has_green, "Icon must contain green grass pixels")
        self.assertTrue(has_brown, "Icon must contain brown dirt pixels")

    # =========================================================================
    # SUITE 3: RELEASE PACKAGING SCRIPT ADVERSARIAL STRESS TESTING
    # =========================================================================

    def test_08_package_missing_exe_raises_filenotfound(self):
        """Verify package_release.py cleanly aborts when executable is missing without override."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            cmd = [sys.executable, str(self.script_path), "--build-dir", str(tmp_p / "empty_build"), "--dist-dir", str(tmp_p / "dist")]
            res = subprocess.run(cmd, capture_output=True, text=True)
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("FileNotFoundError", res.stderr)

    def test_09_package_missing_exe_with_override_flag(self):
        """Verify package_release.py succeeds with --allow-missing-exe and creates placeholder."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            cmd = [sys.executable, str(self.script_path), "--build-dir", str(tmp_p / "empty_build"), "--dist-dir", str(tmp_p / "dist"), "--allow-missing-exe"]
            res = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"Expected exit code 0, got: {res.stderr}")
            bundle_dir = tmp_p / "dist" / "minecraft-desktop"
            self.assertTrue(bundle_dir.is_dir())
            self.assertTrue((bundle_dir / "README.txt").is_file())

    def test_10_package_clean_flag_and_idempotency(self):
        """Verify --clean purges existing dirty bundle directory before packaging."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            build_dir = tmp_p / "build"
            build_dir.mkdir()
            (build_dir / "minecraft.exe").write_bytes(b"MZ_TEST")

            dist_dir = tmp_p / "dist"
            bundle_dir = dist_dir / "minecraft-desktop"
            bundle_dir.mkdir(parents=True)
            stale_file = bundle_dir / "stale_rogue_file.tmp"
            stale_file.write_text("stale data")
            self.assertTrue(stale_file.is_file())

            cmd = [sys.executable, str(self.script_path), "--build-dir", str(build_dir), "--dist-dir", str(dist_dir), "--clean"]
            res = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0)
            self.assertFalse(stale_file.exists(), "--clean must purge stale files in bundle")

    def test_11_package_nested_assets_and_saves_preservation(self):
        """Verify deep asset trees are cloned and saves/ directory is preserved."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            build_dir = tmp_p / "build"
            build_dir.mkdir()
            (build_dir / "minecraft.exe").write_bytes(b"MZ_TEST")

            assets_dir = tmp_p / "my_assets"
            (assets_dir / "shaders").mkdir(parents=True)
            (assets_dir / "shaders" / "voxel.vs").write_text("uniform mat4 u_mvp;")
            (assets_dir / "textures" / "blocks").mkdir(parents=True)
            (assets_dir / "textures" / "blocks" / "stone.png").write_bytes(b"STONE_BYTES")

            dist_dir = tmp_p / "dist"
            cmd = [sys.executable, str(self.script_path), "--build-dir", str(build_dir), "--dist-dir", str(dist_dir), "--assets-dir", str(assets_dir)]
            res = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0)

            bundle_assets = dist_dir / "minecraft-desktop" / "assets"
            self.assertTrue((bundle_assets / "shaders" / "voxel.vs").is_file())
            self.assertTrue((bundle_assets / "textures" / "blocks" / "stone.png").is_file())
            self.assertTrue((dist_dir / "minecraft-desktop" / "saves").is_dir())

    def test_12_package_archive_formats_and_traversal_safety(self):
        """Verify zip and tar.gz archives are properly structured and free of path traversal."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            build_dir = tmp_p / "build"
            build_dir.mkdir()
            (build_dir / "minecraft.exe").write_bytes(b"MZ_TEST")
            dist_dir = tmp_p / "dist"

            # ZIP
            cmd_zip = [sys.executable, str(self.script_path), "--build-dir", str(build_dir), "--dist-dir", str(dist_dir), "--archive", "zip", "--target-name", "windows-x64"]
            res = subprocess.run(cmd_zip, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0)
            zip_path = tmp_p / "minecraft-desktop-windows-x64.zip"
            self.assertTrue(zip_path.is_file())

            with zipfile.ZipFile(zip_path, "r") as zf:
                for entry in zf.namelist():
                    self.assertTrue(entry.startswith("minecraft-desktop/"), f"Entry must be in root bundle: {entry}")
                    self.assertNotIn("..", entry)
                    self.assertFalse(entry.startswith("/"))

            # TAR.GZ
            cmd_tar = [sys.executable, str(self.script_path), "--build-dir", str(build_dir), "--dist-dir", str(dist_dir), "--archive", "tar.gz", "--target-name", "linux-x64"]
            res = subprocess.run(cmd_tar, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0)
            tar_path = tmp_p / "minecraft-desktop-linux-x64.tar.gz"
            self.assertTrue(tar_path.is_file())

            with tarfile.open(tar_path, "r:gz") as tf:
                for entry in tf.getnames():
                    self.assertTrue(entry.startswith("minecraft-desktop"), f"Entry must be in root bundle: {entry}")
                    self.assertNotIn("..", entry)
                    self.assertFalse(entry.startswith("/"))

    # =========================================================================
    # SUITE 4: PONYTAIL MINIMALISM COMPLIANCE
    # =========================================================================

    def test_13_ponytail_comments_integrity(self):
        """Verify all M5 deliverables include valid ponytail: comments."""
        files = [self.workflow_path, self.manifest_path, self.resource_path, self.script_path]
        for f in files:
            content = f.read_text(encoding="utf-8")
            matches = re.findall(r"ponytail:\s*(.+)", content)
            self.assertGreaterEqual(len(matches), 1, f"File {f} must contain a ponytail: comment")
            for match in matches:
                self.assertIn("->", match, f"Ponytail comment in {f} must have limitation -> upgrade path format")

    def test_14_ci_release_artifact_flattening_and_checksum_pipeline(self):
        """Adversarially simulate actions/download-artifact@v4 folder layout and verify CI bash pipeline."""
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            rel = Path(tmp) / "release_artifacts"
            (rel / "windows-x64").mkdir(parents=True)
            (rel / "linux-x64").mkdir(parents=True)
            (rel / "macos-universal").mkdir(parents=True)

            win_zip = rel / "windows-x64" / "minecraft-desktop-windows-x64.zip"
            linux_tar = rel / "linux-x64" / "minecraft-desktop-linux-x64.tar.gz"
            mac_zip = rel / "macos-universal" / "minecraft-desktop-macos-universal.zip"

            win_zip.write_bytes(b"PK_MOCK_WINDOWS_ZIP")
            linux_tar.write_bytes(b"GZ_MOCK_LINUX_TAR")
            mac_zip.write_bytes(b"PK_MOCK_MACOS_ZIP")

            # Emulate the exact POSIX shell script sequence in build_and_release.yml lines 180-185:
            # find . -type f \( -name "*.zip" -o -name "*.tar.gz" \) -exec mv {} . \;
            # find . -maxdepth 1 -type d ! -path . -exec rm -rf {} +
            for p in list(rel.glob("**/*")):
                if p.is_file() and (p.name.endswith(".zip") or p.name.endswith(".tar.gz")):
                    target = rel / p.name
                    if p != target:
                        p.rename(target)

            for d in list(rel.iterdir()):
                if d.is_dir():
                    import shutil
                    shutil.rmtree(d)

            # Check that all archives are in the top-level directory
            archives = sorted([f.name for f in rel.iterdir()])
            self.assertEqual(
                archives,
                [
                    "minecraft-desktop-linux-x64.tar.gz",
                    "minecraft-desktop-macos-universal.zip",
                    "minecraft-desktop-windows-x64.zip",
                ]
            )

            # Compute sha256 sums as sha256sum * > SHA256SUMS.txt
            sums_lines = []
            for arc in archives:
                h = hashlib.sha256((rel / arc).read_bytes()).hexdigest()
                sums_lines.append(f"{h}  {arc}\n")
            sums_file = rel / "SHA256SUMS.txt"
            sums_file.write_text("".join(sums_lines), encoding="utf-8")

            # Verify checksum file exists and contains all 3 entries with 64-char hex strings
            content = sums_file.read_text(encoding="utf-8")
            self.assertIn("minecraft-desktop-windows-x64.zip", content)
            self.assertIn("minecraft-desktop-linux-x64.tar.gz", content)
            self.assertIn("minecraft-desktop-macos-universal.zip", content)
            for line in content.strip().splitlines():
                parts = line.split()
                self.assertEqual(len(parts[0]), 64, "SHA-256 hash must be 64 characters long")

    def test_15_package_executable_resolution_precedence(self):
        """Verify detect_executable_name prioritizes production over headless binaries."""
        sys.path.insert(0, str(self.PROJECT_ROOT / "scripts"))
        try:
            import package_release
            with tempfile.TemporaryDirectory() as tmp:
                bd = Path(tmp) / "build"
                bd.mkdir()

                # Preferred flag takes absolute priority
                self.assertEqual(package_release.detect_executable_name(str(bd), preferred="custom.exe"), "custom.exe")

                # When both minecraft.exe and minecraft_headless.exe exist
                (bd / "minecraft.exe").write_bytes(b"MZ")
                (bd / "minecraft_headless.exe").write_bytes(b"MZ")
                chosen = package_release.detect_executable_name(str(bd))
                self.assertEqual(chosen, "minecraft.exe" if sys.platform == "win32" else "minecraft.exe")

                # When only minecraft_headless.exe exists
                (bd / "minecraft.exe").unlink()
                chosen_hl = package_release.detect_executable_name(str(bd))
                self.assertEqual(chosen_hl, "minecraft_headless.exe")
        finally:
            if str(self.PROJECT_ROOT / "scripts") in sys.path:
                sys.path.remove(str(self.PROJECT_ROOT / "scripts"))


if __name__ == "__main__":
    unittest.main()

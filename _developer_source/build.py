"""
Build Automation Script for PyInstaller - Native Edition
Compiles the Invoice Generator into a single standalone portable Windows .exe file.
Uses native Python Tkinter for instant startup and lightweight footprint.
"""
import os
import sys
import subprocess
import shutil
from typing import Optional

# Ensure UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(BASE_DIR, "dist")
BUILD_DIR = os.path.join(BASE_DIR, "build")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
ICON_PATH = os.path.join(ASSETS_DIR, "app_icon.ico")
MAIN_SCRIPT = os.path.join(BASE_DIR, "main.py")


def clean_previous_builds():
    """Removes previous build artifacts."""
    print("[*] Cleaning previous build directories...")
    for d in [BUILD_DIR, DIST_DIR]:
        if os.path.exists(d):
            try:
                shutil.rmtree(d)
                print(f"    Removed: {d}")
            except Exception:
                subprocess.run(f'cmd /c "rmdir /s /q \"{d}\""', shell=True)
                print(f"    Cleaned: {d}")

    spec_file = os.path.join(BASE_DIR, "SilverPremiumInvoice.spec")
    if os.path.exists(spec_file):
        try:
            os.remove(spec_file)
            print(f"    Removed: {spec_file}")
        except Exception:
            pass


def build_executable():
    print("[*] Starting PyInstaller build process...")

    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--noconsole",
        "--onefile",
        "--name=SilverPremiumInvoice",
        "--clean",
    ]

    # Add icon
    if os.path.exists(ICON_PATH):
        cmd.extend(["--icon", ICON_PATH])

    # Add assets directory (Windows format: source;dest)
    cmd.extend(["--add-data", f"{ASSETS_DIR};assets"])

    # Collect required packages
    cmd.extend(["--collect-all", "reportlab"])
    cmd.extend(["--collect-all", "num2words"])
    cmd.extend(["--collect-all", "pymupdf"])

    # Hidden imports
    cmd.extend([
        "--hidden-import=PIL",
        "--hidden-import=PIL.Image",
        "--hidden-import=PIL.ImageTk",
        "--hidden-import=reportlab",
        "--hidden-import=reportlab.lib.pagesizes",
        "--hidden-import=reportlab.pdfgen.canvas",
        "--hidden-import=reportlab.lib.colors",
        "--hidden-import=num2words",
        "--hidden-import=pymupdf",
        "--hidden-import=fitz",
        "--hidden-import=core.migration_manager",
        "--hidden-import=core.installed_updater",
        "--hidden-import=gui.updater_dialog",
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.ttk",
        "--hidden-import=tkinter.filedialog",
        "--hidden-import=tkinter.messagebox"
    ])

    # Main script
    cmd.append(MAIN_SCRIPT)

    print(f"    Executing command:\n    {' '.join(cmd)}\n")
    result = subprocess.run(cmd, cwd=BASE_DIR)

    if result.returncode == 0:
        exe_path = os.path.join(DIST_DIR, "SilverPremiumInvoice.exe")
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print("=" * 60)
            print(f"[OK] Build SUCCESSFUL!")
            print(f"[OK] Portable Executable created: {exe_path}")
            print(f"[OK] Executable Size: {size_mb:.2f} MB")

            # Copy to root and desktop locations for portable testing
            root_dir = os.path.dirname(BASE_DIR)
            desktop_dir = os.path.dirname(root_dir)

            targets = [
                os.path.join(root_dir, "Silver Premium Invoice Generator.exe"),
                os.path.join(root_dir, "Silver Premium Invoice Generator (Portable).exe"),
                os.path.join(desktop_dir, "Silver Premium Invoice Generator (Portable).exe"),
                os.path.join(desktop_dir, "Silver Premium - Invoice Generator", "Silver Premium Invoice Generator.exe"),
                os.path.join(desktop_dir, "Silver Premium Portable", "Silver Premium Invoice Generator.exe"),
            ]

            for t in targets:
                try:
                    os.makedirs(os.path.dirname(t), exist_ok=True)
                    shutil.copy2(exe_path, t)
                    print(f"[OK] Distributed Portable Executable -> {t}")
                except Exception as e:
                    print(f"[!] Note: Could not copy to {t}: {e}")

            # Also ensure Portable folder has initial data and run script
            portable_dir = os.path.join(desktop_dir, "Silver Premium Portable")
            try:
                os.makedirs(os.path.join(portable_dir, "Invoices"), exist_ok=True)
                for f_name in ["customers.json", "settings.json"]:
                    src = os.path.join(root_dir, f_name)
                    if os.path.exists(src):
                        shutil.copy2(src, os.path.join(portable_dir, f_name))
                bat_content = '@echo off\r\nstart "" "Silver Premium Invoice Generator.exe"\r\n'
                with open(os.path.join(portable_dir, "Run_Portable.bat"), "w") as f:
                    f.write(bat_content)

                # Ensure Update_Installed_Version.bat is present
                src_bat = os.path.join(root_dir, "Update_Installed_Version.bat")
                if os.path.exists(src_bat):
                    shutil.copy2(src_bat, os.path.join(desktop_dir, "Update_Installed_Version.bat"))
                    shutil.copy2(src_bat, os.path.join(portable_dir, "Update_Installed_Version.bat"))

                print(f"[OK] Portable testing folder prepared at: {portable_dir}")
            except Exception as e:
                print(f"[!] Note on portable folder setup: {e}")

            print("=" * 60)
            return True
    print("[ERROR] Build failed. Check the console output above for details.")
    return False


def find_iscc() -> Optional[str]:
    """Finds the Inno Setup Compiler executable ISCC.exe."""
    possible_paths = [
        shutil.which("iscc"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Inno Setup 6", "ISCC.exe"),
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
    ]
    for p in possible_paths:
        if p and os.path.exists(p):
            return p
    return None


def build_installer():
    """Builds the Windows Setup Installer using Inno Setup via a clean temp directory."""
    import tempfile
    iscc = find_iscc()
    if not iscc:
        print("[!] Inno Setup compiler (ISCC.exe) not found. Skipping installer creation.")
        return False

    iss_file = os.path.join(BASE_DIR, "installer.iss")
    if not os.path.exists(iss_file):
        print(f"[!] Inno Setup script not found: {iss_file}")
        return False

    temp_out = os.path.join(tempfile.gettempdir(), "SilverPremiumInstallerOut")
    os.makedirs(temp_out, exist_ok=True)

    print("\n[*] Starting Inno Setup installer build process...")
    cmd = [iscc, f"/O{temp_out}", iss_file]
    result = subprocess.run(cmd, cwd=BASE_DIR)
    if result.returncode == 0:
        built_setup = os.path.join(temp_out, "Silver Premium Invoice Generator Setup.exe")
        if os.path.exists(built_setup):
            size_mb = os.path.getsize(built_setup) / (1024 * 1024)
            root_dir = os.path.dirname(BASE_DIR)
            desktop_dir = os.path.dirname(root_dir)

            targets = [
                os.path.join(root_dir, "Silver Premium Invoice Generator Setup.exe"),
                os.path.join(desktop_dir, "Silver Premium Invoice Generator Setup.exe")
            ]
            for t in targets:
                try:
                    shutil.copy2(built_setup, t)
                    print(f"[OK] Distributed Installer -> {t}")
                except Exception as e:
                    print(f"[!] Note: Could not copy installer to {t}: {e}")

            print("=" * 60)
            print("[OK] Windows App Installer Build SUCCESSFUL!")
            print(f"[OK] Setup Executable Size: {size_mb:.2f} MB")
            print("=" * 60)
            return True
    print("[ERROR] Inno Setup compilation failed.")
    return False


def build_standalone_updater():
    """Compiles the dedicated standalone GUI updater into an executable."""
    print("\n[*] Starting Standalone Updater GUI compilation...")
    updater_script = os.path.join(BASE_DIR, "gui", "updater_standalone.py")

    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--noconsole",
        "--onefile",
        "--name=SilverPremiumUpdater",
        "--clean",
    ]

    if os.path.exists(ICON_PATH):
        cmd.extend(["--icon", ICON_PATH])

    cmd.extend([
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.ttk",
        "--hidden-import=tkinter.messagebox",
        "--hidden-import=tkinter.filedialog",
        "--hidden-import=core.cloud_updater",
        "--hidden-import=core.migration_manager",
        "--hidden-import=gui.window_utils"
    ])
    cmd.append(updater_script)

    result = subprocess.run(cmd, cwd=BASE_DIR)
    if result.returncode == 0:
        exe_path = os.path.join(DIST_DIR, "SilverPremiumUpdater.exe")
        if os.path.exists(exe_path):
            root_dir = os.path.dirname(BASE_DIR)
            desktop_dir = os.path.dirname(root_dir)

            targets = [
                os.path.join(root_dir, "Silver Premium Updater.exe"),
                os.path.join(desktop_dir, "Silver Premium Updater.exe")
            ]
            for t in targets:
                try:
                    shutil.copy2(exe_path, t)
                    print(f"[OK] Distributed Updater -> {t}")
                except Exception as e:
                    print(f"[!] Could not copy updater to {t}: {e}")
            return True
    return False


if __name__ == "__main__":
    clean_previous_builds()
    success = build_executable()
    if success:
        build_standalone_updater()
        build_installer()
    sys.exit(0 if success else 1)


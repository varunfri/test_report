import os
import sys
import subprocess

def install_pyinstaller():
    print("==================================================")
    print("Installing PyInstaller build tool...")
    print("==================================================")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

def build():
    # 1. Ensure PyInstaller is installed in the active environment
    install_pyinstaller()
    
    # 2. Select correct separator for PyInstaller data files based on OS
    # Semicolon (;) on Windows, Colon (:) on macOS/Linux
    sep = ";" if os.name == 'nt' else ":"
    
    # 3. Define the PyInstaller packaging command
    # Sourced from parent directory since desktop scripts are consolidated in 'desktop/' subfolder
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onedir",          # Package as a standalone application directory (instantly launches)
        "--windowed",         # Run headless without opening an empty command prompt window
        "--name=ReportConsolidationTool",
        f"--add-data=../config{sep}config",
        f"--add-data=../services{sep}services",
        f"--add-data=../llm{sep}llm",
        "gui.py"
    ]
    
    print("\n==================================================")
    print("Starting executable compilation...")
    print("Command: " + " ".join(cmd))
    print("==================================================\n")
    
    try:
        subprocess.check_call(cmd)
        print("\n==================================================")
        print("Success! Standalone desktop application compiled.")
        if os.name == 'nt':
            print("Executable created at: dist\\ReportConsolidationTool\\ReportConsolidationTool.exe")
            print("You can zip and distribute the 'dist\\ReportConsolidationTool' folder to users.")
        else:
            print("Application bundle created under: dist/ReportConsolidationTool/")
            print("Executable located at: dist/ReportConsolidationTool/ReportConsolidationTool")
        print("==================================================\n")
    except subprocess.CalledProcessError as e:
        print(f"\nCompilation failed with error code: {e.returncode}", file=sys.stderr)
        sys.exit(e.returncode)

if __name__ == "__main__":
    build()

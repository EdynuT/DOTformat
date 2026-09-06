import sys
import subprocess
import venv
from pathlib import Path

import src.utils.build_nuitka as bn
import src.utils.build_pyinstaller as bp
from src.utils.ffmpeg_finder import ensure_ffmpeg_cli


def install_ffmpeg():
    """
    Ensures FFmpeg is available for the build, delegating to the app's own
    ffmpeg_finder (src/utils/ffmpeg_finder.py) instead of duplicating a
    Windows-only download here. That module already knows how to look for an
    existing installation (project bundle, PATH, per-user cache) and, if
    missing, download the right static build for the current OS/architecture
    (Windows zip or Linux amd64/arm64 tar.xz).
    """
    ffmpeg, ffprobe = ensure_ffmpeg_cli()
    if not ffmpeg or not ffprobe:
        print("FFmpeg is required to build DOTformat. Install it manually, put it on PATH, and re-run setup.")
        sys.exit(1)
    print(f"Using FFmpeg at: {ffmpeg}")
    return ffmpeg.parent

def create_virtualenv(venv_path):
    """
    Creates a virtual environment at the specified path if it does not already exist.
    Upgrades pip inside the virtual environment.
    """
    if not venv_path.exists():
        print(f"Creating virtual environment at: {venv_path}")
        venv.create(venv_path, with_pip=True)
        # Determine the python executable inside the venv
        if sys.platform == "win32":
            python_executable = venv_path / "Scripts" / "python.exe"
        else:
            python_executable = venv_path / "bin" / "python"
        # Upgrade pip inside the venv
        subprocess.check_call([str(python_executable), "-m", "pip", "install", "--upgrade", "pip"])
    else:
        print("Virtual environment already exists.")
        
def install_requirements(venv_path, requirements_file):
    """
    Installs the dependencies defined in the 'requirements.txt' file using the virtual environment's pip.
    """
    # Determine the python executable based on the operating system
    if sys.platform == "win32":
        python_executable = venv_path / "Scripts" / "python.exe"
    else:
        python_executable = venv_path / "bin" / "python"
        
    print("Installing dependencies...")
    with requirements_file.open("r") as req:
        for line in req:
            pkg = line.strip()
            if not pkg or pkg.startswith("#"):
                continue
            print(f"Installing: {pkg}")
            try:
                subprocess.check_call([str(python_executable), "-m", "pip", "install", pkg])
            except subprocess.CalledProcessError as e:
                print(f"Error installing {pkg}: {e}")
                print("You may need to install this package manually.")
                
if __name__ == "__main__":
    # Defines the main project paths
    project_root = Path(__file__).resolve().parent # Adjust this if your setup.py is in a different location
    # Installs FFmpeg (if not already installed) and updates the PATH
    install_ffmpeg()

    # Define the virtual environment directory and the path to the requirements.txt file
    venv_dir = project_root / ".venv"
    requirements_txt = project_root / "requirements.txt"

    # Create the virtual environment, install dependencies, and build the executable
    create_virtualenv(venv_dir)
    install_requirements(venv_dir, requirements_txt)
    choice = input("\nBuild executable: 1-pyinstaller, 2-nuitka (recommended): ").strip().lower()
    onefile = input("\nBuild as a single file? [Y/N] (N = one-folder build): ").strip().lower() == "y"
    print()
    try:
        if choice == "1":
            bp.build_pyinstaller(project_root, venv_dir, onefile=onefile)
        elif choice == "2":
            low_memory = input("Enable low memory mode for Nuitka? [Y/N]: ").strip().lower() == "y"
            print()
            bn.build_nuitka(project_root, venv_dir, low_memory=low_memory, onefile=onefile)
        else:
            print("Setup canceled. Exiting now.")
            sys.exit(1)
    except Exception as e:
        print("Build failed. Details:", e)
        sys.exit(1)

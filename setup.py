import sys
import subprocess
import venv
from pathlib import Path

# build_nuitka is deliberately NOT imported here: it imports llvmlite/numba/pymatting/
# pymupdf at module level (to locate their install paths for bundling), which would
# make this bootstrap script itself require those packages already installed just to
# start -- exactly the chicken-and-egg problem setup.py exists to avoid. It is invoked
# below as a subprocess through the venv's own python instead, via its own `-m` CLI
# entry point, once that venv actually has it installed.
from src.utils.ffmpeg_finder import ensure_ffmpeg_cli


def _venv_python(venv_path: Path) -> Path:
    """Path to the python executable inside ``venv_path``."""
    if sys.platform == "win32":
        return venv_path / "Scripts" / "python.exe"
    return venv_path / "bin" / "python"


def _ask_yes_no(question: str, default: bool) -> bool:
    """Prompts ``question [Y/n]``/``[y/N]``; an empty answer takes ``default``."""
    hint = "[Y/n]" if default else "[y/N]"
    answer = input(f"\n{question} {hint}: ").strip().lower()
    if not answer:
        return default
    return answer == "y"


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
        # Upgrade pip inside the venv
        subprocess.check_call([str(_venv_python(venv_path)), "-m", "pip", "install", "--upgrade", "pip"])
    else:
        print("Virtual environment already exists.")
        
def install_requirements(venv_path, requirements_file):
    """
    Installs the dependencies defined in the 'requirements.txt' file using the virtual environment's pip.
    """
    python_executable = _venv_python(venv_path)

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
    choice_install = _ask_yes_no("Install dependencies?", default=True)
    if choice_install:
        install_requirements(venv_dir, requirements_txt)
    else:
        print("\nSkipping dependency installation.")
    try:
        choice_build = _ask_yes_no("Build executable?", default=True)
        if choice_build:
            onefile = _ask_yes_no("Build as a single file?", default=False)
            low_memory = _ask_yes_no("Enable low memory mode?", default=False)
            print()
            venv_python = str(_venv_python(venv_dir))
            cmd = [venv_python, "-m", "src.utils.build_nuitka", "--project-root", str(project_root)]
            if low_memory:
                cmd.append("--low-memory")
            if onefile:
                cmd.append("--onefile")
            subprocess.check_call(cmd, cwd=project_root)
        else:
            print("\nSetup canceled. Exiting now.")
            sys.exit(1)
    except Exception as e:
        print("Build failed. Details:", e)
        sys.exit(1)

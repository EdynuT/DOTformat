import os
import sys
import subprocess
import venv
from pathlib import Path
import urllib.request, zipfile

# Detect the Desktop path in either English or Portuguese
home = Path.home()
desktop_path = home / "Desktop"
if not desktop_path.exists():
    desktop_path = home / "Área de Trabalho"
print("Desktop found at:", desktop_path)

def install_ffmpeg(project_root):
    """Checks if the 'ffmpeg' folder exists. If not, downloads and extracts FFmpeg."""
    ffmpeg_dir = project_root / "ffmpeg"
    if ffmpeg_dir.exists():
        print("FFmpeg is already installed.")
        # Ensure the ffmpeg binary is in the PATH
        os.environ["PATH"] += os.pathsep + str(ffmpeg_dir / "bin")
        return ffmpeg_dir

    print("FFmpeg not found. Downloading FFmpeg...")
    # URL for a static FFmpeg version for Windows (adjust if updated)
    url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    zip_path = project_root / "ffmpeg.zip"

    try:
        urllib.request.urlretrieve(url, zip_path)
    except Exception as e:
        print("Error downloading FFmpeg:", e)
        sys.exit(1)

    print("Extracting FFmpeg...")
    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(project_root)
    except Exception as e:
        print("Error extracting FFmpeg:", e)
        sys.exit(1)

    # Generally the zip extracts into a folder named something like "ffmpeg-release-essentials"
    # Adjust according to the extracted folder name if needed
    extracted_folder = project_root / "ffmpeg-release-essentials"
    if not extracted_folder.exists():
        print("Extracted FFmpeg folder not found.")
        sys.exit(1)

    # Rename the folder to "ffmpeg" for consistency
    try:
        extracted_folder.rename(ffmpeg_dir)
    except Exception as e:
        print("Error renaming the FFmpeg folder:", e)
        sys.exit(1)

    # Remove the downloaded zip file
    try:
        zip_path.unlink()
    except Exception as e:
        print("Could not remove the zip file:", e)

    # Add the FFmpeg executables path to PATH
    os.environ["PATH"] += os.pathsep + str(ffmpeg_dir / "bin")
    print("FFmpeg installed successfully!")
    return ffmpeg_dir

def create_virtualenv(venv_path):
    if not venv_path.exists():
        print(f"Creating virtual environment at: {venv_path}")
        venv.create(venv_path, with_pip=True)
    else:
        print("Virtual environment already exists.")

def install_requirements(venv_path, requirements_file):
    if sys.platform == "win32":
        pip_executable = venv_path / "Scripts" / "pip.exe"
    else:
        pip_executable = venv_path / "bin" / "pip"
        
    print("Installing dependencies...")
    # Install PyInstaller separately to prevent it from being updated in the freeze
    subprocess.check_call(f"{str(pip_executable)} install pyinstaller", shell=True)
    command = f'{str(pip_executable)} install --upgrade -r "{str(requirements_file)}"'
    try:
        subprocess.check_call(command, shell=True)
    except subprocess.CalledProcessError as e:
        print("Error installing dependencies. Details:", e)
        print("\nTry running the following command manually in the terminal:")
        print('pip install --upgrade -r "{}"'.format(str(requirements_file)))
        sys.exit(1)

def update_requirements(venv_path, requirements_file):
    if sys.platform == "win32":
        pip_executable = venv_path / "Scripts" / "pip.exe"
    else:
        pip_executable = venv_path / "bin" / "pip"
        
    print("Updating requirements.txt with installed versions (pip freeze)...")
    try:
        freeze_output = subprocess.check_output([str(pip_executable), "freeze"]).decode("utf-8").splitlines()
    except subprocess.CalledProcessError as e:
        print("Error during pip freeze. Details:", e)
        sys.exit(1)
        
    # Filter out pyinstaller (add others if needed)
    filtered_lines = [line for line in freeze_output if "pyinstaller" not in line.lower()]
    with requirements_file.open("w") as req:
        req.write("\n".join(filtered_lines) + "\n")

def build_exe(project_root):
    spec_file = project_root / "DOTformat.spec"
    print("Building executable from the spec...")
    command = f'pyinstaller "{str(spec_file)}"'
    try:
        subprocess.check_call(command, shell=True)
    except subprocess.CalledProcessError as e:
        print("Error building executable. Details:", e)
        sys.exit(1)
    print("Executable built successfully!")

if __name__ == "__main__":
    # Define the project paths
    project_root = Path(__file__).resolve().parent.parent
    # Install FFmpeg (if not installed) and update PATH
    install_ffmpeg(project_root)
    
    venv_dir = project_root / "env"
    requirements_txt = project_root / "requirements.txt"
    
    create_virtualenv(venv_dir)
    install_requirements(venv_dir, requirements_txt)
    update_requirements(venv_dir, requirements_txt)
    build_exe(project_root)
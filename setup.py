import os
import sys
import subprocess
import venv
import urllib.request, zipfile
from pathlib import Path

def install_ffmpeg(project_root):
    """
    Checks if the 'ffmpeg' folder already exists in the project.
    If not, downloads and extracts FFmpeg.
    Then, renames the extracted folder to 'ffmpeg' and adds its 'bin' directory to the PATH.
    """
    # Define the directory where FFmpeg will be installed
    ffmpeg_dir = project_root / "ffmpeg"
    if ffmpeg_dir.exists():
        print("FFmpeg is already installed.")
        # Add the ffmpeg 'bin' directory to the PATH so the executables can be found
        os.environ["PATH"] += os.pathsep + str(ffmpeg_dir / "bin")
        return ffmpeg_dir

    print("FFmpeg not found. Downloading FFmpeg...")
    # URL for a static FFmpeg build for Windows (modify if needed)
    url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    zip_path = project_root / "ffmpeg.zip"

    # Download the FFmpeg zip file
    try:
        urllib.request.urlretrieve(url, zip_path)
    except Exception as e:
        print("Error downloading FFmpeg:", e)
        sys.exit(1)

    print("Extracting FFmpeg...")
    # Extract the contents of the zip file to the project directory
    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(project_root)
    except Exception as e:
        print("Error extracting FFmpeg:", e)
        sys.exit(1)

    # Search for the extracted directory which contains both "ffmpeg" and "essentials" in its name.
    # e.g., "ffmpeg-7.1.1-essentials_build"
    extracted_folders = [d for d in project_root.iterdir() 
                         if d.is_dir() and "ffmpeg" in d.name.lower() and "essentials" in d.name.lower()]
    if not extracted_folders:
        print("Extracted FFmpeg folder not found.")
        sys.exit(1)
    
    extracted_folder = extracted_folders[0]
    print(f"Found extracted folder: {extracted_folder.name}")

    # Rename the extracted folder to "ffmpeg" for consistency
    try:
        extracted_folder.rename(ffmpeg_dir)
    except Exception as e:
        print("Error renaming the FFmpeg folder:", e)
        sys.exit(1)

    # Remove the downloaded zip file as it is no longer needed
    try:
        zip_path.unlink()
    except Exception as e:
        print("Could not remove the zip file:", e)

    # Add the ffmpeg 'bin' directory to the system PATH
    os.environ["PATH"] += os.pathsep + str(ffmpeg_dir / "bin")
    print("FFmpeg installed successfully!")
    return ffmpeg_dir

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
    # Determine the pip executable based on the operating system
    if sys.platform == "win32":
        pip_executable = venv_path / "Scripts" / "pip.exe"
    else:
        pip_executable = venv_path / "bin" / "pip"
        
    print("Installing dependencies...")
    with requirements_file.open("r") as req:
        for line in req:
            pkg = line.strip()
            if not pkg or pkg.startswith("#"):
                continue
            print(f"Installing: {pkg}")
            try:
                subprocess.check_call(f"{str(pip_executable)} install {pkg}", shell=True)
            except subprocess.CalledProcessError as e:
                print(f"Error installing {pkg}: {e}")
                print("You may need to install this package manually.")
                
def build_exe(project_root):
    """
    Calls PyInstaller using the spec file to generate an executable.
    """
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
    # Defines the main project paths
    project_root = Path(__file__).resolve().parent # Adjust this if your setup.py is in a different location
    # Installs FFmpeg (if not already installed) and updates the PATH
    install_ffmpeg(project_root)

    # Define the virtual environment directory and the path to the requirements.txt file
    venv_dir = project_root / "env"
    requirements_txt = project_root / "requirements.txt"

    # Create the virtual environment, install dependencies, and build the executable
    create_virtualenv(venv_dir)
    install_requirements(venv_dir, requirements_txt)
    build_exe(project_root)
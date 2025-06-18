import os
import sys
import subprocess
import venv
from pathlib import Path
import urllib.request, zipfile

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
    """
    if not venv_path.exists():
        print(f"Creating virtual environment at: {venv_path}")
        venv.create(venv_path, with_pip=True)
    else:
        print("Virtual environment already exists.")

def install_requirements(venv_path, requirements_file):
    """
    Installs the dependencies defined in the 'requirements.txt' file using the virtual environment's pip.
    Also installs PyInstaller separately to prevent it from being updated when freezing dependencies.
    """
    # Determine the pip executable based on the operating system
    if sys.platform == "win32":
        pip_executable = venv_path / "Scripts" / "pip.exe"
    else:
        pip_executable = venv_path / "bin" / "pip"
        
    print("Installing dependencies...")
    # Install PyInstaller separately
    subprocess.check_call(f"{str(pip_executable)} install pyinstaller", shell=True)
    # Build command to upgrade and install dependencies from requirements.txt
    command = f'{str(pip_executable)} install --upgrade -r "{str(requirements_file)}"'
    try:
        subprocess.check_call(command, shell=True)
    except subprocess.CalledProcessError as e:
        print("Error installing dependencies. Details:", e)
        print("\nTry running the following command manually in the terminal:")
        print('pip install --upgrade -r "{}"'.format(str(requirements_file)))
        sys.exit(1)

def update_requirements(venv_path, requirements_file):
    """
    Updates the 'requirements.txt' file with the currently installed versions in the virtual environment.
    Filters out PyInstaller from the pip freeze output.
    """
    # Determine the pip executable based on the operating system
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
        
    # Filter out lines containing "pyinstaller" to avoid updating this tool
    filtered_lines = [line for line in freeze_output if "pyinstaller" not in line.lower()]
    with requirements_file.open("w") as req:
        req.write("\n".join(filtered_lines) + "\n")

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

    # Create the virtual environment, install dependencies, update requirements.txt, and build the executable
    create_virtualenv(venv_dir)
    install_requirements(venv_dir, requirements_txt)
    update_requirements(venv_dir, requirements_txt)
    build_exe(project_root)
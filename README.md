# DOTFORMAT

DOTFORMAT is a project developed by Edynu to handle various file conversion and manipulation tasks, completely free and open access.

## Version

**Current Version:** 1.1.0

### Changelog

**1.1.0**

- Compatibility bug fixes with other systems lenguages (PT-BR)

- Code tranlation for english for better general understending

- Possibility of converting videos to other formats besides MP4

**1.0.0**

- Project release

## Requirements

- Python version 3.11.9

## Features

Below are the features currently available:

- **Audio to Text Conversion:** Transform audio files into text using speech recognition.

- **Image Conversion:** Convert images to different formats and resolutions.

- **PDF to PNG:** Convert PDF documents into PNG images for easy viewing.

- **PDF to Word:** Convert PDFs into editable Word documents.

- **QR Code Generator:** Create QR codes from inserted text.

- **PDF Passwords:** Generate a password for a chosen PDF file for better security.

- **Video Conversion:** Convert videos from any format to MP4, AVI or MOV for better usability.
(This script uses more CPU and RAM than usual, older systems might have a bit more slowness when using it.)

## Project Structure

The project structure is organized as follows:

```sh
DOTFORMAT/
├── src/                         
│   ├──__pycache__/              
│   ├── converters/             # File conversion modules
│   │   ├── __init__.py          
│   │   ├── audio_to_text.py     
│   │   ├── convert_image.py     
│   │   ├── convert_video.py     
│   │   ├── pdf_to_png.py        
│   │   ├── pdf_to_word.py      
│   │   ├── qrcode_generator.py 
│   │   └── pdf_password.py        
│   ├──images/                  # Image resources
│   │   ├──image.ico            # Shortcut cover for desktop
│   │   └──image.png            # Image for the executable interface
│   ├── gui.py                  # Graphical user interface
│   └── setup.py                # Creates the virtual environment and installs all dependencies
├── DOTformat.spec              # Project build specification file
├── requirements.txt            # List of required Python libraries
├── LICENCE                     # Project license
└── README.md                   # Project documentation
```

## Instalation
Follow the steps below to set up the virtual environment, install the necessary dependencies, and create the executable file:

- Clone the repository:

```sh
git clone https://github.com/EdynuT/DOTformat.git
cd DOTformat
```

- In the terminal, type:

```sh
python setup.py
```

This way, the program should install without major issues.

## Changes

- If any unofficial changes are made to the project (such as adding a new script), it is recommended to update the .spec file:

```sh
cd DOTformat
pyi-makespec --name DOTformat --onefile --windowed src\gui.py
```

- Then, create the executable file:

```sh
pyinstaller DOTformat.spec
```
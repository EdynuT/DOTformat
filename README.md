# DOTFORMAT

DOTFORMAT is a project developed by Edynu to handle various file conversion and manipulation tasks, completely free and open access.

## Version

**Current Version:** 1.1.0

### Changelog

**1.1.0**

- The folder name *converters* was changed to *models*

- Compatibility bug fixes with other systems lenguages (PT-BR)

- Automatic installation of ffmpeg and autonomous addition to the system PATH

- Code tranlation for english and added some comments for better general understending

- Possibility of converting videos to other formats besides MP4

**1.0.0**

- Project release

## Requirements

- The stronger the CPU, the better the performance

- At least 3 GB of space

- Python version 3.11.9

## Features

Below are the features currently available:

- **Audio to Text Conversion:** Transform audio files into text using speech recognition.

- **Image Conversion:** Convert images to different formats and resolutions.

- **PDF to PNG:** Convert PDF documents into PNG images for easy viewing.

- **PDF to Word:** Convert PDFs into editable Word documents.
(This script may have formatting issues when the PDF has tables or when the letters are blurred.)

- **QR Code Generator:** Create QR codes from inserted text.

- **PDF Passwords:** Generate a password for a chosen PDF file for better security.

- **Video Conversion:** Convert videos from any format to MP4, AVI or MOV for better usability.
(This script uses more CPU and RAM than usual, older systems will have a bit more slowness when using it.)

## Project Structure

The project structure is organized as follows:

```sh
DOTFORMAT/
├── src/                         
│   ├──images/                  # Image resources
│   │   ├──image.ico            # Shortcut cover for desktop
│   │   └──image.png            # Image for the executable interface            
│   ├── models/                 # File conversion models
│   │   ├──__pycache__/
│   │   ├── __init__.py          
│   │   ├── audio_to_text.py     
│   │   ├── convert_image.py     
│   │   ├── convert_video.py     
│   │   ├── pdf_password.py        
│   │   ├── pdf_to_docx.py      
│   │   ├── pdf_to_png.py        
│   │   └── qrcode_generator.py 
│   ├── gui.py                  # Graphical user interface
│   └── setup.py                # Creates the virtual environment, installs all dependencies and create the .exe file
├── DOTformat.spec              # Project build specification file
├── LICENCE                     # Project license
├── README.md                   # Project documentation
└── requirements.txt            # List of required Python libraries
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

Just a warning, when creating the executable, the log may get stuck with this message:

```sh
Building PKG (CArchive) DOTformat.pkg
```

Don't worry, the file is a little heavier than normal, so it takes some minutes to build.

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

## Contributions

We welcome contributions to improve DOTFORMAT!  
If you’d like to contribute, please follow these guidelines:

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Write clear, concise commit messages.
4. Ensure that your code follows the existing style.
5. Submit a pull request describing your changes and why they’re needed.

## License

MIT License

Copyright (c) 2025 Edynu

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
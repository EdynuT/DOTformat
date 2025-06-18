# DOTFORMAT

DOTFORMAT is a project developed by Edynu to handle various file conversion and manipulation tasks, completely free and open access.

## Version

**Current Version:** 1.1.0

### Changelog

**1.2.0**

- Added a background remover for your images with a eraser mode

    - Adjustable brush size with visual indicators

    - Brush preview follows the mouse

    - Zoom (centered on cursor) and pan with right mouse button

    - Undo for manual edits

    - Option to save or discard manual changes

    - Enhanced post-processing: clean mask, fill holes, smooth edges

    - Better usability and interface layout for manual editing

- Add a [main.py] file for a easier search for the start of the program

- Changed the [setup.py] file from [src] folder for a easier search for the setup of the system

- Improved the compatibility with other systems in general

**1.1.0**

- The folder name [converters] was changed to [models]

- Compatibility bug fixes with other systems lenguages (PT-BR)

- Automatic installation of ffmpeg and autonomous addition to the system PATH

- Code tranlation for english and added some comments for better general understending

- Possibility of converting videos to other formats besides MP4

**1.0.0**

- Project release

## Requirements

- The stronger the CPU and the more RAM, the better the performance

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
(This script uses more CPU and RAM than usual, older systems will have a bit more slowness when using it, but will work.)

- **Remove Background:** Removes the background of the image that you choose, with advanced post-processing options:

    - **Post-processing tools:** Clean mask, fill small holes, and smooth edges with one click.

    - **Manual Eraser Mode:** After automatic background removal, you can manually erase or restore areas of the image using a configurable brush.

        - Adjustable brush size (vertical slider from 1 to 100, with visual indicators).
        - Brush preview follows the mouse cursor.
        - Zoom in/out with mouse scroll (up to 500%), centered on the cursor.
        - Pan the image by dragging with the right mouse button.
        - Undo last manual actions.
        - Option to save or discard manual edits before returning to the main window.

### Manual Eraser Mode (Background Remover)

After removing the background from an image, you can further refine the result with the Manual Eraser Mode:

- **Brush Size Control:** Adjust the eraser size with a vertical slider (1–100), with "Brush Size" label and numeric indicators.
- **Brush Preview:** A red circle shows the current brush size and follows your mouse.
- **Zoom and Pan:** Use the mouse scroll to zoom in/out (up to 500%), and drag with the right mouse button to pan the image.
- **Undo:** Undo your last manual erasing actions.
- **Exit Options:** When exiting, choose to save or discard your manual edits.

This makes it easy to clean up any leftover background or restore details with precision.

## Project Structure

The project structure is organized as follows:

```sh
DOTFORMAT/
├── src/
│   ├──__pycache__/
│   ├──images/                  # Image resources
│   │   ├──image.ico            # Shortcut cover for desktop (unfortunately you still have to do this manualy)
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
│   │   ├── qrcode_generator.py
│   │   └── remove_background.py
│   └── gui.py                  # Graphical user interface
├── DOTformat.spec              # Project build specification file
├── LICENCE                     # Project license
├── main.py                     # Start button of the program
├── README.md                   # Project documentation
├── requirements.txt            # List of required Python libraries
└── setup.py                    # Creates the virtual environment, installs all dependencies and create the .exe file
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
pyi-makespec --name DOTformat --onefile --windowed main.py
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
4. Ensure that your code follows the existing style and is well commented.
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

## Message

Rarely I will make just minor bug fixes, but might happen. ¯\_(ツ)_/¯
# DOTFORMAT

DOTFORMAT is a Python project developed by Edynu to handle various file conversion and manipulation tasks, completely free and open access.

## Version

**Current Version:** 1.2.0

### Changelog

**1.2.0**

- (Finally) Added the **PDF Password** to the user interface in the pdf_manager_action function.
(How did I forget about this all this time?)

- Merged the PDF files (pdf_to_png.py, pdf_to_docx.py, and pdf_password.py) into a single one called **pdf_manager.py** to keep the code clean.

- Added a background remover script using the **rembg** library. See the [Features](#features) section for more details.

- Added a **main.py** file for easier access to the program's entry point.

- Moved the **setup.py** file from the **src** folder to the main folder for easier access to the setup script.

- Improved the video converter with a real-time progress bar and the ability to cancel conversion during processing.

- Improved compatibility with other systems in general.

**1.1.0**

- The folder name **converters** was changed to **models**.

- Compatibility bug fixes with other system languages (PT-BR).

- Automatic installation of ffmpeg and autonomous addition to the system PATH.

- Code translation to English and added some comments for better general understanding.

- Possibility of converting videos to other formats besides MP4.

**1.0.0**

- Project release.

## Requirements

- The stronger the CPU and the higher the RAM frequency, the better the performance.

- At least 2 GB of free space.

- Python version 3.11.9

## Features

Below are the features currently available:

- **Audio to Text Conversion:** Transform audio files into text using speech recognition.

- **Image Conversion:** Convert images to different formats and resolutions.

- **PDF to PNG:** Convert PDF documents into PNG images for easy viewing.

- **PDF to Word (.docx):** Convert PDFs into editable Word documents.
(This script may have formatting issues when the PDF has tables or when the text is blurry.)

- **PDF Passwords:** Set a password for a chosen PDF file for better security.

- **QR Code Generator:** Create QR codes from inserted text.

- **Video Conversion:** Convert videos from any format to MP4, AVI, or MOV for better usability.

    - MP4 for better image resolution. Most common for everything.

    - AVI for higher frame rate at the expense of quality.

    - MOV for good resolution and frame rate.

(This script uses more CPU and RAM than usual. Older systems may experience some slowness when using it, but it will work.)

- **Remove Background:** Removes the background of the image you choose, with advanced post-processing options:

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
│   │   ├──image.ico            # Shortcut icon for desktop (unfortunately you still have to do this manually)
│   │   └──image.png            # Image for the executable interface            
│   ├── models/                 # File conversion models
│   │   ├──__pycache__/
│   │   ├── __init__.py
│   │   ├── audio_to_text.py
│   │   ├── convert_image.py
│   │   ├── convert_video.py
│   │   ├── pdf_manager.py
│   │   ├── qrcode_generator.py
│   │   └── remove_background.py
│   └── gui.py                  # Graphical user interface
├── DOTformat.spec              # Project build specification file
├── LICENSE                     # Project license
├── main.py                     # Program entry point
├── README.md                   # Project documentation
├── requirements.txt            # List of required Python libraries
└── setup.py                    # Creates the virtual environment, installs all dependencies, and creates the .exe file
```

## Installation
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

Just a warning: when creating the executable, the log may get stuck with this message:

```sh
Building PKG (CArchive) DOTformat.pkg
```

Don't worry, the file is a little larger than normal, so it takes a few minutes to build.

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

It is highly recommended to use DOTFORMAT version >=1.2.0 if you want to have access to the background remover and PDF password maker.

I will rarely make small bug fixes, but it may happen at some point.
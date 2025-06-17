from pdf2image import convert_from_path
import os

def pdf_to_png(pdf_file, output_dir):
    """
    Converts each page of a PDF file into an individual PNG image.
    
    Parameters:
      - pdf_file: Path to the input PDF.
      - output_dir: Directory where PNG images will be saved.
      
    Returns:
      A tuple (True, success message) if successful, otherwise (False, error message).
    """
    try:
        pages = convert_from_path(pdf_file)
        for i, page in enumerate(pages):
            output_path = os.path.join(output_dir, f"page_{i + 1}.png")
            page.save(output_path, 'PNG')
        return True, f"Images successfully saved in '{output_dir}'!"
    except Exception as e:
        return False, str(e)
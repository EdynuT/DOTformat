from pdf2docx import Converter
import os

def pdf_to_docx(pdf_file, docx_file):
    """
    Converts a PDF file to a DOCX file.
    
    Parameters:
      - pdf_file: Path to the input PDF.
      - docx_file: Path where the output DOCX will be saved.
      
    Returns:
      A tuple (True, success message) if conversion is successful, otherwise (False, error message).
    """
    try:
        cv = Converter(pdf_file)
        cv.convert(docx_file, start=0, end=None)
        cv.close()
        return True, f"DOCX file saved successfully at '{docx_file}'!"
    except Exception as e:
        return False, str(e)
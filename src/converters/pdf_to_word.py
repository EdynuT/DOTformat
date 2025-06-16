from pdf2docx import Converter
import os

def pdf_to_docx(pdf_file, docx_file):
    try:
        cv = Converter(pdf_file)
        cv.convert(docx_file, start=0, end=None)
        cv.close()
        return True, f"The DOCX file was saved successfully at '{docx_file}'!"
    except Exception as e:
        return False, str(e)
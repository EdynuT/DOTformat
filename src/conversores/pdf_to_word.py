from pdf2docx import Converter
import os

def pdf_to_word(pdf_file, docx_file):
    try:
        cv = Converter(pdf_file)
        cv.convert(docx_file, start=0, end=None)
        cv.close()
        return True, f"O arquivo DOCX foi salvo em '{docx_file}' com sucesso!"
    except Exception as e:
        return False, str(e)
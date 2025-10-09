import os
import PyPDF2
from pdf2docx import Converter
from pdf2image import convert_from_path

def pdf_to_docx(pdf_file, docx_file):
    """
    Converts a PDF file to a DOCX file.
    """
    if not pdf_file or not docx_file:
        return False, "Missing input PDF or output DOCX path."
    try:
        cv = Converter(pdf_file)
        cv.convert(docx_file, start=0, end=None)
        cv.close()
        return True, f"DOCX file saved successfully at '{docx_file}'!"
    except Exception as e:
        try:
            # Attempt to close converter if partially opened
            cv.close()  # type: ignore
        except Exception:
            pass
        return False, str(e)

def protect_pdf(input_pdf, password, output_pdf):
    """
    Protects a PDF file by adding a password provided by the user.
    Parameters:
      - input_pdf (str): Path to the input PDF file.
      - password (str): The password to secure the PDF (must be provided by the user).
      - output_pdf (str): Path where the protected PDF will be saved.
    """
    if not input_pdf or not output_pdf:
        return False, "Missing input or output path."
    try:
        pdf_reader = PyPDF2.PdfReader(input_pdf)
        pdf_writer = PyPDF2.PdfWriter()
        for page in pdf_reader.pages:
            pdf_writer.add_page(page)
        if password:
            pdf_writer.encrypt(password)
        with open(output_pdf, "wb") as pdf_out:
            pdf_writer.write(pdf_out)
        return True, f"Protected PDF saved at '{output_pdf}'!"
    except Exception as e:
        return False, str(e)



def pdf_to_png(pdf_file, output_dir):
    """
    Converts each page of a PDF file into an individual PNG image.
    """
    if not pdf_file or not output_dir:
        return False, "Missing input PDF or output directory."
    try:
        pages = convert_from_path(pdf_file)
        for i, page in enumerate(pages):
            output_path = os.path.join(output_dir, f"page_{i + 1}.png")
            page.save(output_path, 'PNG')
        return True, f"Images successfully saved in '{output_dir}'!"
    except Exception as e:
        return False, str(e)
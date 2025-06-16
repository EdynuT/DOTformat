import os
import PyPDF2
import random
from tkinter import Tk
from tkinter.filedialog import askopenfilename

def generate_password():
    return str(random.randint(10000, 99999))

def protect_pdf(input_pdf, output_pdf, password):
    # Open the input PDF file
    pdf_reader = PyPDF2.PdfReader(input_pdf)
    pdf_writer = PyPDF2.PdfWriter()
    
    # Add all pages to the writer
    for page_num in range(len(pdf_reader.pages)):
        pdf_writer.add_page(pdf_reader.pages[page_num])
    
    # Set the PDF password
    pdf_writer.encrypt(password)
    
    # Write the protected PDF to the output file
    with open(output_pdf, "wb") as pdf_out:
        pdf_writer.write(pdf_out)

# Example usage
Tk().withdraw()  # Hide the main tkinter window
input_pdf = askopenfilename(title="Select the PDF file")
if not input_pdf:
    print("No file selected. Exiting the script.")
else:
    output_pdf = os.path.join(os.path.dirname(input_pdf), "protected_file.pdf")
    password = generate_password()
    print(f"The generated password for the PDF is: {password}")
    protect_pdf(input_pdf, output_pdf, password)
    print(f"Protected PDF saved at: {output_pdf}")
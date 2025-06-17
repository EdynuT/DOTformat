import os
import PyPDF2
import random
from tkinter import Tk
from tkinter.filedialog import askopenfilename

def generate_password():
    """
    Generates a random 5-digit numeric password.
    
    Returns:
        A string representing a random 5-digit password.
    """
    return str(random.randint(10000, 99999))

def protect_pdf(input_pdf, output_pdf, password):
    """
    Protects a PDF file by adding a password.
    
    Parameters:
      - input_pdf (str): Path to the input PDF file.
      - output_pdf (str): Path where the protected PDF will be saved.
      - password (str): The password to secure the PDF.
      
    Process:
      1. Reads the input PDF.
      2. Copies all pages into a new PDF writer object.
      3. Encrypts the new PDF with the provided password.
      4. Writes the encrypted PDF to the output file.
    """
    # Open the input PDF file using PyPDF2
    pdf_reader = PyPDF2.PdfReader(input_pdf)
    pdf_writer = PyPDF2.PdfWriter()
    
    # Add every page from the input PDF to the writer
    for page in pdf_reader.pages:
        pdf_writer.add_page(page)
    
    # Encrypt the PDF with the provided password
    pdf_writer.encrypt(password)
    
    # Write the encrypted PDF to the specified output file
    with open(output_pdf, "wb") as pdf_out:
        pdf_writer.write(pdf_out)

# Main execution block for demonstration purposes
if __name__ == "__main__":
    # Hide the main tkinter window so that only file dialogs are shown
    Tk().withdraw()
    
    # Ask the user to select an input PDF file
    input_pdf = askopenfilename(title="Select the PDF file")
    if not input_pdf:
        print("No file selected. Exiting the script.")
    else:
        # Set the output PDF path to be in the same directory as the input file
        output_pdf = os.path.join(os.path.dirname(input_pdf), "protected_file.pdf")
        
        # Generate a random password for the PDF
        password = generate_password()
        print(f"The generated password for the PDF is: {password}")
        
        # Protect the PDF by applying the generated password
        protect_pdf(input_pdf, output_pdf, password)
        print(f"Protected PDF saved at: {output_pdf}")
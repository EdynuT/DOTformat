from pdf2image import convert_from_path
import os

def pdf_to_png(pdf_file, output_dir):
    try:
        pages = convert_from_path(pdf_file)
        for i, page in enumerate(pages):
            output_path = os.path.join(output_dir, f"page_{i + 1}.png")
            page.save(output_path, 'PNG')
        return True, f"Images were successfully saved in '{output_dir}'!"
    except Exception as e:
        return False, str(e)
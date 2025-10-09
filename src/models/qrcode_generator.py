import qrcode

def generate_qr_code(text, save_path):
    """
    Generates a QR code from the provided text or URL and saves it as a PNG image.
    
    Parameters:
      - text: The text or URL to encode in the QR code.
      - save_path: The path where the QR code image will be saved.
      
    Returns:
      A tuple (True, success message) if successful, otherwise (False, error message).
    """
    if not text or not save_path:
        return False, "Missing text or save path."
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(text)
        qr.make(fit=True)

        img = qr.make_image(fill_color='black', back_color='white')
        img.save(save_path)
        return True, f"QR Code saved at: {save_path}"
    except Exception as e:
        return False, str(e)
import qrcode

def generate_qr_code(text, save_path):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(text)
    qr.make(fit=True)

    img = qr.make_image(fill='black', back_color='white')
    img.save(save_path)
    return True, f"QR Code salvo em: {save_path}"

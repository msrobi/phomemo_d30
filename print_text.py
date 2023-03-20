import click
import serial
from wand.image import Image
from wand.font import Font
import PIL.Image
import image_helper
import os


@click.command()
@click.argument('text')
@click.option('--font', default="Helvetica", help='Path to TTF font file')
@click.option('--fruit', is_flag=True, show_default=True, default=False,
              help='Enable offsets to print on a fruit label')
@click.option('--show', is_flag=True, show_default=True, default=False,
              help='Show output, will not print')
@click.option('--qrcode', default="", help='Text for QR Code')
def main(text, font, fruit, qrcode, show):
    if not show:
      port = serial.Serial("/dev/rfcomm1", timeout=10)

    filename = generate_image(text, font, fruit, qrcode, show, "temp.png")
    if not show:
      header(port)
    if show:
      show_image(filename)
    else:
      print_image(port, filename)
    if not show:
      print_image(port, filename)
    os.remove(filename)
    if qrcode:
        os.remove("qrcode.png")


def header(port):
    # printer initialization sniffed from Android app "Print Master"
    packets = [
        '1f1138',
        '1f11121f1113',
        '1f1109',
        '1f1111',
        '1f1119',
        '1f1107',
        '1f110a1f110202'
    ]

    for packet in packets:
        port.write(bytes.fromhex(packet))
        port.flush()


def generate_image(text, font, fruit, qrcode, show, filename):
    font = Font(path=font)
    if fruit:
        width, height = 240, 80
    elif qrcode:
        generate_qrcode(qrcode, "qrcode.png")
        width, height = 224, 80
    else:
        width, height = 288, 88

    with Image(width=width, height=height, background="white") as img:
        # center text, fill canvas
        img.caption(text, font=font, gravity="center")

        # extent and rotate image
        img.background_color = "white"
        img.gravity = "center"
        if fruit:
            img.extent(width=320, height=96, x=-60)
        elif qrcode:
            img.extent(width=320, height=96, x=-96)
            qr_img=Image(filename="qrcode.png")
            img.composite(qr_img, left=8, top=8)
        else:
            img.extent(width=320, height=96)
        img.rotate(270)
        img.save(filename=filename)

    return filename


def generate_qrcode(text, filename):
    import qrcode
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=1,
        border=1,
    )
    qr.add_data(text)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img.save(filename) 
    image = PIL.Image.open(filename)
    img_resize = image.resize((80,80), PIL.Image.Resampling.LANCZOS)
    img_resize.save(filename)


def show_image(filename):
    import matplotlib.pyplot as plt
    import matplotlib.image as mpimg
    import pygame

    image = pygame.image.load(filename)
    rot_img = pygame.transform.rotate(image, 270)
    pygame.image.save(rot_img, "preview.png")
    plt.imshow(mpimg.imread('preview.png'))
    plt.show()
    os.remove("preview.png")


def print_image(port, filename):
    width = 96

    with Image.open(filename) as src:
        image = image_helper.preprocess_image(src, width)

    # printer initialization sniffed from Android app "Print Master"
    output = '1f1124001b401d7630000c004001'

    # adapted from https://github.com/theacodes/phomemo_m02s/blob/main/phomemo_m02s/printer.py
    for chunk in image_helper.split_image(image):
        output = bytearray.fromhex(output)

        bits = image_helper.image_to_bits(chunk)
        for line in bits:
            for byte_num in range(width // 8):
                byte = 0
                for bit in range(8):
                    pixel = line[byte_num * 8 + bit]
                    byte |= (pixel & 0x01) << (7 - bit)
                output.append(byte)

        port.write(output)
        port.flush()

        output = ''


if __name__ == '__main__':
    main()

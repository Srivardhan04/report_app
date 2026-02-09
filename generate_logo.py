"""
Generate a simple KL University logo as a PNG placeholder.
Run this once before starting the server.
"""

import struct
import zlib
from pathlib import Path


def create_kl_logo():
    """Create a minimal KL logo PNG with blue background and white 'KL' text."""
    width, height = 200, 200

    # Create pixel data: a blue circle-ish background with 'KL' text
    pixels = []
    for y in range(height):
        row = []
        for x in range(width):
            # Distance from center
            cx, cy = width // 2, height // 2
            dist = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            radius = 90

            if dist <= radius:
                # Inside circle: blue background
                # Simple "KL" pattern using pixel art
                # K region: x in [55-75], L region: x in [110-140]
                lx = x - cx + 100  # normalize to 0-200 center
                ly = y - cy + 100

                is_text = False

                # Letter K
                if 60 <= lx <= 70 and 65 <= ly <= 135:
                    is_text = True  # vertical bar
                elif 70 <= lx <= 90 and abs(ly - 100) <= (lx - 70) * 1.5 + 2 and abs(ly - 100) >= (lx - 70) * 1.5 - 8:
                    is_text = True  # diagonal strokes

                # Letter L
                elif 110 <= lx <= 120 and 65 <= ly <= 135:
                    is_text = True  # vertical bar
                elif 120 <= lx <= 145 and 125 <= ly <= 135:
                    is_text = True  # horizontal bar

                if is_text:
                    row.extend([255, 255, 255])  # white text
                else:
                    row.extend([26, 35, 126])  # KL blue #1a237e
            else:
                row.extend([255, 255, 255])  # white background (transparent effect)

        pixels.append(bytes([0] + row))  # filter byte + row data

    # Encode as PNG
    raw_data = b''.join(pixels)

    def make_chunk(chunk_type, data):
        chunk = chunk_type + data
        return struct.pack('>I', len(data)) + chunk + struct.pack('>I', zlib.crc32(chunk) & 0xFFFFFFFF)

    # PNG signature
    signature = b'\x89PNG\r\n\x1a\n'

    # IHDR
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    ihdr = make_chunk(b'IHDR', ihdr_data)

    # IDAT
    compressed = zlib.compress(raw_data, 9)
    idat = make_chunk(b'IDAT', compressed)

    # IEND
    iend = make_chunk(b'IEND', b'')

    png_data = signature + ihdr + idat + iend

    logo_path = Path(__file__).parent / "static" / "images" / "kl_logo.png"
    logo_path.parent.mkdir(parents=True, exist_ok=True)
    logo_path.write_bytes(png_data)
    print(f"Logo created at: {logo_path}")
    return logo_path


if __name__ == "__main__":
    create_kl_logo()

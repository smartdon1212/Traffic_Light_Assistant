"""Generate synthetic red/yellow/green test images under `images/`.

Run: python create_images.py
"""
import os
import cv2
import numpy as np


def make_image(bgr_color, path, size=(200, 200), center=None, radius=40):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img = np.zeros((size[1], size[0], 3), dtype=np.uint8)
    if center is None:
        center = (size[0] // 2, size[1] // 2)
    cv2.circle(img, center, radius, bgr_color, -1)
    cv2.imwrite(path, img)


def main():
    make_image((0, 0, 255), "images/red.png")
    make_image((0, 255, 255), "images/yellow.png")
    make_image((0, 255, 0), "images/green.png")
    print("Wrote images/red.png, images/yellow.png, images/green.png")


if __name__ == "__main__":
    main()

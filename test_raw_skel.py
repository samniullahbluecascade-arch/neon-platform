import sys
import cv2
import numpy as np
from skimage.morphology import skeletonize

def main():
    for img_name, width_in in [("Ground_Truth\\20 1.67.png", 20.0), ("Ground_Truth\\36 2.38.png", 36.0)]:
        img = cv2.imread(img_name, cv2.IMREAD_UNCHANGED)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        
        # Skeletonize
        skel = skeletonize(mask > 0)
        n_skel = np.sum(skel)
        
        # Calculate ppi
        ppi = gray.shape[1] / width_in
        
        # Calculate LOC
        loc_m = n_skel / ppi * 0.0254
        print(f"{img_name}: ppi={ppi:.1f}, skel_px={n_skel}, loc={loc_m:.3f}m")

if __name__ == '__main__':
    main()

# Rank_Suit_Isolator.py  — capture flattened card corners for rank/suit training
import cv2
import numpy as np
import time
import os
import uuid
import Cards
import sys

# Try to import Picamera2 (if on Pi)
try:
    from picamera2 import Picamera2, Preview
except ImportError:
    Picamera2 = None
    Preview = None

# ---------- Paths & Sizes ----------
img_path    = os.path.join(os.path.dirname(__file__), 'Card_Imgs')
os.makedirs(img_path, exist_ok=True)

IM_WIDTH    = 1280
IM_HEIGHT   = 720
RANK_W, RANK_H = 70, 125
SUIT_W, SUIT_H = 70, 100

# ---------- Camera Choice ----------
# 1 = PiCamera2, 2 = USB
PiOrUSB = 1

if PiOrUSB == 1 and Picamera2:
    # — Picamera2 setup with DRM preview (no Qt) —
    picam2 = Picamera2()
    cfg = picam2.create_preview_configuration({"size": (IM_WIDTH, IM_HEIGHT)})
    picam2.configure(cfg)
    try:
        picam2.start_preview(Preview.DRM)
    except Exception:
        pass
    picam2.start()
    time.sleep(1)   # auto‑exposure warm‑up

elif PiOrUSB == 2:
    # — USB webcam setup (we'll use cv2.imshow here) —
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, IM_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, IM_HEIGHT)

else:
    print("No Picamera2 available and PiOrUSB=1; exiting.")
    sys.exit(1)

# ---------- Labels to Capture ----------
labels = ['Queen']

#    [ 'Ace','Two','Three','Four','Five','Six','Seven','Eight','Nine','Ten','Jack','Queen','King', 'Spades','Diamonds','Clubs','Hearts']

i = 1
for name in labels:
    filename = f"{name}.jpg"
    print(f"\n--- Capture {filename} ---")

    # ─── Grab a frame ─────────────────────────────────────────────
    if PiOrUSB == 1:
        # On Pi, we already have DRM preview. Just wait for Enter.
        input("Position the card over the camera, then press ENTER to capture…")
        frame = picam2.capture_array()

    else:
        # USB: show a live OpenCV window and wait for 'p'
        while True:
            ret, frame = cap.read()
            if not ret:
                raise RuntimeError("USB camera read failed")
            cv2.imshow("USB Preview (press p)", frame)
            if cv2.waitKey(1) & 0xFF == ord('p'):
                break
        cv2.destroyWindow("USB Preview (press p)")

    # ─── Preprocess & find the card contour ─────────────────────────
    gray   = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur   = cv2.GaussianBlur(gray, (5,5), 0)
    _, thresh = cv2.threshold(blur, 100, 255, cv2.THRESH_BINARY)
    cnts, _  = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        print("⚠️ No contours found, skipping this label.")
        continue
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)
    card = cnts[0]

    # ─── Flatten to 200×300 ────────────────────────────────────────
    peri   = cv2.arcLength(card, True)
    approx = cv2.approxPolyDP(card, 0.01*peri, True)
    pts    = np.float32(approx)
    x, y, w, h = cv2.boundingRect(card)
    warp = Cards.flattener(frame, pts, w, h)

    # ─── Extract & threshold the corner ─────────────────────────────
    corner      = warp[0:84, 0:32]
    corner_zoom = cv2.resize(corner, (0,0), fx=4, fy=4)
    cb_blur     = cv2.GaussianBlur(corner_zoom, (5,5), 0)
    _, corner_th= cv2.threshold(cb_blur, 155, 255, cv2.THRESH_BINARY_INV)

    # ─── Isolate rank vs. suit ─────────────────────────────────────
    # if i <= 13:
    #     roi = corner_th[20:185, 0:128]
    # else:
    #     roi = corner_th[186:336, 0:128]
    if i <= 13:   # rank (now captures the full “10”)
        roi = corner_th[10:200,  0:160]   # ← wider + slightly taller
    else:         # suit
        roi = corner_th[200:360, 0:160]

    cnts2, _ = cv2.findContours(roi, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts2:
        print("⚠️ No ROI contours, skipping.")
        continue
    cnts2 = sorted(cnts2, key=cv2.contourArea, reverse=True)
    x2, y2, w2, h2 = cv2.boundingRect(cnts2[0])
    crop = roi[y2:y2+h2, x2:x2+w2]

    if i <= 13:
        final_img = cv2.resize(crop, (RANK_W, RANK_H))
    else:
        final_img = cv2.resize(crop, (SUIT_W, SUIT_H))

    # ─── Show & Save ───────────────────────────────────────────────
    if PiOrUSB == 2:
        # Only show in USB mode
        cv2.imshow("Isolated", final_img)
        print('Press "c" to save, any other key to skip.')
        key = cv2.waitKey(0) & 0xFF
        cv2.destroyWindow("Isolated")
        if key != ord('c'):
            print("Skipped.")
            i += 1
            continue
    else:
        # On Pi, just save automatically after capture
        print("Saving…")

    out = os.path.join(img_path, filename)
    cv2.imwrite(out, final_img)
    print(f"✔ Saved {out}")

    i += 1

# ─── Cleanup ─────────────────────────────────────────────────────────
if PiOrUSB == 1 and Picamera2:
    try: picam2.stop_preview()
    except: pass
    picam2.stop()
elif PiOrUSB == 2:
    cap.release()
cv2.destroyAllWindows()





### Takes a card picture and creates a top-down 200x300 flattened image
### of it. Isolates the suit and rank and saves the isolated images.
### Runs through A - K ranks and then the 4 suits.

# # Import necessary packages
# import cv2
# import numpy as np
# import time
# import Cards
# import os
# from picamera2 import Picamera2


# img_path = os.path.dirname(os.path.abspath(__file__)) + '/Card_Imgs/'

# IM_WIDTH = 1280
# IM_HEIGHT = 720

# RANK_WIDTH = 70
# RANK_HEIGHT = 125

# SUIT_WIDTH = 70
# SUIT_HEIGHT = 100

# # If using a USB Camera instead of a PiCamera, change PiOrUSB to 2
# PiOrUSB = 1

# if PiOrUSB == 1:
#     # Import packages from picamera library
#     from Picamera2.array import PiRGBArray
#     from picamera2 import Picamera2


#     # Initialize PiCamera and grab reference to the raw capture
#     camera = Picamera2()
#     camera.resolution = (IM_WIDTH,IM_HEIGHT)
#     camera.framerate = 10
#     rawCapture = PiRGBArray(camera, size=(IM_WIDTH,IM_HEIGHT))

# if PiOrUSB == 2:
#     # Initialize USB camera
#     cap = cv2.VideoCapture(0)

# # Use counter variable to switch from isolating Rank to isolating Suit
# i = 1

# for Name in ['Ace','Two','Three','Four','Five','Six','Seven','Eight',
#              'Nine','Ten','Jack','Queen','King','Spades','Diamonds',
#              'Clubs','Hearts']:

#     filename = Name + '.jpg'

#     print('Press "p" to take a picture of ' + filename)
    
    

#     if PiOrUSB == 1: # PiCamera
#         rawCapture.truncate(0)
#         # Press 'p' to take a picture
#         for frame in camera.capture_continuous(rawCapture, format="bgr",use_video_port=True):

#             image = frame.array
#             cv2.imshow("Card",image)
#             key = cv2.waitKey(1) & 0xFF
#             if key == ord("p"):
#                 break

#             rawCapture.truncate(0)

#     if PiOrUSB == 2: # USB camera
#         # Press 'p' to take a picture
#         while(True):

#             ret, frame = cap.read()
#             cv2.imshow("Card",frame)
#             key = cv2.waitKey(1) & 0xFF
#             if key == ord("p"):
#                 image = frame
#                 break

#     # Pre-process image
#     gray = cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
#     blur = cv2.GaussianBlur(gray,(5,5),0)
#     retval, thresh = cv2.threshold(blur,100,255,cv2.THRESH_BINARY)

#     # Find contours and sort them by size
#     dummy,cnts,hier = cv2.findContours(thresh,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
#     cnts = sorted(cnts, key=cv2.contourArea,reverse=True)

#     # Assume largest contour is the card. If there are no contours, print an error
#     flag = 0
#     image2 = image.copy()

#     if len(cnts) == 0:
#         print('No contours found!')
#         quit()

#     card = cnts[0]

#     # Approximate the corner points of the card
#     peri = cv2.arcLength(card,True)
#     approx = cv2.approxPolyDP(card,0.01*peri,True)
#     pts = np.float32(approx)

#     x,y,w,h = cv2.boundingRect(card)

#     # Flatten the card and convert it to 200x300
#     warp = Cards.flattener(image,pts,w,h)

#     # Grab corner of card image, zoom, and threshold
#     corner = warp[0:84, 0:32]
#     #corner_gray = cv2.cvtColor(corner,cv2.COLOR_BGR2GRAY)
#     corner_zoom = cv2.resize(corner, (0,0), fx=4, fy=4)
#     corner_blur = cv2.GaussianBlur(corner_zoom,(5,5),0)
#     retval, corner_thresh = cv2.threshold(corner_blur, 155, 255, cv2. THRESH_BINARY_INV)

#     # Isolate suit or rank
#     if i <= 13: # Isolate rank
#         rank = corner_thresh[20:185, 0:128] # Grabs portion of image that shows rank
#         dummy, rank_cnts, hier = cv2.findContours(rank, cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
#         rank_cnts = sorted(rank_cnts, key=cv2.contourArea,reverse=True)
#         x,y,w,h = cv2.boundingRect(rank_cnts[0])
#         rank_roi = rank[y:y+h, x:x+w]
#         rank_sized = cv2.resize(rank_roi, (RANK_WIDTH, RANK_HEIGHT), 0, 0)
#         final_img = rank_sized

#     if i > 13: # Isolate suit
#         suit = corner_thresh[186:336, 0:128] # Grabs portion of image that shows suit
#         dummy, suit_cnts, hier = cv2.findContours(suit, cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
#         suit_cnts = sorted(suit_cnts, key=cv2.contourArea,reverse=True)
#         x,y,w,h = cv2.boundingRect(suit_cnts[0])
#         suit_roi = suit[y:y+h, x:x+w]
#         suit_sized = cv2.resize(suit_roi, (SUIT_WIDTH, SUIT_HEIGHT), 0, 0)
#         final_img = suit_sized

#     cv2.imshow("Image",final_img)

#     # Save image
#     print('Press "c" to continue.')
#     key = cv2.waitKey(0) & 0xFF
#     if key == ord('c'):
#         cv2.imwrite(img_path+filename,final_img)

#     i = i + 1

# cv2.destroyAllWindows()
# camera.close()

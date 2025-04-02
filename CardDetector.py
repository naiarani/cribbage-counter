############## Python-OpenCV Playing Card Detector ###############
#
# Author: Evan Juras
# Editor: Naia Lum
# Date: 9/5/17
# Description: Python script to detect and identify playing cards
# from a PiCamera video feed.
#

import cv2
import numpy as np
import time
import os
import shutil
import Cards
from picamera2 import Picamera2, Preview

# # Save image function
# SAVE_FOLDER = 'captured_images'
# if os.path.exists(SAVE_FOLDER):
#     shutil.rmtree(SAVE_FOLDER)
# os.makedirs(SAVE_FOLDER)

# def save_image(image, index):
#     filename = f"{SAVE_FOLDER}/image_{index}.jpg"
#     cv2.imwrite(filename, image)
#     print(f"Image saved as {filename}")

# # Initialize constants and variables
# IM_WIDTH = 1280
# IM_HEIGHT = 720
# FRAME_RATE = 10

# frame_rate_calc = 1
# freq = cv2.getTickFrequency()
# font = cv2.FONT_HERSHEY_SIMPLEX

# # Initialize camera with Picamera2
# picam2 = Picamera2()
# preview_config = picam2.create_preview_configuration({"size": (IM_WIDTH, IM_HEIGHT)})
# picam2.configure(preview_config)
# picam2.start_preview(Preview.DRM, x=1000, y=100)
# picam2.start()
# time.sleep(1)

# # Load the train rank and suit images
# path = os.path.dirname(os.path.abspath(__file__))
# train_ranks = Cards.load_ranks(path + '/Card_Imgs/')
# train_suits = Cards.load_suits(path + '/Card_Imgs/')

# # Main loop
# cam_quit = 0

# try:
#     while cam_quit == 0:
#         image = picam2.capture_array()

#         # Start timer for FPS calculation
#         t1 = cv2.getTickCount()

#         # Pre-process camera image (gray, blur, and threshold it)
#         pre_proc = Cards.preprocess_image(image)

#         # Find and sort contours
#         cnts_sort, cnt_is_card = Cards.find_cards(pre_proc)
#         cards = []
#         k = 0

#         if len(cnts_sort) != 0:
#             for i in range(len(cnts_sort)):
#                 if cnt_is_card[i] == 1:
#                     cards.append(Cards.preprocess_card(cnts_sort[i], image))
#                     cards[k].best_rank_match, cards[k].best_suit_match, \
#                     cards[k].rank_diff, cards[k].suit_diff = Cards.match_card(
#                         cards[k], train_ranks, train_suits
#                     )

#                     image = Cards.draw_results(image, cards[k])
#                     k += 1

#             if len(cards) != 0:
#                 temp_cnts = [card.contour for card in cards]
#                 cv2.drawContours(image, temp_cnts, -1, (255, 0, 0), 2)

#         # Draw framerate
#         cv2.putText(image, "FPS: " + str(int(frame_rate_calc)), (10, 26),
#                     font, 0.7, (255, 0, 255), 2, cv2.LINE_AA)

#         # Display the updated image on the DRM preview
#         picam2.set_overlay(image)

#         # Calculate framerate
#         t2 = cv2.getTickCount()
#         time1 = (t2 - t1) / freq
#         frame_rate_calc = 1 / time1

#         # Save each detected card
#         for idx, card in enumerate(cards):
#             save_image(card.image, idx)

#         # Status messages
#         if cards:
#             print(f"Detected {len(cards)} cards.")
#             for card in cards:
#                 print(f"Detected card: {card.name}")
#         else:
#             print("No cards detected.")

#         time.sleep(0.2)

# except KeyboardInterrupt:
#     print("\n[INFO] Program terminated by user.")

# # Cleanup
# picam2.stop_preview()
# picam2.stop()




# import cv2
# import numpy as np
# import time
# import os
# import shutil
# import Cards
# from picamera2 import Picamera2, Preview

# # Save image function
# SAVE_FOLDER = 'captured_images'
# if os.path.exists(SAVE_FOLDER):
#     shutil.rmtree(SAVE_FOLDER)
# os.makedirs(SAVE_FOLDER)

# def save_image(image, index):
#     filename = f"{SAVE_FOLDER}/image_{index}.jpg"
#     cv2.imwrite(filename, image)
#     # print(f"Image saved as {filename}")

# # Initialize constants and variables
# IM_WIDTH = 1280
# IM_HEIGHT = 720
# FRAME_RATE = 10

# frame_rate_calc = 1
# freq = cv2.getTickFrequency()
# font = cv2.FONT_HERSHEY_SIMPLEX

# # Initialize camera with Picamera2
# picam2 = Picamera2()
# preview_config = picam2.create_preview_configuration({"size": (IM_WIDTH, IM_HEIGHT)})
# picam2.configure(preview_config)
# picam2.start_preview(Preview.DRM, x=200, y=500)
# picam2.start()
# time.sleep(1)

# # Load the train rank and suit images
# path = os.path.dirname(os.path.abspath(__file__))
# train_ranks = Cards.load_ranks(path + '/Card_Imgs/')
# train_suits = Cards.load_suits(path + '/Card_Imgs/')

# # Main loop
# cam_quit = 0
# detected_cards = set()  # Using a set to ensure uniqueness

# try:
#     while cam_quit == 0:
#         image = picam2.capture_array()

#         # Start timer for FPS calculation
#         t1 = cv2.getTickCount()

#         # Pre-process camera image (gray, blur, and threshold it)
#         pre_proc = Cards.preprocess_image(image)

#         # Find and sort contours
#         cnts_sort, cnt_is_card = Cards.find_cards(pre_proc)
#         cards = []
#         k = 0

#         if len(cnts_sort) != 0:
#             for i in range(len(cnts_sort)):
#                 if cnt_is_card[i] == 1:
#                     cards.append(Cards.preprocess_card(cnts_sort[i], image))
#                     cards[k].best_rank_match, cards[k].best_suit_match, \
#                     cards[k].rank_diff, cards[k].suit_diff = Cards.match_card(
#                         cards[k], train_ranks, train_suits
#                     )

#                     image = Cards.draw_results(image, cards[k])
#                     k += 1

#             if len(cards) != 0:
#                 temp_cnts = [card.contour for card in cards]
#                 cv2.drawContours(image, temp_cnts, -1, (255, 0, 0), 2)

#         # Draw framerate
#         cv2.putText(image, "FPS: " + str(int(frame_rate_calc)), (10, 26),
#                     font, 0.7, (255, 0, 255), 2, cv2.LINE_AA)

#         # Display the updated image on the DRM preview
#         picam2.set_overlay(image)

#         # Calculate framerate
#         t2 = cv2.getTickCount()
#         time1 = (t2 - t1) / freq
#         frame_rate_calc = 1 / time1

#         # Save each detected card (use card.warp instead of card.image)
#         for idx, card in enumerate(cards):
#             save_image(card.warp, idx)

#         # Status messages
#         if cards:
#             print(f"Detected {len(cards)} cards.")
#             for card in cards:
#                 print(f"Detected card: {card.best_rank_match} of {card.best_suit_match}")
#         else:
#             print("No cards detected.")

#         time.sleep(0.2)

# except KeyboardInterrupt:
#     print("\n[INFO] Program terminated by user.")

# # Cleanup
# picam2.stop_preview()
# picam2.stop()




# import cv2
# import numpy as np
# import time
# import os
# import shutil
# import Cards
# from picamera2 import Picamera2, Preview

# # Save image function
# SAVE_FOLDER = 'captured_images'
# if os.path.exists(SAVE_FOLDER):
#     shutil.rmtree(SAVE_FOLDER)
# os.makedirs(SAVE_FOLDER)

# def save_image(image, index):
#     filename = f"{SAVE_FOLDER}/image_{index}.jpg"
#     cv2.imwrite(filename, image)

# # Initialize constants and variables
# IM_WIDTH = 1280
# IM_HEIGHT = 720
# FRAME_RATE = 10

# frame_rate_calc = 1
# freq = cv2.getTickFrequency()
# font = cv2.FONT_HERSHEY_SIMPLEX

# # Initialize camera with Picamera2
# picam2 = Picamera2()
# preview_config = picam2.create_preview_configuration({"size": (IM_WIDTH, IM_HEIGHT)})
# picam2.configure(preview_config)
# picam2.start_preview(Preview.DRM, x=200, y=500)
# picam2.start()
# time.sleep(1)

# # Load the train rank and suit images
# path = os.path.dirname(os.path.abspath(__file__))
# train_ranks = Cards.load_ranks(path + '/Card_Imgs/')
# train_suits = Cards.load_suits(path + '/Card_Imgs/')

# # Main loop
# cam_quit = 0

# # Track distinct cards
# detected_cards = set()

# try:
#     while cam_quit == 0:
#         image = picam2.capture_array()
#         t1 = cv2.getTickCount()

#         pre_proc = Cards.preprocess_image(image)
#         cnts_sort, cnt_is_card = Cards.find_cards(pre_proc)
#         cards = []

#         if len(cnts_sort) != 0:
#             for i in range(len(cnts_sort)):
#                 if cnt_is_card[i] == 1:
#                     cards.append(Cards.preprocess_card(cnts_sort[i], image))
#                     cards[-1].best_rank_match, cards[-1].best_suit_match, \
#                     cards[-1].rank_diff, cards[-1].suit_diff = Cards.match_card(
#                         cards[-1], train_ranks, train_suits
#                     )

#                     image = Cards.draw_results(image, cards[-1])

#                     # Track distinct cards
#                     card_name = f"{cards[-1].best_rank_match} of {cards[-1].best_suit_match}"
#                     detected_cards.add(card_name)

#         if cards:
#             print(f"Detected {len(cards)} cards.")
#             for card in cards:
#                 print(f"Detected card: {card.best_rank_match} of {card.best_suit_match}")
#         else:
#             print("No cards detected.")

#         picam2.set_overlay(image)
#         t2 = cv2.getTickCount()
#         frame_rate_calc = 1 / ((t2 - t1) / freq)

#         for idx, card in enumerate(cards):
#             save_image(card.warp, idx)

#         time.sleep(0.2)

# except KeyboardInterrupt:
#     print("\n[INFO] Program terminated by user.")
#     if detected_cards:
#         print("\nDetected cards during the session:")
#         for card in detected_cards:
#             print(f"- {card}")
#     else:
#         print("No cards were detected during the session.")

# # Cleanup
# picam2.stop_preview()
# picam2.stop()

import cv2
import numpy as np
import time
import os
import shutil
import Cards
from picamera2 import Picamera2, Preview

# Save image function
SAVE_FOLDER = 'captured_images'
if os.path.exists(SAVE_FOLDER):
    shutil.rmtree(SAVE_FOLDER)
os.makedirs(SAVE_FOLDER)

def save_image(image, index):
    filename = f"{SAVE_FOLDER}/image_{index}.jpg"
    cv2.imwrite(filename, image)

# Initialize constants and variables
IM_WIDTH = 1280
IM_HEIGHT = 720
FRAME_RATE = 10

frame_rate_calc = 1
freq = cv2.getTickFrequency()
font = cv2.FONT_HERSHEY_SIMPLEX

# Initialize camera with Picamera2
picam2 = Picamera2()
preview_config = picam2.create_preview_configuration({"size": (IM_WIDTH, IM_HEIGHT)})
picam2.configure(preview_config)
picam2.start_preview(Preview.DRM, x=200, y=500)
picam2.start()
time.sleep(1)

# Load the train rank and suit images
path = os.path.dirname(os.path.abspath(__file__))
train_ranks = Cards.load_ranks(path + '/Card_Imgs/')
train_suits = Cards.load_suits(path + '/Card_Imgs/')

detected_cards = set()  # Persistent set to store distinct cards

def format_card(card):
    return f"{card.best_rank_match} of {card.best_suit_match}"

# Main loop
cam_quit = 0

try:
    while cam_quit == 0:
        image = picam2.capture_array()

        # Start timer for FPS calculation
        t1 = cv2.getTickCount()

        # Pre-process camera image (gray, blur, and threshold it)
        pre_proc = Cards.preprocess_image(image)

        # Find and sort contours
        cnts_sort, cnt_is_card = Cards.find_cards(pre_proc)
        cards = []
        k = 0

        if len(cnts_sort) != 0:
            for i in range(len(cnts_sort)):
                if cnt_is_card[i] == 1:
                    cards.append(Cards.preprocess_card(cnts_sort[i], image))
                    cards[k].best_rank_match, cards[k].best_suit_match, \
                    cards[k].rank_diff, cards[k].suit_diff = Cards.match_card(
                        cards[k], train_ranks, train_suits
                    )

                    image = Cards.draw_results(image, cards[k])
                    k += 1

            if len(cards) != 0:
                temp_cnts = [card.contour for card in cards]
                cv2.drawContours(image, temp_cnts, -1, (255, 0, 0), 2)

        # Track detected cards persistently
        for card in cards:
            detected_cards.add(format_card(card))

        # Draw framerate
        cv2.putText(image, "FPS: " + str(int(frame_rate_calc)), (10, 26),
                    font, 0.7, (255, 0, 255), 2, cv2.LINE_AA)

        # Display the updated image on the DRM preview
        picam2.set_overlay(image)

        # Calculate framerate
        t2 = cv2.getTickCount()
        time1 = (t2 - t1) / freq
        frame_rate_calc = 1 / time1

        # Save each detected card (use card.warp instead of card.image)
        for idx, card in enumerate(cards):
            save_image(card.warp, idx)

        # Status messages
        if cards:
            print(f"Detected {len(cards)} cards.")
            for card in cards:
                print(f"Detected card: {format_card(card)}")
        else:
            print("No cards detected.")

        time.sleep(0.2)

except KeyboardInterrupt:
    print("\n[INFO] Program terminated by user.")
    print("\nDetected cards during the session:")
    for card in sorted(detected_cards):
        print(f"- {card}")

# Cleanup
picam2.stop_preview()
picam2.stop()

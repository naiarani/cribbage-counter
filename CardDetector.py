# CardDetector.py  – Full pegging with corrected Go & auto-pass logic
# -------------------------------------------------------------------------------
import cv2
import numpy as np
import time
import os
import shutil
import uuid
import sys

import Cards
from picamera2 import Picamera2, Preview
from CribbageScorer import CribbageScorer

import RPi.GPIO as GPIO
import serial


# LED
# import board
# import neopixel

GPIO.setmode(GPIO.BCM)
PIN = 18    # the gate of your MOSFET
GPIO.setup(PIN, GPIO.OUT)
GPIO.output(PIN, GPIO.HIGH)  # LED ring on
# p = GPIO.PWM(PIN, 1000)
# p.start(100)   # start at 0% duty (off)


# PIXEL_PIN = board.D18    # BCM18
# NUM_PIXELS = 16          # however many LEDs in your ring
# pixels = neopixel.NeoPixel(
#     PIXEL_PIN, NUM_PIXELS,
#     brightness=0.5, auto_write=True
# )
# # turn them all white:
# pixels.fill((255,255,255))


# ---------- Go-Button Setup ----------
GO_BUTTON_PIN = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(GO_BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# ---------- Optional Serial Setup (Arduino) ----------
try:
    ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
    print("✅ Arduino serial port opened on /dev/ttyACM0")
except (serial.SerialException, FileNotFoundError):
    ser = None
    print("⚠️ No Arduino on /dev/ttyACM0 — running without serial output.")

# ---------- Setup: Image Saving ----------
SAVE_FOLDER = 'captured_images'
if os.path.exists(SAVE_FOLDER):
    shutil.rmtree(SAVE_FOLDER)
os.makedirs(SAVE_FOLDER)
def save_image(image, index):
    cv2.imwrite(f"{SAVE_FOLDER}/image_{uuid.uuid4().hex}.jpg", image)

# ---------- Setup: Camera ----------
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration({"size": (1280,720)}))
picam2.start_preview(Preview.DRM, x=1000, y=200)
picam2.start()
time.sleep(1)

# ---------- Constants & State ----------
initial             = picam2.capture_array()
IM_HEIGHT, IM_WIDTH = initial.shape[:2]
freq                = cv2.getTickFrequency()
font                = cv2.FONT_HERSHEY_SIMPLEX
PEG_CARDS           = 4
GAME_END            = 61
SILENCE_CUT         = 10.0
NO_CARD_WAIT   = 10.0      # seconds with no cards before next round
no_card_since  = None

# ---------- Load Training Images ----------
path        = os.path.dirname(os.path.abspath(__file__))
train_ranks = Cards.load_ranks(path + '/Card_Imgs/')
train_suits = Cards.load_suits(path + '/Card_Imgs/')

# ---------- Initialize Scorer & Regions ----------
scorer = CribbageScorer()
left_third  = IM_WIDTH // 3
mid_third   = 2 * IM_WIDTH // 3
scorer.regions = {
    'Player 2': (0, 0, left_third, IM_HEIGHT),
    'Player 1': (left_third, 0, mid_third, IM_HEIGHT),
    'Crib':      (mid_third, 0, IM_WIDTH, IM_HEIGHT)
}
region_map = {'Player 1': 'player1', 'Player 2': 'player2'}

# ---------- Game Variables ----------
state            = 'cut'
last_state       = None
play_count       = 0
crib_count       = 0
player_hands     = {'Player 1': [], 'Player 2': []}
crib_cards       = []
used_names       = set()
cut_card         = None
first_player     = None
crib_owner       = None
cut_ready        = time.time() + SILENCE_CUT
last_card_player = None

# ── Go-button logic ─────────────────────────────────────────
go_pending      = False
last_go_player  = None
last_go_time    = 0.0
GO_DEBOUNCE     = 1.0  # seconds

# Track number of cards each has played this deal
played_count = {'Player 1': 0, 'Player 2': 0}
auto_passed = {'Player 1': False, 'Player 2': False}


# ---------- Helpers ----------
def prompt_stage():
    global last_state
    if state != last_state:
        if state == 'cut':
            print("🟥 Round start: Clear table → wait 10s → place cut card in crib.")
        elif state == 'play':
            print(f"🎴 Pegging ({PEG_CARDS} each). {first_player} leads.")
        else:
            owner = crib_owner or scorer.crib_owner
            print(f"🗄️ Crib phase: {owner}, place 4 cards.")
        last_state = state

def get_section(x):
    if x < left_third:
        return 'player2'
    elif x < mid_third:
        return 'player1'
    else:
        return 'crib'

# ---------- Main Loop ----------
try:
    while True:
        prompt_stage()

        # ── AUTO-PASS WHEN OUT OF CARDS ─────────────────────
        # if state == 'play' and scorer.turn is not None:
        #     turn = scorer.turn
        #     if played_count.get(turn, 0) >= PEG_CARDS:
        #         # that player is out of cards → just skip their turn
        #         scorer.turn = 'Player 2' if turn == 'Player 1' else 'Player 1'
        #         go_pending = False
        #         last_go_player = None
        #         continue

        

        # ── GO BUTTON HANDLER ─────────────────────────────────────────
        # if state=='play' and scorer.turn is None:
        #     continue
        if state == 'play' and GPIO.input(GO_BUTTON_PIN) == GPIO.LOW:
            now = time.time()
            if now - last_go_time >= GO_DEBOUNCE:
                last_go_time = now
                current = scorer.turn
                other   = 'Player 2' if current == 'Player 1' else 'Player 1'

                if not go_pending:
                    # first Go in this sequence
                    go_pending      = True
                    last_go_player  = current
                    scorer.turn     = other
                    print(f"🆗 {current} says Go → {other} to play")

                elif current != last_go_player:
                    # second Go → reset the count, award last‐card bonus,
                    # and lead goes back to first Go‐sayer
                    print("🔁 Both players said Go! Resetting count…")
                    if last_card_player:
                        scorer.scores[last_card_player] += 1
                        pid = '1' if last_card_player=='Player 1' else '2'
                        print(f"🏁 Last card: Player {pid} +1 (total {scorer.scores[last_card_player]})")
                        if ser:
                            ser.write(f"{pid},{scorer.scores[last_card_player]}\n".encode())

                    scorer.current_total    = 0
                    scorer.pegging_stack.clear()
                    go_pending              = False
                    scorer.turn             = last_go_player    # **lead = first Go‐sayer**
                    print(f"🔄 {scorer.turn} leads next.")
                    last_go_player          = None

            time.sleep(0.2)
            continue
        # # ── GO BUTTON HANDLER ─────────────────────────────
        # if state == 'play' and GPIO.input(GO_BUTTON_PIN) == GPIO.LOW:
        #     now = time.time()
        #     if now - last_go_time >= GO_DEBOUNCE:
        #         last_go_time = now
        #         current = scorer.turn
        #         other   = 'Player 2' if current=='Player 1' else 'Player 1'

        #         if not go_pending:
        #             go_pending     = True
        #             last_go_player = current
        #             print(f"🆗 {current} says Go → {other} to play")
        #             scorer.turn = other
        #         else:
        #             if current != last_go_player:
        #                 print("🔁 Both players said Go! Resetting count…")
        #                 # award last-card peg
        #                 if last_card_player:
        #                     scorer.scores[last_card_player] += 1
        #                     pid = '1' if last_card_player=='Player 1' else '2'
        #                     print(f"🏁 Last card: Player {pid} +1 (total {scorer.scores[last_card_player]})")
        #                     if ser:
        #                         ser.write(f"{pid},{scorer.scores[last_card_player]}\n".encode())
        #                 scorer.current_total = 0
        #                 scorer.pegging_stack.clear()
        #                 go_pending = False
        #                 last_go_player = None
        #                 scorer.turn = last_card_player
        #                 print(f"🔄 {last_card_player} leads next.")
        #         time.sleep(0.2)
        #     continue

        # ── CAPTURE & DETECT CARDS ─────────────────────────
        img = picam2.capture_array()
        t0  = cv2.getTickCount()
        pre, cnts, flags = Cards.preprocess_image(img), *Cards.find_cards(Cards.preprocess_image(img))
        detections = []
        if cnts:
            for i,c in enumerate(cnts):
                if flags[i]!=1: continue
                card,warp = Cards.preprocess_card(c,img)
                card.warp = warp
                (card.best_rank_match, card.best_suit_match,
                 card.rank_diff, card.suit_diff) = Cards.match_card(card, train_ranks, train_suits)
                detections.append(card)
        # if len(detections) == 0:
        #     if no_card_since is None:
        #         no_card_since = time.time()
        # else:
        #     no_card_since = None


        # ── PROCESS EACH DETECTION ──────────────────────────
        for card in detections:
            name = f"{card.best_rank_match} of {card.best_suit_match}"
            if 'Unknown' in (card.best_rank_match, card.best_suit_match): continue
            if name in used_names: continue
            if not hasattr(card,'corner_pts') or card.corner_pts is None: continue

            # centroid → section
            if hasattr(card,'center') and card.center is not None:
                cx,cy = map(int,card.center)
            else:
                cx = int(np.mean(card.corner_pts[:,0]))
                cy = int(np.mean(card.corner_pts[:,1]))
            sec = get_section(cx)

            # ── CUT stage ───────────────────────────────────
            # replace your existing CUT block with something like:

            # if state == 'cut':
            #     # enforce both the original cut‐silence _and_ a clear‐table pause
            #     if time.time() < cut_ready:
            #         continue
            #     if no_card_since is None or (time.time() - no_card_since) < NO_CARD_WAIT:
            #         # still waiting on table to clear
            #         continue

            #     if sec == 'crib':
            #         used_names.add(name)
            #         cut_card = name
            #         scorer.set_first_card_in_crib(name)
            #         print(f"🟥 Cut card: {name}")
            #         state = 'play'
            #     continue
            if state=='cut':
                if time.time() < cut_ready: continue
                if sec=='crib':
                    used_names.add(name)
                    cut_card = name
                    scorer.set_first_card_in_crib(name)
                    print(f"🟥 Cut card: {name}")
                    state = 'play'
                continue
            # ── PLAY STAGE ────────────────────────────────────────────────
            if state == 'play':
                # (1) Lead & crib-owner on first play
                if play_count == 0 and sec in ('player1','player2'):
                    first = 'Player 1' if sec=='player1' else 'Player 2'
                    other = 'Player 2' if first=='Player 1' else 'Player 1'
                    scorer.set_first_player(first, other)
                    first_player = first

                # (2) Auto-pass *once* when a player has no cards left
                current  = scorer.turn
                opponent = 'Player 2' if current=='Player 1' else 'Player 1'
                # only award when they *just* ran out, and the opponent still has cards:
                if (played_count[current] >= PEG_CARDS 
                and played_count[opponent] < PEG_CARDS 
                and not auto_passed[current]):
                    auto_passed[current] = True
                    scorer.scores[opponent] += 1
                    pid = '1' if opponent=='Player 1' else '2'
                    print(f"➕ Auto‐Go: {opponent} +1 (total {scorer.scores[opponent]})")
                    if ser:
                        ser.write(f"{pid},{scorer.scores[opponent]}\n".encode())
                    # hand over the turn to the opponent
                    scorer.turn = opponent

                # 3) Only allow the correct player
                expected = scorer.turn
                sec_p    = 'Player 1' if sec=='player1' else ('Player 2' if sec=='player2' else None)
                if sec_p != expected:
                    continue

                # 4) Guard >31
                val = scorer.card_value(name)
                if scorer.current_total + val > 31:
                    print(f"⚠️ Invalid play: {name} would bring count to "
                        f"{scorer.current_total + val} (>31). Play smaller card or press Go.")
                    continue

                # 5) Accept the card
                used_names.add(name)
                player_hands[sec_p].append(name)
                played_count[sec_p] += 1

                # 6) Score pegging
                scorer.score_pegging(sec_p, name)
                evt = scorer.score_history[-1]
                pid   = '1' if sec_p=='Player 1' else '2'
                print(f"🔔 Player {pid}: +{evt['delta']} pts, total {evt['total']}")
                if ser:
                    ser.write(f"{pid},{evt['total']}\n".encode())

                # 7) Show running count
                print(f"🧮 Count: {scorer.current_total}")

                # 8) If exactly 31, reset immediately
                if scorer.current_total == 31:
                    print("🔄 Hit 31! Resetting count to 0.")
                    scorer.current_total    = 0
                    scorer.pegging_stack.clear()
                    # turn has already been switched inside score_pegging()

                # 9) Handle any pending Go
                if go_pending and last_go_player != sec_p:
                    if scorer.current_total != 31:
                        scorer.scores[sec_p] += 1
                        print(f"➕ Player {pid}: +1 for Go (total {scorer.scores[sec_p]})")
                        if ser:
                            ser.write(f"{pid},{scorer.scores[sec_p]}\n".encode())

                    scorer.current_total = 0
                    scorer.pegging_stack.clear()
                    scorer.turn = last_go_player      # first Go‐sayer leads next
                    print(f"🔄 Count reset after Go → {scorer.turn} leads next.")
                    go_pending      = False
                    last_go_player  = None

                # 10) Now increment the play count
                play_count += 1
                last_card_player = sec_p

                # 11) End pegging on the 8th card
                if play_count >= 2 * PEG_CARDS:
                    scorer.scores[last_card_player] += 1
                    lp = '1' if last_card_player=='Player 1' else '2'
                    print(f"🏁 Last card: Player {lp} +1 (total {scorer.scores[last_card_player]})")
                    if ser:
                        ser.write(f"{lp},{scorer.scores[last_card_player]}\n".encode())
                    print(f"🛑 Pegging complete. Scores: {scorer.get_scores()}")
                    crib_owner = scorer.crib_owner
                    state      = 'crib'
                else:
                    print(f"➡️ {sec_p} played {name}. Next: {scorer.turn}")

                continue

            # # ── PLAY stage ─────────────────────────────────────────
            # if state == 'play':
            #     # 1) First play: decide who leads and who owns the crib
            #     if play_count == 0 and sec in ('player1','player2'):
            #         first = 'Player 1' if sec=='player1' else 'Player 2'
            #         other = 'Player 2' if first=='Player 1' else 'Player 1'
            #         scorer.set_first_player(first, other)
            #         first_player = first

            #     # 2) Auto‐pass if one player has no cards left to play
            #     current = scorer.turn
            #     if current:
            #         opponent = 'Player 2' if current=='Player 1' else 'Player 1'
            #         if played_count[current] >= PEG_CARDS and played_count[opponent] < PEG_CARDS:
            #             # opponent gets 1 for forced Go
            #             scorer.scores[opponent] += 1
            #             pid = '1' if opponent=='Player 1' else '2'
            #             print(f"➕ Auto‐Go: {opponent} +1 (total {scorer.scores[opponent]})")
            #             if ser:
            #                 ser.write(f"{pid},{scorer.scores[opponent]}\n".encode())
            #             # switch turn
            #             scorer.turn = opponent
            #             continue

            #     # 3) Only allow the current‐turn player to play
            #     expected = scorer.turn
            #     sec_p    = 'Player 1' if sec=='player1' else ('Player 2' if sec=='player2' else None)
            #     if sec_p != expected:
            #         continue

            #     # 4) Guard against over‐31
            #     val = scorer.card_value(name)
            #     if scorer.current_total + val > 31:
            #         print(f"⚠️ Invalid play: {name} would bring count to "
            #             f"{scorer.current_total + val} (>31). Play smaller card or press Go.")
            #         continue

            #     # 5) Accept the card
            #     used_names.add(name)
            #     player_hands[sec_p].append(name)
            #     played_count[sec_p] += 1

            #     # 6) Score pegging
            #     scorer.score_pegging(sec_p, name)
            #     evt = scorer.score_history[-1]
            #     pid   = '1' if sec_p=='Player 1' else '2'
            #     print(f"🔔 Player {pid}: +{evt['delta']} pts, total {evt['total']}")
            #     if ser:
            #         ser.write(f"{pid},{evt['total']}\n".encode())

            #     # 7) Show running count
            #     print(f"🧮 Count: {scorer.current_total}")

            #     # 8) If exactly 31, reset immediately
            #     if scorer.current_total == 31:
            #         print("🔄 Hit 31! Resetting count to 0.")
            #         scorer.current_total   = 0
            #         scorer.pegging_stack.clear()
            #         # turn already flipped inside score_pegging()

            #     # 9) Handle any pending Go
            #     if go_pending:
            #         if scorer.current_total != 31:
            #             scorer.scores[sec_p] += 1
            #             print(f"➕ Player {pid}: +1 for Go (total {scorer.scores[sec_p]})")
            #             if ser:
            #                 ser.write(f"{pid},{scorer.scores[sec_p]}\n".encode())
            #         scorer.current_total = 0
            #         scorer.pegging_stack.clear()
            #         go_pending           = False
            #         last_go_player       = None
            #         print("🔄 Count reset after Go")

            #     # play_count += 1
            #     last_card_player = sec_p

            #     # 10) **End pegging** exactly on the 8th card played
            #     if play_count >= 2 * PEG_CARDS:
            #         # award last‐card
            #         scorer.scores[last_card_player] += 1
            #         lp = '1' if last_card_player=='Player 1' else '2'
            #         print(f"🏁 Last card: Player {lp} +1 (total {scorer.scores[last_card_player]})")
            #         if ser:
            #             ser.write(f"{lp},{scorer.scores[last_card_player]}\n".encode())

            #         print(f"🛑 Pegging complete. Scores: {scorer.get_scores()}")
            #         crib_owner = scorer.crib_owner
            #         state      = 'crib'
            #     else:
            #         print(f"➡️ {sec_p} played {name}. Next: {scorer.turn}")
            #     continue



            # ── CRIB stage ────────────────────────────────────
            target = region_map.get(crib_owner)
            if state=='crib' and sec in ('crib',target):
                used_names.add(name)
                crib_cards.append(name)
                crib_count += 1
                print(f"🗄️ Crib card {name} ({crib_count}/4)")
                if crib_count==4:
                    scorer.score_round(player_hands['Player 1'], player_hands['Player 2'], crib_cards, cut_card)
                    for evt in scorer.score_history[-3:]:
                        pid = '1' if evt['player']=='Player 1' else '2'
                        print(f"🔔 Player {pid}: +{evt['delta']} pts, total {evt['total']}")
                        if ser:
                            ser.write(f"{pid},{evt['total']}\n".encode())
                    for p,s in scorer.get_scores().items():
                        if s>=GAME_END:
                            print(f"🥳 Game over! {p} wins with {s}.")
                            sys.exit(0)
                    print("🔄 Next round; crib passes.")
                    # reset
                    state        = 'cut'
                    last_state   = None
                    play_count   = crib_count = 0
                    player_hands = {'Player 1':[], 'Player 2':[]}
                    crib_cards   = []
                    used_names.clear()
                    cut_card     = None
                    first_player, crib_owner = crib_owner, first_player
                    scorer.cut_card         = None
                    scorer.pegging_stack.clear()
                    scorer.current_total    = 0
                    auto_passed = {'Player 1': False, 'Player 2': False}
                    cut_ready    = time.time() + SILENCE_CUT
                continue

        # ── Draw & FPS ─────────────────────────────────────
        for card in detections:
            if hasattr(card,'contour'):
                cv2.drawContours(img,[card.contour],-1,(255,0,0),2)
            if hasattr(card,'center') and card.center is not None:
                x,y=map(int,card.center)
                cv2.circle(img,(x,y),5,(0,255,255),-1)
        cv2.line(img,(left_third,0),(left_third,IM_HEIGHT),(0,255,0),2)
        cv2.line(img,(mid_third,0),(mid_third,IM_HEIGHT),(255,0,0),2)
        fps = 1/((cv2.getTickCount()-t0)/freq)
        cv2.putText(img, f'FPS:{int(fps)}',(20,40),font,1,(255,255,0),2)
        try:
            picam2.set_overlay(img)
        except:
            pass

        time.sleep(0.2)

except KeyboardInterrupt:
    print("\n[INFO] Terminated by user.")
finally:
    picam2.stop_preview()
    picam2.stop()
    cv2.destroyAllWindows()
    # pixels.fill((0,0,0))
    # p.stop()
    GPIO.output(PIN, GPIO.LOW)   # LED ring off
    GPIO.cleanup()



# import cv2
# import numpy as np
# import time
# import os
# import shutil
# import uuid
# import sys

# import Cards
# from picamera2 import Picamera2, Preview
# from CribbageScorer import CribbageScorer

# import RPi.GPIO as GPIO
# import serial

# # ---------- Go-Button Setup ----------
# GO_BUTTON_PIN = 17
# GPIO.setmode(GPIO.BCM)
# GPIO.setup(GO_BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# # ---------- Optional Serial Setup (Arduino) ----------
# try:
#     ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
#     print("✅ Arduino serial port opened on /dev/ttyACM0")
# except (serial.SerialException, FileNotFoundError):
#     ser = None
#     print("⚠️ No Arduino on /dev/ttyACM0 — running without serial output.")

# # ---------- Setup: Image Saving ----------
# SAVE_FOLDER = 'captured_images'
# if os.path.exists(SAVE_FOLDER):
#     shutil.rmtree(SAVE_FOLDER)
# os.makedirs(SAVE_FOLDER)
# def save_image(image, index):
#     cv2.imwrite(f"{SAVE_FOLDER}/image_{uuid.uuid4().hex}.jpg", image)

# # ---------- Setup: Camera ----------
# picam2 = Picamera2()
# picam2.configure(picam2.create_preview_configuration({"size": (1280,720)}))
# picam2.start_preview(Preview.DRM, x=200, y=500)
# picam2.start()
# time.sleep(1)

# # ---------- Constants & State ----------
# initial             = picam2.capture_array()
# IM_HEIGHT, IM_WIDTH = initial.shape[:2]
# freq                = cv2.getTickFrequency()
# font                = cv2.FONT_HERSHEY_SIMPLEX
# PEG_CARDS           = 4
# GAME_END            = 51
# SILENCE_CUT         = 3.0

# # ---------- Load Training Images ----------
# path        = os.path.dirname(os.path.abspath(__file__))
# train_ranks = Cards.load_ranks(path + '/Card_Imgs/')
# train_suits = Cards.load_suits(path + '/Card_Imgs/')

# # ---------- Initialize Scorer & Regions ----------
# scorer = CribbageScorer()
# left_third  = IM_WIDTH // 3
# mid_third   = 2 * IM_WIDTH // 3
# # 'Player 2' on left, 'Player 1' in middle, 'Crib' on right
# scorer.regions = {
#     'Player 2': (0, 0, left_third, IM_HEIGHT),
#     'Player 1': (left_third, 0, mid_third, IM_HEIGHT),
#     'Crib':      (mid_third, 0, IM_WIDTH, IM_HEIGHT)
# }
# region_map = {'Player 1': 'player1', 'Player 2': 'player2'}

# # ---------- Game Variables ----------
# state             = 'cut'
# last_state        = None
# play_count        = 0
# crib_count        = 0
# player_hands      = {'Player 1': [], 'Player 2': []}
# crib_cards        = []
# used_names        = set()
# cut_card          = None
# first_player      = None
# crib_owner        = None
# cut_ready         = time.time() + SILENCE_CUT
# last_card_player  = None

# # ── Go-button logic ─────────────────────────────────────────
# go_pending      = False
# last_go_player  = None
# last_go_time    = 0.0
# GO_DEBOUNCE     = 1.0  # seconds

# # ---------- Helpers ----------
# def prompt_stage():
#     global last_state
#     if state != last_state:
#         if state == 'cut':
#             print("🟥 Round start: Clear table → wait 3s → place cut card in crib.")
#         elif state == 'play':
#             print(f"🎴 Pegging ({PEG_CARDS} each). {first_player} leads.")
#         else:  # crib
#             owner = crib_owner or scorer.crib_owner
#             print(f"🗄️ Crib phase: {owner}, place 4 cards.")
#         last_state = state

# def get_section(x):
#     if x < left_third:
#         return 'player2'
#     elif x < mid_third:
#         return 'player1'
#     else:
#         return 'crib'

# # ---------- Main Loop ----------
# try:
#     while True:
#         prompt_stage()

#         # ── GO BUTTON HANDLER ─────────────────────────────────
#         if state == 'play' and GPIO.input(GO_BUTTON_PIN) == GPIO.LOW:
#             now = time.time()
#             if now - last_go_time >= GO_DEBOUNCE:
#                 last_go_time = now
#                 current = scorer.turn or first_player
#                 other   = 'Player 2' if current == 'Player 1' else 'Player 1'

#                 if not go_pending:
#                     go_pending     = True
#                     last_go_player = current
#                     scorer.turn    = other
#                     print(f"🆗 {current} says Go → {other} to play")
#                 else:
#                     if current != last_go_player:
#                         print("🔁 Both players said Go! Resetting count…")
#                         if last_card_player:
#                             scorer.scores[last_card_player] += 1
#                             pid = '1' if last_card_player=='Player 1' else '2'
#                             print(f"🏁 Last card: Player {pid} +1 (total {scorer.scores[last_card_player]})")
#                             if ser:
#                                 ser.write(f"{pid},{scorer.scores[last_card_player]}\n".encode())
#                         scorer.current_total   = 0
#                         scorer.pegging_stack.clear()
#                         go_pending             = False
#                         last_go_player         = None
#                         scorer.turn            = other
#                         print(f"🔄 {other} leads next.")
#                 time.sleep(0.5)
#             continue

#         # ── Capture frame & detect cards ─────────────────────
#         img = picam2.capture_array()
#         t0  = cv2.getTickCount()

#         pre, cnts, flags = Cards.preprocess_image(img), *Cards.find_cards(Cards.preprocess_image(img))
#         detections = []
#         if cnts:
#             for i, c in enumerate(cnts):
#                 if flags[i] != 1: continue
#                 card, warp = Cards.preprocess_card(c, img)
#                 card.warp = warp
#                 (card.best_rank_match, card.best_suit_match,
#                  card.rank_diff, card.suit_diff) = Cards.match_card(card, train_ranks, train_suits)
#                 detections.append(card)

#         # ── Process each detection ────────────────────────────
#         for card in detections:
#             name = f"{card.best_rank_match} of {card.best_suit_match}"
#             if 'Unknown' in (card.best_rank_match, card.best_suit_match): continue
#             if name in used_names: continue
#             if not hasattr(card, 'corner_pts') or card.corner_pts is None: continue

#             # centroid → section
#             if hasattr(card, 'center') and card.center is not None:
#                 cx, cy = map(int, card.center)
#             else:
#                 cx = int(np.mean(card.corner_pts[:,0]))
#                 cy = int(np.mean(card.corner_pts[:,1]))
#             sec = get_section(cx)

#             # ── CUT stage ─────────────────────────────────────
#             if state == 'cut':
#                 if time.time() < cut_ready: continue
#                 if sec == 'crib':
#                     used_names.add(name)
#                     cut_card = name
#                     scorer.set_first_card_in_crib(name)
#                     print(f"🟥 Cut card: {name}")
#                     state = 'play'
#                 continue

#             # ── PLAY stage ───────────────────────────────────
#             if state == 'play':
#                 # 1) determine lead & crib owner on first play
#                 if play_count == 0 and sec in ('player1','player2'):
#                     first  = 'Player 1' if sec=='player1' else 'Player 2'
#                     other  = 'Player 2' if first=='Player 1' else 'Player 1'
#                     scorer.set_first_player(first, other)

#                 expected = scorer.turn
#                 sec_p    = 'Player 1' if sec=='player1' else ('Player 2' if sec=='player2' else None)
#                 if sec_p == expected:
#                     # over-31 guard
#                     val = scorer.card_value(name)
#                     if scorer.current_total + val > 31:
#                         print(f"⚠️ Invalid play: {name} would bring count to "
#                               f"{scorer.current_total + val} (>31). Play smaller card or press Go.")
#                         continue

#                     used_names.add(name)
#                     player_hands[sec_p].append(name)

#                     # score pegging
#                     scorer.score_pegging(sec_p, name)
#                     evt = scorer.score_history[-1]
#                     pid   = '1' if evt['player']=='Player 1' else '2'
#                     delta = evt['delta']
#                     total = evt['total']
#                     last_card_player = sec_p

#                     print(f"🔔 Player {pid}: +{delta} pts, {total} total")
#                     if ser:
#                         ser.write(f"{pid},{total}\n".encode())

#                     # show running count before any resets
#                     print(f"🧮 Count: {scorer.current_total}")

#                     # *** NEW: if exactly 31, reset count & stack immediately ***
#                     if scorer.current_total == 31:
#                         print("🔄 Hit 31! Resetting count to 0.")
#                         scorer.current_total = 0
#                         scorer.pegging_stack.clear()
#                         # last_card_player leads next automatically
#                         # leave scorer.turn as-is (it’s already switched by score_pegging)

#                     # handle any pending Go (unchanged)
#                     if go_pending:
#                         if scorer.current_total != 31:
#                             scorer.scores[sec_p] += 1
#                             print(f"➕ Player {pid}: +1 for Go (total {scorer.scores[sec_p]})")
#                             if ser:
#                                 ser.write(f"{pid},{scorer.scores[sec_p]}\n".encode())
#                         scorer.current_total   = 0
#                         scorer.pegging_stack.clear()
#                         go_pending             = False
#                         last_go_player         = None
#                         print("🔄 Count reset after Go")

#                     play_count += 1

#                     # end-of-hand (unchanged) …
#                     if play_count >= 2 * PEG_CARDS:
#                         scorer.scores[last_card_player] += 1
#                         pid = '1' if last_card_player=='Player 1' else '2'
#                         print(f"🏁 Last card: Player {pid} +1 (total {scorer.scores[last_card_player]})")
#                         if ser:
#                             ser.write(f"{pid},{scorer.scores[last_card_player]}\n".encode())
#                         print(f"🛑 Pegging complete. Scores: {scorer.get_scores()}")
#                         crib_owner = scorer.crib_owner
#                         state = 'crib'
#                     else:
#                         print(f"➡️ {sec_p} played {name}. Next: {scorer.turn}")
#                 continue

#             # ── CRIB stage ────────────────────────────────────
#             target = region_map.get(crib_owner)
#             if state == 'crib' and sec in ('crib', target):
#                 used_names.add(name)
#                 crib_cards.append(name)
#                 crib_count += 1
#                 print(f"🗄️ Crib card {name} ({crib_count}/4)")
#                 if crib_count == 4:
#                     scorer.score_round(player_hands['Player 1'],
#                                        player_hands['Player 2'],
#                                        crib_cards,
#                                        cut_card)
#                     for evt in scorer.score_history[-3:]:
#                         pid = '1' if evt['player']=='Player 1' else '2'
#                         print(f"🔔 Player {pid}: +{evt['delta']} pts, {evt['total']} total")
#                         if ser:
#                             ser.write(f"{pid},{evt['total']}\n".encode())
#                     for p,s in scorer.get_scores().items():
#                         if s >= GAME_END:
#                             print(f"🥳 Game over! {p} wins with {s}.")
#                             sys.exit(0)
#                     print("🔄 Next round; crib passes.")
#                     # reset
#                     state        = 'cut'
#                     last_state   = None
#                     play_count   = crib_count = 0
#                     player_hands = {'Player 1': [], 'Player 2': []}
#                     crib_cards   = []
#                     used_names.clear()
#                     cut_card     = None
#                     first_player, crib_owner = crib_owner, first_player
#                     scorer.cut_card = None
#                     scorer.pegging_stack.clear()
#                     scorer.current_total = 0
#                     cut_ready    = time.time() + SILENCE_CUT
#                 continue

#         # ── Draw & FPS ─────────────────────────────────────────
#         for card in detections:
#             if hasattr(card, 'contour'):
#                 cv2.drawContours(img, [card.contour], -1, (255,0,0), 2)
#             if hasattr(card, 'center') and card.center is not None:
#                 x,y = map(int, card.center)
#                 cv2.circle(img, (x,y), 5, (0,255,255), -1)
#         cv2.line(img, (left_third,0), (left_third, IM_HEIGHT), (0,255,0), 2)
#         cv2.line(img, (mid_third,0), (mid_third, IM_HEIGHT), (255,0,0), 2)
#         fps = 1 / ((cv2.getTickCount() - t0)/freq)
#         cv2.putText(img, f'FPS:{int(fps)}', (20,40), font,1,(255,255,0),2)
#         try:
#             picam2.set_overlay(img)
#         except:
#             pass

#         time.sleep(0.2)

# except KeyboardInterrupt:
#     print("\n[INFO] Terminated by user.")
# finally:
#     GPIO.cleanup()
#     picam2.stop_preview()
#     picam2.stop()
#     cv2.destroyAllWindows()


          
#             ############### CURRENTLY WORKS WIHTOUT THE GO ################
#             if state == 'play':
#                 if play_count == 0 and sec in ('player1', 'player2'):
#                     first_player = 'Player 1' if sec == 'player1' else 'Player 2'
#                     crib_owner   = 'Player 2' if first_player == 'Player 1' else 'Player 1'
#                     scorer.set_first_player(first_player, crib_owner)

#                 expected = first_player if play_count % 2 == 0 else crib_owner
#                 sec_p    = 'Player 1' if sec=='player1' else ('Player 2' if sec=='player2' else None)

#                 if sec_p == expected:
#                     used_names.add(name)
#                     player_hands[sec_p].append(name)

#                     # score pegging
#                     scorer.score_pegging(sec_p, name)
#                     evt   = scorer.score_history[-1]
#                     pid   = '1' if evt['player']=='Player 1' else '2'
#                     delta = evt['delta']
#                     total = evt['total']

#                     # console update
#                     print(f"🔔 Player {pid}: +{delta} points, {total} total")

#                     # serial out
#                     msg = f"{pid},{total}\n"
#                     print(f"→ SERIAL OUT: {msg.strip()}")
#                     if ser:
#                         ser.write(msg.encode())

#                     play_count += 1
#                     if play_count < 2 * PEG_CARDS:
#                         nxt = first_player if play_count % 2 == 0 else crib_owner
#                         print(f"➡️ {sec_p} played {name}. Next: {nxt}.")
#                     else:
#                         print(f"🛑 Pegging complete. Scores: {scorer.get_scores()}")
#                         state = 'crib'
#                 continue

#             ############### CURRENTLY WORKS WIHTOUT THE GO ################

#             # ── CRIB stage ───────────────────────────────────────────
#             target = region_map[crib_owner]
#             if state == 'crib' and sec in ('crib', target):
#                 used_names.add(name)
#                 crib_cards.append(name)
#                 crib_count += 1
#                 print(f"🗄️ Crib card {name} ({crib_count}/4)")

#                 if crib_count == 4:
#                     scorer.score_round(player_hands['Player 1'],
#                                       player_hands['Player 2'],
#                                       crib_cards, cut_card)

#                     # show and send last three events
#                     for evt in scorer.score_history[-3:]:
#                         pid   = '1' if evt['player']=='Player 1' else '2'
#                         delta = evt['delta']
#                         total = evt['total']
#                         print(f"🔔 Player {pid}: +{delta} points, {total} total")
#                         msg = f"{pid},{total}\n"
#                         print(f"→ SERIAL OUT: {msg.strip()}")
#                         if ser:
#                             ser.write(msg.encode())

#                     # check for winner
#                     for p, s in scorer.get_scores().items():
#                         if s >= GAME_END:
#                             print(f"🥳 Game over! {p} wins with {s}.")
#                             sys.exit(0)

#                     # reset for next round
#                     print("🔄 Next round; crib passes.")
#                     state           = 'cut'
#                     last_state      = None
#                     play_count      = crib_count = 0
#                     player_hands    = {'Player 1': [], 'Player 2': []}
#                     crib_cards      = []
#                     used_names.clear()
#                     cut_card        = None
#                     first_player, crib_owner = crib_owner, first_player
#                     scorer.cut_card       = None
#                     scorer.pegging_stack.clear()
#                     scorer.current_total  = 0
#                     cut_ready       = time.time() + SILENCE_CUT
#                 continue

#         # ── Draw & FPS ──────────────────────────────────────────────
#         for card in detections:
#             if hasattr(card, 'contour'):
#                 cv2.drawContours(img, [card.contour], -1, (255,0,0), 2)
#             if hasattr(card, 'center') and card.center is not None:
#                 x, y = map(int, card.center)
#                 cv2.circle(img, (x,y), 5, (0,255,255), -1)
#         cv2.line(img, (p1_x,0), (p1_x, IM_HEIGHT), (0,255,0), 2)
#         cv2.line(img, (p2_x,0), (p2_x, IM_HEIGHT), (255,0,0), 2)
#         fps = 1 / ((cv2.getTickCount() - t0) / freq)
#         cv2.putText(img, f'FPS:{int(fps)}', (20,40), font,1,(255,255,0),2)
#         try:
#             picam2.set_overlay(img)
#         except:
#             pass

#         time.sleep(0.2)

# except KeyboardInterrupt:
#     print("\n[INFO] Terminated by user.")
# finally:
#     GPIO.cleanup()
#     picam2.stop_preview()
#     picam2.stop()
#     cv2.destroyAllWindows()



# # # CardDetector.py  (with conditional Arduino serial output)
# # # -------------------------------------------------------------------------------
# import cv2
# import numpy as np
# import time
# import os
# import shutil
# import uuid
# import sys

# import Cards
# from picamera2 import Picamera2, Preview
# from CribbageScorer import CribbageScorer

# # ---------- Optional Serial Setup (Arduino) ----------
# import serial
# try:
#     ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
#     print("✅ Arduino serial port opened on /dev/ttyACM0 at 9600 baud")
# except (serial.SerialException, FileNotFoundError):
#     ser = None
#     print("⚠️ No Arduino on /dev/ttyACM0 — running without serial output.")

# # ---------- Setup: Image Saving ----------
# SAVE_FOLDER = 'captured_images'
# if os.path.exists(SAVE_FOLDER):
#     shutil.rmtree(SAVE_FOLDER)
# os.makedirs(SAVE_FOLDER)

# def save_image(image, index):
#     cv2.imwrite(f"{SAVE_FOLDER}/image_{uuid.uuid4().hex}.jpg", image)

# # ---------- Setup: Camera ----------
# picam2 = Picamera2()
# picam2.configure(picam2.create_preview_configuration({"size": (1280,720)}))
# picam2.start_preview(Preview.DRM, x=200, y=500)
# picam2.start()
# time.sleep(1)

# # ---------- Constants & State ----------
# initial        = picam2.capture_array()
# IM_HEIGHT, IM_WIDTH = initial.shape[:2]
# freq           = cv2.getTickFrequency()
# font           = cv2.FONT_HERSHEY_SIMPLEX
# PEG_CARDS      = 4
# GAME_END       = 51
# SILENCE_CUT    = 3.0

# # ---------- Load Training Images ----------
# path         = os.path.dirname(os.path.abspath(__file__))
# train_ranks  = Cards.load_ranks(path + '/Card_Imgs/')
# train_suits  = Cards.load_suits(path + '/Card_Imgs/')

# # ---------- Initialize Scorer & Regions ----------
# scorer       = CribbageScorer()
# p1_x         = IM_WIDTH // 3
# p2_x         = 2 * IM_WIDTH // 3
# scorer.regions = {
#     'Player 1': (0, 0, p1_x, IM_HEIGHT),
#     'Player 2': (p1_x, 0, p2_x, IM_HEIGHT),
#     'Crib':      (p2_x, 0, IM_WIDTH, IM_HEIGHT)
# }

# region_map   = {'Player 1': 'player1', 'Player 2': 'player2'}

# # ---------- Game Variables ----------
# state         = 'cut'
# last_state    = None
# play_count    = 0
# crib_count    = 0
# player_hands  = {'Player 1': [], 'Player 2': []}
# crib_cards    = []
# used_names    = set()
# cut_card      = None
# first_player  = None
# crib_owner    = None
# cut_ready     = time.time() + SILENCE_CUT

# # ---------- Helpers ----------
# def prompt_stage():
#     global last_state
#     if state != last_state:
#         if state == 'cut':
#             print("🟥 Round start: Clear table → wait 3s → place cut card in crib.")
#         elif state == 'play':
#             print(f"🎴 Pegging ({PEG_CARDS} each). {first_player} leads.")
#         elif state == 'crib':
#             print(f"🗄️ Crib phase: {crib_owner}, place 4 cards.")
#         last_state = state

# def get_section(x):
#     if x < p1_x:
#         return 'player1'
#     if x < p2_x:
#         return 'player2'
#     return 'crib'

# # ---------- Main Loop ----------
# try:
#     while True:
#         prompt_stage()
#         img = picam2.capture_array()
#         t0  = cv2.getTickCount()

#         # detect cards
#         pre, cnts, flags = Cards.preprocess_image(img), *Cards.find_cards(Cards.preprocess_image(img))
#         detections = []
#         if cnts:
#             for i, c in enumerate(cnts):
#                 if flags[i] != 1:
#                     continue
#                 card, warp = Cards.preprocess_card(c, img)
#                 card.warp  = warp
#                 (card.best_rank_match, card.best_suit_match,
#                  card.rank_diff, card.suit_diff) = Cards.match_card(card, train_ranks, train_suits)
#                 detections.append(card)

#         for card in detections:
#             name = f"{card.best_rank_match} of {card.best_suit_match}"
#             # skip bad or already used
#             if 'Unknown' in (card.best_rank_match, card.best_suit_match):
#                 continue
#             if name in used_names:
#                 continue
#             if not hasattr(card, 'corner_pts') or card.corner_pts is None:
#                 continue

#             # centroid
#             if hasattr(card, 'center') and card.center is not None:
#                 cx, cy = map(int, card.center)
#             else:
#                 cx = int(np.mean(card.corner_pts[:,0]))
#                 cy = int(np.mean(card.corner_pts[:,1]))
#             sec = get_section(cx)

#             # ── CUT stage ────────────────────────────────────────────
#             if state == 'cut':
#                 if time.time() < cut_ready:
#                     continue
#                 if sec == 'crib':
#                     used_names.add(name)
#                     cut_card = name
#                     scorer.set_first_card_in_crib(name)
#                     print(f"🟥 Cut card: {name}")
#                     state = 'play'
#                 continue

#             # ── PLAY stage ───────────────────────────────────────────
#             if state == 'play':
#                 if play_count == 0 and sec in ('player1', 'player2'):
#                     first_player = 'Player 1' if sec == 'player1' else 'Player 2'
#                     crib_owner   = 'Player 2' if first_player == 'Player 1' else 'Player 1'
#                     scorer.set_first_player(first_player, crib_owner)

#                 expected = first_player if play_count % 2 == 0 else crib_owner
#                 sec_p = 'Player 1' if sec == 'player1' else ('Player 2' if sec == 'player2' else None)

#                 if sec_p == expected:
#                     used_names.add(name)
#                     player_hands[sec_p].append(name)
#                     # score pegging
#                     _ = scorer.score_pegging(sec_p, name)
#                     evt = scorer.score_history[-1]
#                     print(f"🎯 Event: {evt}")
#                     msg = f"{evt['player'][0]}{evt['delta']:+d},{evt['total']}\n"
#                     if ser:
#                         ser.write(msg.encode())

#                     play_count += 1
#                     if play_count < 2 * PEG_CARDS:
#                         nxt = first_player if play_count % 2 == 0 else crib_owner
#                         print(f"➡️ {sec_p} played {name}. Next: {nxt}.")
#                     else:
#                         print(f"🛑 Pegging complete. Scores: {scorer.get_scores()}")
#                         state = 'crib'
#                 continue

#             # ── CRIB stage ───────────────────────────────────────────
#             target = region_map[crib_owner]
#             if state == 'crib' and sec in ('crib', target):
#                 used_names.add(name)
#                 crib_cards.append(name)
#                 crib_count += 1
#                 print(f"🗄️ Crib card {name} ({crib_count}/4)")
#                 if crib_count == 4:
#                     scorer.score_round(player_hands['Player 1'],
#                                       player_hands['Player 2'],
#                                       crib_cards, cut_card)
#                     print(f"📊 Round scores: {scorer.get_scores()}")

#                     # send last three events
#                     for evt in scorer.score_history[-3:]:
#                         print(f"🎯 Event: {evt}")
#                         msg = f"{evt['player'][0]}{evt['delta']:+d},{evt['total']}\n"
#                         if ser:
#                             ser.write(msg.encode())

#                     # check for winner
#                     for p, s in scorer.get_scores().items():
#                         if s >= GAME_END:
#                             print(f"🥳 Game over! {p} wins with {s}.")
#                             sys.exit(0)

#                     # reset for next round
#                     print("🔄 Next round; crib passes.")
#                     state        = 'cut'
#                     last_state   = None
#                     play_count   = crib_count = 0
#                     player_hands = {'Player 1': [], 'Player 2': []}
#                     crib_cards   = []
#                     used_names.clear()
#                     cut_card     = None
#                     # swap lead
#                     first_player = crib_owner
#                     crib_owner   = 'Player 1' if first_player == 'Player 2' else 'Player 2'
#                     # reset scorer
#                     scorer.cut_card       = None
#                     scorer.pegging_stack.clear()
#                     scorer.current_total  = 0
#                     # restart cut timer
#                     cut_ready = time.time() + SILENCE_CUT
#                 continue

#         # ── Draw & FPS ──────────────────────────────────────────────
#         for card in detections:
#             if hasattr(card, 'contour'):
#                 cv2.drawContours(img, [card.contour], -1, (255,0,0), 2)
#             if hasattr(card, 'center') and card.center is not None:
#                 x, y = map(int, card.center)
#                 cv2.circle(img, (x,y), 5, (0,255,255), -1)
#         cv2.line(img, (p1_x,0), (p1_x, IM_HEIGHT), (0,255,0), 2)
#         cv2.line(img, (p2_x,0), (p2_x, IM_HEIGHT), (255,0,0), 2)
#         fps = 1 / ((cv2.getTickCount() - t0) / freq)
#         cv2.putText(img, f'FPS:{int(fps)}', (20,40), font,1,(255,255,0),2)
#         try:
#             picam2.set_overlay(img)
#         except:
#             pass

#         time.sleep(0.2)

# except KeyboardInterrupt:
#     print("\n[INFO] Terminated by user.")
# finally:
#     picam2.stop_preview()
#     picam2.stop()
#     cv2.destroyAllWindows()



###### Working best one 4/21 2PM ########
# CardDetector.py  (Full Game Loop with Multiple Rounds, fixed resets and seen logic)
# -------------------------------------------------------------------------------
# import cv2
# import numpy as np
# import time
# import os
# import shutil
# import uuid
# import sys
# import Cards
# from picamera2 import Picamera2, Preview
# from CribbageScorer import CribbageScorer

# # ---------- Setup: Image Saving ----------
# SAVE_FOLDER = 'captured_images'
# if os.path.exists(SAVE_FOLDER):
#     shutil.rmtree(SAVE_FOLDER)
# os.makedirs(SAVE_FOLDER)

# def save_image(image, index):
#     cv2.imwrite(f"{SAVE_FOLDER}/image_{uuid.uuid4().hex}.jpg", image)

# # ---------- Setup: Camera ----------
# picam2 = Picamera2()
# picam2.configure(picam2.create_preview_configuration({"size": (1280,720)}))
# picam2.start_preview(Preview.DRM, x=200, y=500)
# picam2.start()
# time.sleep(1)

# # ---------- Constants ----------
# initial = picam2.capture_array()
# IM_HEIGHT, IM_WIDTH = initial.shape[:2]
# freq = cv2.getTickFrequency()
# font = cv2.FONT_HERSHEY_SIMPLEX
# PEGGING_CARDS_PER_PLAYER = 4
# GAME_END_SCORE = 51

# # ---------- Load Training Images ----------
# path = os.path.dirname(os.path.abspath(__file__))
# train_ranks = Cards.load_ranks(path + '/Card_Imgs/')
# train_suits = Cards.load_suits(path + '/Card_Imgs/')

# # ---------- Initialize Scorer & Regions ----------
# scorer = CribbageScorer()
# player1_x = IM_WIDTH//3
# player2_x = 2*IM_WIDTH//3
# scorer.regions = {
#     'Player 1': (0, 0, player1_x, IM_HEIGHT),
#     'Player 2': (player1_x, 0, player2_x, IM_HEIGHT),
#     'Crib':      (player2_x, 0, IM_WIDTH, IM_HEIGHT)
# }

# # ---------- Game State ----------
# state = 'cut'
# last_state = None
# play_count = 0
# crib_count = 0
# player_hands = {'Player 1': [], 'Player 2': []}
# crib_cards = []
# used_card_names = set()
# cut_card = None
# first_player = None
# crib_owner = None

# # ---------- Helpers ----------
# def prompt_stage():
#     global last_state
#     if state != last_state:
#         if state == 'cut':
#             print("🟥 Round start: Place cut card in crib region.")
#         elif state == 'play':
#             print(f"🎴 Pegging ({PEGGING_CARDS_PER_PLAYER} each). {first_player} to lead.")
#         elif state == 'crib':
#             print(f"🗄️ Crib phase: {crib_owner}, place 4 cards.")
#         last_state = state

# # ---------- Section Mapping ----------
# def get_section(x):
#     if x < player1_x: return 'player1'
#     if x < player2_x: return 'player2'
#     return 'crib'

# # ---------- Main Loop ----------
# try:
#     while True:
#         prompt_stage()
#         img = picam2.capture_array()
#         t0 = cv2.getTickCount()

#         pre = Cards.preprocess_image(img)
#         cnts, flags = Cards.find_cards(pre)
#         detections = []
#         if cnts:
#             for i, c in enumerate(cnts):
#                 if flags[i] != 1: continue
#                 card, warp = Cards.preprocess_card(c, img)
#                 card.warp = warp
#                 (card.best_rank_match, card.best_suit_match,
#                  card.rank_diff, card.suit_diff) = Cards.match_card(card, train_ranks, train_suits)
#                 detections.append(card)

#         for card in detections:
#             name = f"{card.best_rank_match} of {card.best_suit_match}"
#             # Skip unknown or already used
#             if 'Unknown' in (card.best_rank_match, card.best_suit_match): continue
#             if name in used_card_names: continue
#             if not hasattr(card, 'corner_pts') or card.corner_pts is None: continue

#             cx, cy = ((int(card.center[0]), int(card.center[1]))
#                       if hasattr(card, 'center') and card.center is not None
#                       else (int(np.mean(card.corner_pts[:,0])), int(np.mean(card.corner_pts[:,1]))))
#             sec = get_section(cx)

#             # CUT stage
#             if state == 'cut' and sec == 'crib':
#                 used_card_names.add(name)
#                 cut_card = name
#                 scorer.cut_card = name
#                 scorer.set_first_card_in_crib(name)
#                 print(f"🟥 Cut card: {name}")
#                 state = 'play'
#                 continue

#             # PLAY stage
#             if state == 'play':
#                 # Determine first player and crib owner
#                 if play_count == 0 and sec in ('player1', 'player2'):
#                     first_player = 'Player 1' if sec == 'player1' else 'Player 2'
#                     crib_owner = 'Player 2' if first_player == 'Player 1' else 'Player 1'
#                     scorer.set_first_player(first_player, crib_owner)

#                 expected = first_player if play_count % 2 == 0 else crib_owner
#                 sec_p = 'Player 1' if sec == 'player1' else ('Player 2' if sec == 'player2' else None)
#                 if sec_p == expected:
#                     used_card_names.add(name)
#                     player_hands[sec_p].append(name)
#                     scorer.card_detected_in_hand(sec_p, name, (cx, cy))
#                     play_count += 1
#                     if play_count < 2 * PEGGING_CARDS_PER_PLAYER:
#                         next_p = first_player if play_count % 2 == 0 else crib_owner
#                         print(f"➡️ {sec_p} played {name}. Next: {next_p}.")
#                     else:
#                         print(f"🛑 Pegging complete. Scores: {scorer.get_scores()}")
#                         state = 'crib'
#                 continue

#             # CRIB stage
#             if state == 'crib' and sec == 'crib':
#                 used_card_names.add(name)
#                 crib_cards.append(name)
#                 crib_count += 1
#                 print(f"🗄️ Crib card {name} ({crib_count}/4)")
#                 if crib_count == 4:
#                     scorer.score_round(player_hands['Player 1'], player_hands['Player 2'], crib_cards, cut_card)
#                     print(f"📊 Round scores: {scorer.get_scores()}")
#                     # Check end game
#                     for p, score in scorer.get_scores().items():
#                         if score >= GAME_END_SCORE:
#                             print(f"🥳 Game over! {p} wins with {score}.")
#                             sys.exit(0)
#                     # Reset for next round
#                     print("🔄 Next round starting; crib passes.")
#                     # Reset detector/game state
#                     state = 'cut'
#                     last_state = None
#                     play_count = 0
#                     crib_count = 0
#                     player_hands = {'Player 1': [], 'Player 2': []}
#                     crib_cards = []
#                     used_card_names.clear()
#                     cut_card = None
#                     first_player = None
#                     crib_owner = None
#                     # Reset scorer round data
#                     scorer.cut_card = None
#                     scorer.pegging_stack.clear()
#                     scorer.current_total = 0
#                 continue

#         # Debug overlays
#         for card in detections:
#             if hasattr(card, 'contour'): cv2.drawContours(img, [card.contour], -1, (255, 0, 0), 2)
#             if hasattr(card, 'center') and card.center is not None:
#                 x, y = int(card.center[0]), int(card.center[1])
#                 cv2.circle(img, (x, y), 5, (0, 255, 255), -1)
#         cv2.line(img, (player1_x, 0), (player1_x, IM_HEIGHT), (0, 255, 0), 2)
#         cv2.line(img, (player2_x, 0), (player2_x, IM_HEIGHT), (255, 0, 0), 2)
#         fps = 1 / ((cv2.getTickCount() - t0) / freq)
#         cv2.putText(img, f'FPS:{int(fps)}', (20, 40), font, 1, (255, 255, 0), 2)
#         try:
#             picam2.set_overlay(img)
#         except:
#             pass
#         time.sleep(0.2)

# except KeyboardInterrupt:
#     print("\n[INFO] Terminated by user.")
# finally:
#     picam2.stop_preview()
#     picam2.stop()
#     cv2.destroyAllWindows()









# ##### WORKING 4/21 ####


# import cv2
# import numpy as np
# import time
# import os
# import shutil
# import uuid
# import Cards
# from picamera2 import Picamera2, Preview

# # ---------- Setup: Image Saving ----------
# SAVE_FOLDER = 'captured_images'
# if os.path.exists(SAVE_FOLDER):
#     shutil.rmtree(SAVE_FOLDER)
# os.makedirs(SAVE_FOLDER)

# def save_image(image, index):
#     filename = f"{SAVE_FOLDER}/image_{uuid.uuid4().hex}.jpg"
#     cv2.imwrite(filename, image)

# # ---------- Setup: Camera ----------
# picam2 = Picamera2()
# picam2.configure(picam2.create_preview_configuration({"size": (1280, 720)}))
# picam2.start_preview(Preview.DRM, x=200, y=500)
# picam2.start()
# time.sleep(1)

# # ---------- Setup: Dimensions & Constants ----------
# initial_image = picam2.capture_array()
# IM_HEIGHT, IM_WIDTH = initial_image.shape[:2]
# FRAME_RATE = 10
# frame_rate_calc = 1
# freq = cv2.getTickFrequency()
# font = cv2.FONT_HERSHEY_SIMPLEX

# # ---------- Load Rank/Suit Training Images ----------
# path = os.path.dirname(os.path.abspath(__file__))
# train_ranks = Cards.load_ranks(path + '/Card_Imgs/')
# train_suits = Cards.load_suits(path + '/Card_Imgs/')

# # ---------- Tracking ----------
# player1_cards = set()
# player2_cards = set()
# crib_cards = set()
# seen_cards = set()

# # ---------- Define Regions ----------
# player1_x = IM_WIDTH // 3
# player2_x = 2 * IM_WIDTH // 3

# player1_region = (0, 0, player1_x, IM_HEIGHT)
# player2_region = (player1_x, 0, player2_x, IM_HEIGHT)
# crib_region    = (player2_x, 0, IM_WIDTH, IM_HEIGHT)

# print(f"[INFO] Image size: {IM_WIDTH}x{IM_HEIGHT}")
# print(f"[INFO] Regions -> Player 1: x<{player1_x}, Player 2: x<{player2_x}, Crib: x>={player2_x}")

# # ---------- Region Classifier ----------
# def get_card_section(cent_x, cent_y):
#     if player1_region[0] <= cent_x <= player1_region[2]:
#         return 'player1'
#     elif player2_region[0] <= cent_x <= player2_region[2]:
#         return 'player2'
#     elif crib_region[0] <= cent_x <= crib_region[2]:
#         return 'crib'
#     else:
#         return 'outside'

# # ---------- Card Formatter ----------
# def format_card(card):
#     card_name = f"{card.best_rank_match} of {card.best_suit_match}"

#     if hasattr(card, 'corner_pts') and card.corner_pts is not None:
#         card_id = tuple(card.corner_pts.flatten())
#         if card_id in seen_cards:
#             return card_name
#         seen_cards.add(card_id)

#         # Get centroid
#         if hasattr(card, 'center') and card.center is not None:
#             cent_x, cent_y = card.center
#         else:
#             cent_x = int(np.mean(card.corner_pts[:, 0]))
#             cent_y = int(np.mean(card.corner_pts[:, 1]))
#     else:
#         print(f"⚠️ Warning: No corner points for {card_name}. Defaulting to Crib.")
#         crib_cards.add(card_name)
#         return card_name

#     section = get_card_section(cent_x, cent_y)

#     if section == 'player1':
#         player1_cards.add(card_name)
#         assigned_to = "Player 1"
#     elif section == 'player2':
#         player2_cards.add(card_name)
#         assigned_to = "Player 2"
#     elif section == 'crib':
#         crib_cards.add(card_name)
#         assigned_to = "Crib"
#     else:
#         crib_cards.add(card_name)
#         assigned_to = "Unknown"

#     print(f"✅ Assigned {card_name} to {assigned_to} (center=({cent_x}, {cent_y}))")
#     return card_name

# # ---------- Card Display ----------
# def display_cards():
#     print("\n📢 Updated Hands:")
#     print("🎴 Player 1 Cards:", sorted(player1_cards))
#     print("🎴 Player 2 Cards:", sorted(player2_cards))
#     print("🎴 Crib Cards:", sorted(crib_cards))

# # ---------- Main Loop ----------
# try:
#     while True:
#         image = picam2.capture_array()
#         t1 = cv2.getTickCount()

#         pre_proc = Cards.preprocess_image(image)
#         cnts_sort, cnt_is_card = Cards.find_cards(pre_proc)
#         cards = []

#         if cnts_sort:
#             for i in range(len(cnts_sort)):
#                 if cnt_is_card[i] == 1:
#                     card, warp = Cards.preprocess_card(cnts_sort[i], image)
#                     card.warp = warp  # Attach the warp image to the card object for later use
#                     # card = Cards.preprocess_card(cnts_sort[i], image)
#                     card.best_rank_match, card.best_suit_match, \
#                     card.rank_diff, card.suit_diff = Cards.match_card(card, train_ranks, train_suits)
#                     image = Cards.draw_results(image, card)
#                     cards.append(card)

#         for card in cards:
#             format_card(card)

#             # Draw card contour
#             if hasattr(card, 'contour'):
#                 cv2.drawContours(image, [card.contour], -1, (255, 0, 0), 2)

#             # Draw centroid
#             if hasattr(card, 'center') and card.center is not None:
#                 cx, cy = map(int, card.center)
#                 cv2.circle(image, (cx, cy), 5, (0, 255, 255), -1)

#         display_cards()

#         # Draw region lines
#         cv2.line(image, (player1_x, 0), (player1_x, IM_HEIGHT), (0, 255, 0), 2)
#         cv2.line(image, (player2_x, 0), (player2_x, IM_HEIGHT), (255, 0, 0), 2)

#         # Show FPS
#         cv2.putText(image, f'FPS: {int(frame_rate_calc)}', (20, 40), font, 1, (255, 255, 0), 2)

#         # Show image
#         try:
#             picam2.set_overlay(image)
#         except Exception as e:
#             print("[WARNING] Could not overlay image:", e)

#         # FPS Calculation
#         t2 = cv2.getTickCount()
#         time1 = (t2 - t1) / freq
#         frame_rate_calc = 1 / time1

#         # Save warped card image
#         for card in cards:
#             save_image(card.warp, time.time())

#         # Quit key
#         key = cv2.waitKey(1) & 0xFF
#         if key == ord('q'):
#             break

#         time.sleep(0.2)

# except KeyboardInterrupt:
#     print("\n[INFO] Program terminated by user.")
#     display_cards()

# # ---------- Cleanup ----------
# picam2.stop_preview()
# picam2.stop()
# cv2.destroyAllWindows()


# ### WORKING 4/21 ####
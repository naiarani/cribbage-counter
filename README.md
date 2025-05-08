# MMAE 432 Capstone

## What is it?
This repo contains all files to operate an automatic cribbage scorer system, connected to a physical gameboard. See more information on our project here:

https://sites.google.com/view/holy-mackerel


The OpenCV-based python code to detect and identify playing cards from a PiCamera video feed is based off an existing project. Check out the YouTube video that describes what it does and how it works:

https://www.youtube.com/watch?v=m-QPjO-2IkA


## Usage
This code runs with to physical subsystems: A Card Detector and an Automated Scoring Gameboard. The Card Detector hosts a Raspberry Pi 5 and ArduCAM 3 with a button connected to the Pi's GPIO17 pin. The Automated Scoring Gameboard consists of 2 stepper motors that drive a chain around a loop. The chain has a magnet attached to it that connects to a game piece through a wooden panel. See more on the physical design on our website. 

Download this repository to a directory and run CardDetector.py from that directory. Cards need to be placed on a dark background for the detector to work. Press CTRL 'C' to end the program. The terminal will guide users in the gameplay as well as the point updates in case you do not have the automated scoring gameboard. 

The program was originally designed to run on a Raspberry Pi with a Linux OS, but it can also be run on Windows 7/8/10. To run on Windows, download and install Anaconda (https://www.anaconda.com/download/, Python 3.6 version), launch Anaconda Prompt, and execute the program by launching IDLE (type "idle" and press ENTER in the prompt) and opening/running the CardDetector.py file in IDLE. The Anaconda environment comes with the opencv and numpy packages installed, so you don't need to install those yourself. If you are running this on Windows, you will also need to change the program to use a USB camera, as described below.

The card detector will work best if you use isolated rank and suit images generated from your own cards. To do this, run Rank_Suit_Isolator.py to take pictures of your cards. It will ask you to take a picture of an Ace, then a Two, and so on. Then, it will ask you to take a picture of one card from each of the suits (Spades, Diamonds, Clubs, Hearts). As you take pictures of the cards, the script will automatically isolate the rank or suit and save them in the Card_Imgs directory (overwriting the existing images).


## Files
CardDetector.py contains the main script

Cards.py has classes and functions that are used by CardDetector.py

PiVideoStream.py creates a video stream from the PiCamera, and is used by CardDetector.py

Rank_Suit_Isolator.py is a standalone script that can be used to isolate the rank and suit from a set of cards to create train images

Card_Imgs contains all the train images of the card ranks and suits

Cribbage_Scorer.py contains the scoring logic for cribbage. 

test_button.py and test_camera.py are debugging tools to allow you to test the camera and "GO" button functionalities seperately.

Within mmae_432microcontroller folder contains mmae432_motorcontroller.ino which is the code that intakes serial monitor outputs from the Pi and interprets the motor steps accordingly to move the Automated Scoring Gameboard.

## Dependencies
Python 3.6

OpenCV-Python 3.2.0 and numpy 1.8.2:
See https://www.pyimagesearch.com/2016/04/18/install-guide-raspberry-pi-3-raspbian-jessie-opencv-3/
for how to build and install OpenCV-Python on the Raspberry Pi

Picamera2 library:
```
sudo apt-get update
sudo apt-get install python-picamera python3-picamera
```



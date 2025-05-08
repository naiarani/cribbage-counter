#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time

# Change this if you wired to a different BCM pin
GO_BUTTON_PIN = 17

def main():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(GO_BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    print(f"Press the button connected to GPIO{GO_BUTTON_PIN} (Ctrl+C to exit)...")
    try:
        last_state = GPIO.input(GO_BUTTON_PIN)
        while True:
            current_state = GPIO.input(GO_BUTTON_PIN)
            # button is wired to GND, so pressed == LOW
            if current_state == GPIO.LOW and last_state == GPIO.HIGH:
                print("🔘 PRESSED")
            elif current_state == GPIO.HIGH and last_state == GPIO.LOW:
                print("⚪ RELEASED")
            last_state = current_state
            time.sleep(0.05)  # 50 ms debounce polling
    except KeyboardInterrupt:
        print("\nExiting")
    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    main()

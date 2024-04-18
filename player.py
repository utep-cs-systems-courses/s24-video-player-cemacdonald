#!/usr/bin/env python3

import threading
import cv2
import numpy as np
import base64
from threading import Semaphore, Lock

# Sentinel value to indicate the end of processing
SENTINEL = None

# Flag to signal the main thread to close the window
close_window_flag = False

def extractFrames(fileName, outputBuffer, bufferLock, emptySlots, filledSlots, maxFramesToLoad=9999):
    # Initialize frame count
    count = 0

    # Open video file
    vidcap = cv2.VideoCapture(fileName)

    # Read first image
    success, image = vidcap.read()

    print(f'Reading frame {count} {success}')
    while success and count < maxFramesToLoad:
        # Wait for an empty slot in the buffer
        emptySlots.acquire()

        # Acquire the lock to modify the buffer
        bufferLock.acquire()

        # Add the frame to the buffer
        outputBuffer.append(image)

        # Release the lock and signal that a frame was added
        bufferLock.release()
        filledSlots.release()

        # Read the next frame
        success, image = vidcap.read()
        print(f'Reading frame {count} {success}')
        count += 1

    # Signal the end of processing by adding a sentinel value to the buffer
    emptySlots.acquire()
    bufferLock.acquire()
    outputBuffer.append(SENTINEL)
    bufferLock.release()
    filledSlots.release()

    print('Frame extraction complete')

def convertFramesToGrayscale(inputBuffer, outputBuffer, bufferLock, inputLock, outputLock, inputFilledSlots, inputEmptySlots, outputFilledSlots, outputEmptySlots):

    # Initialize the frame count
    count = 0

    # Go through each frame in the input buffer until the buffer is empty
    while True:
        # Wait for a filled slot in the input buffer
        inputFilledSlots.acquire()

        # Acquire the lock to modify the input buffer
        inputLock.acquire()

        # Get the next frame or sentinel value
        frame = inputBuffer.pop(0)

        # Release the lock and signal that an item was removed
        inputLock.release()
        inputEmptySlots.release()

        # Check if it's the sentinel value
        if frame is SENTINEL:
            # Add sentinel value to output buffer
            outputEmptySlots.acquire()
            outputLock.acquire()
            outputBuffer.append(frame)
            outputLock.release()
            outputFilledSlots.release()
            break

        print(f'Converting frame {count}')

        # Convert the image to grayscale
        grayscaleFrame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Wait for an empty slot in the output buffer
        outputEmptySlots.acquire()

        # Acquire the lock to modify the output buffer
        outputLock.acquire()

        # Add the converted frame to the output buffer
        outputBuffer.append(grayscaleFrame)

        # Release the lock and signal that an item was added
        outputLock.release()
        outputFilledSlots.release()

        count += 1

    print('Frame conversion complete')

def displayFrames(inputBuffer, bufferLock, filledSlots, emptySlots):

    # Initialize frame count
    count = 0

    # Go through each frame in the buffer until the buffer is empty
    while True:
        # Wait for a filled slot in the input buffer
        filledSlots.acquire()

        # Acquire the lock to modify the input buffer
        bufferLock.acquire()

        # Get the next frame or sentinel value
        frame = inputBuffer.pop(0)

        # Release the lock and signal that an item was removed
        bufferLock.release()
        emptySlots.release()

        # Check if it's the sentinel value
        if frame is SENTINEL:
            break

        print(f'Displaying frame {count}')        

        # Display the image in a window called "Video" and wait 42ms before displaying the next frame
        cv2.imshow('Video', frame)
        if cv2.waitKey(42) and 0xFF == ord("q"):
            global close_window_flag
            close_window_flag = True
            break

        count += 1

    print('Finished displaying all frames')
    cv2.destroyAllWindows()

# Filename of clip to load
filename = 'clip.mp4'

# Extra fluff to calculate the length of the mp4 file if you wanted to play the full thing
cap = cv2.VideoCapture(filename)
property_id = int(cv2.CAP_PROP_FRAME_COUNT)
length = int(cv2.VideoCapture.get(cap, property_id))

# Create shared buffers (lists) and synchronization primitives
extractionBuffer = []
conversionBuffer = []

# Create locks for synchronizing access to the buffers
extractionLock = Lock()
conversionLock = Lock()

# Create semaphores to control access to the buffers
extractionEmptySlots = Semaphore(10)  # Buffer capacity of 10
extractionFilledSlots = Semaphore(0)
conversionEmptySlots = Semaphore(10)  # Buffer capacity of 10
conversionFilledSlots = Semaphore(0)

# Start the extraction thread
extractThread = threading.Thread(target=extractFrames, args=(filename, extractionBuffer, extractionLock, extractionEmptySlots, extractionFilledSlots, 72))
extractThread.start()

# Start the conversion thread
convertThread = threading.Thread(target=convertFramesToGrayscale, args=(extractionBuffer, conversionBuffer, extractionLock, conversionLock, conversionLock, extractionFilledSlots, extractionEmptySlots, conversionFilledSlots, conversionEmptySlots))
convertThread.start()

# Start the display thread
displayThread = threading.Thread(target=displayFrames, args=(conversionBuffer, conversionLock, conversionFilledSlots, conversionEmptySlots))
displayThread.start()

# Wait for all threads to finish
extractThread.join()
convertThread.join()
displayThread.join()

# Edge Impulse - OpenMV FOMO Object Detection Example
#
# This work is licensed under the MIT license.
# Copyright (c) 2013-2024 OpenMV LLC. All rights reserved.
# https://github.com/openmv/openmv/blob/master/LICENSE

import sensor, image, time, ml, math, uos, gc
#from collections import deque, counter # deque = double ended queue

# Detection control variables
FRAMES_DETECTION_TIMES = 4 # number of frames to track
MIN_DETECTION_RATIO = 0.75 # minimum of 75% thershold an object needs to be detected

# Deque to store detected labels from recent frames
#recent_detections = deque(maxlen=FRAMES_DETECTION_TIMES)
# Opslag voor de laatste N frames van detecties
recent_detections = []  # Elke entry is een lijst van labels per frame

# Camera setup
sensor.reset()                         # Reset and initialize the sensor.
sensor.set_pixformat(sensor.RGB565)    # Set pixel format to RGB565 (or GRAYSCALE)
sensor.set_framesize(sensor.QVGA)      # Set frame size to QVGA (320x240)
sensor.set_windowing((240, 240))       # Set 240x240 window.
sensor.skip_frames(time=2000)          # Let the camera adjust.

# -- Model setup --
net = None
labels = None
min_confidence = 0.5

try:
    # load the model, alloc the model file on the heap if we have at least 64K free after loading
    net = ml.Model("trained.tflite", load_to_fb=uos.stat('trained.tflite')[6] > (gc.mem_free() - (64*1024)))
except Exception as e:
    raise Exception('Failed to load "trained.tflite", did you copy the .tflite and labels.txt file onto the mass-storage device? (' + str(e) + ')')

try:
    # Load label names from labels.txt
    labels = [line.rstrip('\n') for line in open("labels.txt")]
except Exception as e:
    raise Exception('Failed to load "labels.txt", did you copy the .tflite and labels.txt file onto the mass-storage device? (' + str(e) + ')')

# Colors used to draw detection results
colors = [ # Add more colors if you are detecting more than 7 types of classes at once.
    (255,   0,   0), # Red
    (  0, 255,   0), # Green
    (255, 255,   0), # Yellow
    (  0,   0, 255), # Blue
    (255,   0, 255), # Magenta
    (  0, 255, 255), # Cyan
    (255, 255, 255), # White
]

# Defines thresholds for object detection blob extraction
threshold_list = [(math.ceil(min_confidence * 255), 255)] # Convert confidence to 0-255 scale

# -- Post-processing function for FOMO --
def fomo_post_process(model, inputs, outputs):
    ob, oh, ow, oc = model.output_shape[0] # output shape: batch, height, width channels (classes)

    # Compute scaling factors and offsets to map detection to image coordinates
    x_scale = inputs[0].roi[2] / ow
    y_scale = inputs[0].roi[3] / oh

    scale = min(x_scale, y_scale)

    x_offset = ((inputs[0].roi[2] - (ow * scale)) / 2) + inputs[0].roi[0]
    y_offset = ((inputs[0].roi[3] - (ow * scale)) / 2) + inputs[0].roi[1]

    l = [[] for i in range(oc)] # Create a list of detections for each class

    for i in range(oc): # Loop through each class channel
        img = image.Image(outputs[0][0, :, :, i] * 255) # Convert prediction map to grayscale image
        blobs = img.find_blobs(
            threshold_list, x_stride=1, y_stride=1, area_threshold=1, pixels_threshold=1
        )

        for b in blobs:
            rect = b.rect() # Bounding box for blob
            x, y, w, h = rect

            # Calculate average confidence score in this area --> maybe adjust here to only accept >0.80
            score = (
                img.get_statistics(thresholds=threshold_list, roi=rect).l_mean() / 255.0
            )

            # Scale detection box back to original image coordinates
            x = int((x * scale) + x_offset)
            y = int((y * scale) + y_offset)
            w = int(w * scale)
            h = int(h * scale)
            l[i].append((x, y, w, h, score)) # Store detection data
    return l # Return list of detections for each class

# -- Main loop --
clock = time.clock()
while(True):
    clock.tick()
    img = sensor.snapshot()

    detected_labels = []  # Reset lijst voor dit frame

    # Voer predictie uit met post-processing
    for i, detection_list in enumerate(net.predict([img], callback=fomo_post_process)):
        if i == 0: continue  # Skip background class
        if len(detection_list) == 0: continue # Geen detecties voor deze klasse

        for x, y, w, h, score in detection_list:
         # Score-filter wordt al toegepast in fomo_post_process, maar nog extra check
         # dit kan je verhogen als er teveel wordt opgepakt of verlagen indien te weinig
            if score < 0.80:
                continue

            # Voeg label toe voor dit frame
            detected_labels.append(labels[i])

            # Bereken midden van bounding box en teken een cirkel
            center_x = math.floor(x + (w / 2))
            center_y = math.floor(y + (h / 2))
            print(f"x {center_x}\ty {center_y}\tscore {score:.2f}")
            img.draw_circle((center_x, center_y, 12), color=colors[i])

    # Voeg deze frame's detecties toe aan de geschiedenis
    recent_detections.append(detected_labels)

    # Beperk geschiedenis tot maximaal FRAMES_DETECTION_TIMES
    if len(recent_detections) > FRAMES_DETECTION_TIMES:
        recent_detections.pop(0)

    # Tellen hoe vaak elk label voorkomt in de laatste N frames
    label_frequency = {}
    for frame_labels in recent_detections:
        for label in frame_labels:
            label_frequency[label] = label_frequency.get(label, 0) + 1

    # Print alleen labels die in ≥ 75% van de laatste frames zijn gezien
    for label in label_frequency:
        if label_frequency[label] >= int(FRAMES_DETECTION_TIMES * MIN_DETECTION_RATIO):
            print("Bevestigde detectie van:", label)

    # Print het aantal frames per seconde
    print(clock.fps(), "fps\n")


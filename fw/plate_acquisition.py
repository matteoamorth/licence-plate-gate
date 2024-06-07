import sensor, image, time, os, tf, uos, gc

sensor.reset()                         # Reset and initialize the sensor
sensor.set_pixformat(sensor.RGB565)    # Set pixel format to RGB565 (or GRAYSCALE)
sensor.set_framesize(sensor.QVGA)      # Set frame size to QVGA (320x240)
sensor.set_windowing((240, 240))       # Set 240x240 window
sensor.skip_frames(time=2000)          # Let the camera adjust

# Load the plate model
try:
    net_plate = tf.load("trained_plate.tflite", load_to_fb=uos.stat('trained_plate.tflite')[6] > (gc.mem_free() - (64*1024)))
    labels_plate = [line.rstrip('\n') for line in open("labels_plate.txt")]
except Exception as e:
    raise Exception(f'Failed to load plate model or labels: {e}\n')

# Load the character model
try:
    net_chars = tf.load("trained_chars.tflite", load_to_fb=uos.stat('trained_chars.tflite')[6] > (gc.mem_free() - (64*1024)))
    labels_chars = [line.rstrip('\n') for line in open("labels_chars.txt")]
except Exception as e:
    raise Exception(f'Failed to load character model or labels: {e}\n')

confidence_th = 0.75
clock = time.clock()

while True:
    clock.tick()
    img = sensor.snapshot()

    # Detect plate
    for obj in net_plate.classify(img, min_scale=1.0, scale_mul=0.8, x_overlap=0.5, y_overlap=0.5):
        print("**********\nPlate at [x=%d,y=%d,w=%d,h=%d]" % obj.rect())

        img.draw_rectangle(obj.rect())

        plate_region = img.copy(roi=obj.rect())
        plate_region = plate_region.resize(300, 300)

        # optional filter on plates
        #threshold = plate_region.get_histogram().get_threshold().value()
        #plate_region.binary([(threshold, 255)], invert=True)

        plate_text = ""
        chars_predictions = net_chars.classify(plate_region, min_scale=1.0, scale_mul=0.8, x_overlap=0.5, y_overlap=0.5)

        chars_with_positions = []

        for char_obj in chars_predictions:
            char_predictions_list = list(zip(labels_chars, char_obj.output()))

            best_prediction = max(char_predictions_list, key=lambda x: x[1])

            if best_prediction[1] > confidence_th:
                x, _, _, _ = char_obj.rect()
                chars_with_positions.append((x, best_prediction[0]))


        # Sort characters by x
        chars_with_positions.sort(key=lambda item: item[0])

        # Build string
        plate_text = "".join([char for _, char in chars_with_positions])

        # Perform operations
        if plate_text:
            print(f"Recognized plate: {plate_text}")
        else:
            print("No characters recognized with sufficient confidence")

    print(clock.fps(), "fps")

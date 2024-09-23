# option A

import keras_ocr


pipeline = keras_ocr.pipeline.Pipeline()

images = [
    keras_ocr.tools.read('img/cropped_plate.jpg')  
]


prediction_groups = pipeline.recognize(images)


predicted_image = prediction_groups[0]


sorted_predictions = sorted(predicted_image, key=lambda p: p[1][0][0])  

for text, box in sorted_predictions:
    print(text)


# option B

import easyocr
import cv2


reader = easyocr.Reader(['en'], gpu=False)

image = cv2.imread('img/cropped_plate.jpg')

results = reader.readtext(image)

sorted_results = sorted(results, key=lambda x: x[0][0][0]) 

for (bbox, text, prob) in sorted_results:
    print(f'Text: {text}, Probability: {prob}')


import keras_ocr

def clean_text(text):
    cleaned_text = ''
    for char in text:
        if char.isalnum(): 
            cleaned_text += char
    return cleaned_text

pipeline = keras_ocr.pipeline.Pipeline()
image = keras_ocr.tools.read('img/plate.jpg')  
predicted_image = pipeline.recognize([image])[0] 
sorted_predictions = sorted(predicted_image, key=lambda p: p[1][0][0])  
result_string = ''.join([text for text, _ in sorted_predictions]) 
cleaned_result = clean_text(result_string)
final_str = cleaned_result.upper()
print(final_str)
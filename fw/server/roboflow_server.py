import functions as fn
import numpy as np
import cv2, base64, json
from influxdb_client import InfluxDBClient, Point, WriteOptions
import paho.mqtt.client as mqtt
import configparser

import cv2
import base64
import requests
import matplotlib.pyplot as plt
import keras_ocr
import numpy as np

from inference_sdk import InferenceHTTPClient

# MODE constants


DEBUG = 1

dprint = print if DEBUG else lambda *args, **kwargs: None

class ServerStateMachine:
    def __init__(self):
        dprint("Setting up server...")
        
        config = configparser.ConfigParser()
        config.read('server_config.ini')
        
        self.DEVICE_ID = config['Settings']['DEVICE_ID']
        self.CLIENT_ID = config['Settings']['CLIENT_ID']
        self.mode = config['Settings']['MODE']
        
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.connect(self.DEVICE_ID, config['MQTT Settings']['PORT'], 60)
        self.mqtt_client.subscribe(config['MQTT Topics']['TOPIC_SUBSCRIBE'])
        self.mqtt_client.loop_start()
        
        self.MODEL_ID = config['Roboflow']['MODEL_ID']
        self.robo_client =  InferenceHTTPClient(
                                api_url = config['Roboflow']['API_URL'],
                                api_key = config['Roboflow']['API_KEY']
                            )
        
        self.influx_client = InfluxDBClient(url=config['InfluxDB']['INFLUXDB_URL'], token=config['InfluxDB']['INFLUXDB_TOKEN'])
        self.write_api = self.influx_client.write_api(write_options=WriteOptions(batch_size=500, flush_interval=10_000, jitter_interval=2_000, retry_interval=5_000))
        
        self.mode = None # defined by the client
        self.state = "idle"
        
        
    def idle(self):
        dprint("Server is idle, waiting for messages...")
        

    def on_message(self, mqtt_client, userdata, msg):
        dprint('Incoming message...')
        
        try:
            msg_dict = json.loads(msg.payload)
            dprint(f"Received message: {msg_dict}")
            
            client_id = msg_dict.get('device_id')
            
            if self.CLIENT_ID == client_id:
                self.msg_payload = msg_dict.get('msg')
                self.state = "analysis"; return
                
            else:
                dprint("Wrong id client")
            
            self.state = "idle"
                
        except Exception as e:
            dprint(f"Failed to process message: {e}")
            self.state = "idle"
            

    def string_mode(self):
        dprint("Processing STRING_MODE...")
        self.check_string_record(self.msg_payload)
        self.state = "idle"            
  
        

    def analysis(self):
        dprint("Processing images...")
        img = self.base64_to_image(self.msg_payload)
        
        if img is not None:
            result = self.robo_client.infer(img, model_id=self.MODEL_ID)
        else: dprint("No image decoded"); return
        
        if result is None:
            dprint("No plate detected.")
            self.state = "idle"
            return
            
        predictions = result['predictions']
        best_plate = max(predictions, key=lambda p: p['confidence'])
        
        if self.target is None:
            dprint("New plate detected.")
            self.target = best_plate
            self.state = "idle"
            return
        
        if self.target['width'] > best_plate['width']:
                dprint("Car leaving ...")
                self.state = "idle"
                return
        
        self.target = best_plate
        img = crop_best_prediction(img,self.target)
        ### chars detection

        # process img
        preprocessImage(img)
        
        #evaluate
        
        images = [keras_ocr.tools.read(img)]
        # Get Predictions
        prediction_groups = pipeline.recognize(images)
        # Print the predictions
        for predictions in prediction_groups:
            for prediction in predictions:
                print(prediction[0])
        
        
        
        
    def preprocessImage(image):
        # Read Image
        img = cv2.imread(image)
        # Resize Image
        img = cv2.resize(img, None, fx=1.2, fy=1.2, interpolation=cv2.INTER_CUBIC)
        # Change Color Format
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Kernel to filter image
        kernel = np.ones((1, 1), np.uint8)
        # Dilate + Erode image using kernel
        img = cv2.dilate(img, kernel, iterations=1)
        img = cv2.erode(img, kernel, iterations=1)
        img = cv2.addWeighted(img, 4, cv2.blur(img, (30, 30)), -4, 128)
        # Save + Return image
        cv2.imwrite('processed.jpg', img)
        img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        return img
    

    def crop_best_prediction(self, image, best_prediction):
        x = best_prediction['x']
        y = best_prediction['y']
        width = best_prediction['width']
        height = best_prediction['height']

        # Calculate the coordinates of the rectangle
        left = x - width / 2
        top = y - height / 2
        right = x + width / 2
        bottom = y + height / 2

        # Crop the image based on the best prediction
        cropped_image = image.crop((left, top, right, bottom))

        dprint(f"Cropped image created")

        return cropped_image    
        
        

    def base64_to_image(self, base64_string):
        img_data = base64.b64decode(base64_string)
        img_array = np.frombuffer(img_data, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        return img

    def img2base64(self, img):
        _, buffer = cv2.imencode('.jpg', img)
        img_str = base64.b64encode(buffer).decode('utf-8')
        return img_str

    def check_string_record(self, text):
        query = f'from(bucket: "{INFLUXDB_BUCKET}") |> filter(fn: (r) => r["_measurement"] == "plates_registered" and r["plate_number"] == "{text}")'

        try:
            result = self.influx_client.query_api().query(query=query, org=INFLUXDB_ORG)

            if result:
                dprint(f"Record '{text}' found in InfluxDB.")
                self.store_access_record(text)
                self.send_gate_open_message()
            else:
                dprint(f"Record '{text}' not found in InfluxDB.")

        except Exception as e:
            dprint(f"Failed to query InfluxDB: {e}")

    def store_access_record(self, plate):
        point = Point("accesses").tag("plate_number", plate)
        self.write_api.write(INFLUXDB_BUCKET, INFLUXDB_ORG, point)

    def send_gate_open_message(self):
            msg = {
                "device_id": self.DEVICE_ID,
                "action": "gate_open"
            }
            self.mqtt_client.publish(self.TOPIC_TARGET, json.dumps(msg))

    def run(self):
        state_functions = {
            "idle": self.idle,
            "analysis": self.analysis,
        }

        while True:
            state_function = state_functions.get(self.state)
            if state_function:
                state_function()
            else:
                dprint(f"Unknown state: {self.state}")
                break

if __name__ == "__main__":
    sm = ServerStateMachine()
    
    
    
    sm.run()

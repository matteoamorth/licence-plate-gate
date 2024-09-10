#   _      _ _                    _           
#  | |    (_) |                  (_)          
#  | |     _| |__  _ __ __ _ _ __ _  ___  ___ 
#  | |    | | '_ \| '__/ _` | '__| |/ _ \/ __|
#  | |____| | |_) | | | (_| | |  | |  __/\__ \
#  |______|_|_.__/|_|  \__,_|_|  |_|\___||___/
                                            
                                            
# parsing libraries
import configparser, json

# images libraries
import cv2, base64
import numpy as np
from PIL import Image


# roboflow libraries
import keras_ocr
from inference_sdk import InferenceHTTPClient

# influxDB 
from influxdb_client import InfluxDBClient, Point, WriteOptions

# mqtt
import paho.mqtt.client as mqtt


#   _                     _             _   _   _                 
#  | |                   | |           | | | | (_)                
#  | |     ___   ___ __ _| |   ___  ___| |_| |_ _ _ __   __ _ ___ 
#  | |    / _ \ / __/ _` | |  / __|/ _ \ __| __| | '_ \ / _` / __|
#  | |___| (_) | (_| (_| | |  \__ \  __/ |_| |_| | | | | (_| \__ \
#  |______\___/ \___\__,_|_|  |___/\___|\__|\__|_|_| |_|\__, |___/
#                                                        __/ |    
#                                                       |___/     

CONFIG_FILENAME = 'server_config.ini'
STRING_MODE  = 1
CHARS_MODE   = 2
CAMERA_MODE  = 3
DEBUG = True

# Macros
dprint = print if DEBUG else lambda *args, **kwargs: None

dprint('######################################################################\n\nPlate recognition server\n\n######################################################################\n')
#pipeline = keras_ocr.pipeline.Pipeline()


######################################################################

class Program:
    
    #
    #   _____      _               
    #  / ____|    | |              
    # | (___   ___| |_ _   _ _ __  
    #  \___ \ / _ \ __| | | | '_ \ 
    #  ____) |  __/ |_| |_| | |_) |
    # |_____/ \___|\__|\__,_| .__/ 
    #                       | |    
    #                       |_|     
    #
    
    def __init__(self):
         
        dprint('Setting up server...\n')
        
        self.state = 'idle'
        self.msg_payload = None
        self.client_mode = None # defined by client
        self.img = None
        self.prediction = None
        self.mode = None
        
        # import settings
        config = configparser.ConfigParser()
        config.read(CONFIG_FILENAME)
        
        self.DEVICE_ID = config['Settings']['DEVICE_ID']
        self.CLIENT_ID = config['Settings']['CLIENT_ID'] ## make it an array
        
        
        # model 
        self.MODEL_ID = config['Roboflow']['MODEL_ID']
        self.robo_client =  InferenceHTTPClient(
            api_url = config['Roboflow']['API_URL'],
            api_key = config['Roboflow']['API_KEY'])
        
        # influx 
        self.influx_client = InfluxDBClient(url=config['InfluxDB']['INFLUXDB_URL'], token=config['InfluxDB']['INFLUXDB_TOKEN'])
        self.write_api = self.influx_client.write_api(write_options=WriteOptions(batch_size=500, 
                                                                                 flush_interval=10_000, 
                                                                                 jitter_interval=2_000, 
                                                                                 retry_interval=5_000))
        self.influx_org = config['InfluxDB']['INFLUXDB_ORG']
        self.influx_bucket = config['InfluxDB']['INFLUXDB_BUCKET']
        
        # mqtt
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.username_pw_set(config['MQTT Settings']['USER'], config['MQTT Settings']['PASSWORD'])
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.connect(config['MQTT Settings']['BROKER'], int(config['MQTT Settings']['PORT']), 60)
        self.mqtt_client.subscribe(config['MQTT Topics']['TOPIC_SUBSCRIBE'])
        
        self.mqtt_sub = config['MQTT Topics']['TOPIC_SUBSCRIBE']
        self.mqtt_targ = config['MQTT Topics']['TOPIC_TARGET']
        self.mqtt_dbg = config['MQTT Topics']['TOPIC_DEBUG']
        
        self.mqtt_client.loop_start()

        ### end of __init__ ###
    
    
    def idle(self):
        dprint('Server is idle, waiting for messages...')
        
        ### end of idle ###
    
    
    #    _____      _ _ _                _    
    #   / ____|    | | | |              | |   
    #  | |     __ _| | | |__   __ _  ___| | __
    #  | |    / _` | | | '_ \ / _` |/ __| |/ /
    #  | |___| (_| | | | |_) | (_| | (__|   < 
    #   \_____\__,_|_|_|_.__/ \__,_|\___|_|\_\                               
    
    def on_message(self, mqtt_client, userdata, msg):
        dprint('Reading incoming message...')
        
        try:
            msg_dict = json.loads(msg.payload)
            dprint('Received message: {msg_dict}')
            client_id = msg_dict.get('device_id')
            self.client_mode = msg_dict.get('mode')
            
            if self.CLIENT_ID not in client_id:
                dprint('No record match')
                self.client_mode = None
                return
            
            self.mqtt_client.loop_stop() # block mqtt callback 
            self.msg_payload = msg_dict.get('msg')
            
            
            if self.client_mode == CAMERA_MODE: self.state = 'plate_detection'; return
            if self.client_mode == CHARS_MODE: self.state = 'chars_detection'; return
            if self.client_mode == STRING_MODE: self.state = 'string_detection'; return
            else: 
                dprint('Unknown mode {self.client_mode}') 
                self.state = 'idle'   
            
        except Exception as e:
            dprint('Failed to process message: {e}')
            self.state = 'idle'
        

    #   _____                                                                _             
    #  |_   _|                                                              (_)            
    #    | |  _ __ ___   __ _  __ _  ___   _ __  _ __ ___   ___ ___  ___ ___ _ _ __   __ _ 
    #    | | | '_ ` _ \ / _` |/ _` |/ _ \ | '_ \| '__/ _ \ / __/ _ \/ __/ __| | '_ \ / _` |
    #   _| |_| | | | | | (_| | (_| |  __/ | |_) | | | (_) | (_|  __/\__ \__ \ | | | | (_| |
    #  |_____|_| |_| |_|\__,_|\__, |\___| | .__/|_|  \___/ \___\___||___/___/_|_| |_|\__, |
    #                          __/ |      | |                                         __/ |
    #                         |___/       |_|                                        |___/ 

    def plate_detection(self):
        dprint('Processing images...')
        self.img = self.base2image(self.msg_payload)
        
        if self.img is None:
            dprint('No image decoded') 
            self.state = 'idle'
            self.mqtt_client.loop_start()
            return
        
        result = self.robo_client.infer(self.img, model_id=self.MODEL_ID)
        
        if result is None:
            dprint('No plate detected.')
            self.state = 'idle'
            self.mqtt_client.loop_start()
            return
        
        predictions = result['predictions']
        best_plate = max(predictions, key=lambda p: p['confidence'])
        
        if self.prediction is None:
            dprint('New plate detected.')
            self.prediction = best_plate
            self.state = 'idle'
            self.mqtt_client.loop_start()
            return

        if self.prediction['width'] > best_plate['width']:
            dprint('Car leaving ...')
            self.prediction = None
            self.state = 'idle'
            self.mqtt_client.loop_start()
            return
        
        
        self.state = 'img_crop'
        
    
    def img_crop(self):
        dprint('Selecting the plate ...')
        x = self.prediction['x']
        y = self.prediction['y']
        w = self.prediction['width']
        h = self.prediction['height']
        
        L = x - w / 2
        R = x + w / 2
        T = y - h / 2
        B = y + h / 2
        
        self.img = self.img.crop((L, T, R, B))
        
        dprint('Cropped image created')
        
        self.state = 'chars_detection'
     
        
    def chars_detection(self):
        dprint('Processing plate...')
        
        if self.mode == CHARS_MODE:
            img = self.base2image(self.msg_payload)
            
            if img is None:
                dprint('No image decoded'); 
                self.state = 'idle'
                self.mqtt_client.loop_start()
                return
        
        # Preprocessing
        img = cv2.resize(img, None, fx=1.2, fy=1.2, interpolation=cv2.INTER_CUBIC)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        kernel = np.ones((1, 1), np.uint8)
        img = cv2.dilate(img, kernel, iterations=1)
        img = cv2.erode(img, kernel, iterations=1)
        img = cv2.addWeighted(img, 4, cv2.blur(img, (30, 30)), -4, 128)
        self.img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        
        # Evaluation
        images_list = [keras_ocr.tools.read(self.img)]
        prediction_groups = pipeline.recognize(images_list)
        predictions = prediction_groups[0]
        sorted_predictions = sorted(predictions, key=lambda p: p[1][0][0])
        
        recognized_text = ''.join([prediction[0] for prediction in sorted_predictions])

        
        dprint(f"Recognized text: {recognized_text}")
        self.msg_payload = recognized_text
        self.state = 'string_detection'
    
    
    #   _____        _                          _             _   _             
    #  |  __ \      | |                        | |           | | (_)            
    #  | |  | | __ _| |_ __ _    _____   ____ _| |_   _  __ _| |_ _  ___  _ __  
    #  | |  | |/ _` | __/ _` |  / _ \ \ / / _` | | | | |/ _` | __| |/ _ \| '_ \ 
    #  | |__| | (_| | || (_| | |  __/\ V / (_| | | |_| | (_| | |_| | (_) | | | |
    #  |_____/ \__,_|\__\__,_|  \___| \_/ \__,_|_|\__,_|\__,_|\__|_|\___/|_| |_|
                                                                              
                                                                              
    
    def string_detection(self):
        dprint('Processing STRING_MODE...')
        
        query = 'from(bucket: "{self.influx_bucket}") |> ' \
                'filter(fn: (r) => r["_measurement"] == "plates_registered" and ' \
                'r["plate_number"] == "{self.msg_payload}")'
        try:
            result = self.influx_client.query_api().query(query=query, org=self.influx_org)

            if result:
                dprint('Record "{self.msg_payload}" found in InfluxDB.')
                self.store_access_record(self.msg_payload)
                self.send_gate_open_message()
            else:
                dprint('Record "{self.msg_payload}" not found in InfluxDB.')

        except Exception as e:
            dprint('Failed to query InfluxDB: {e}')

        self.mqtt_client.loop_start()
        self.state = "idle"
        
                                                
    def base2image(self, base64_string):
        img_data = base64.b64decode(base64_string)
        img_array = np.frombuffer(img_data, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        return img
    
    
    def store_access_record(self, plate):
        point = Point("accesses").tag("plate_number", plate)
        self.write_api.write(self.influx_bucket, self.influx_org, point)


    def send_gate_open_message(self):
            msg = {
                "device_id": self.DEVICE_ID,
                "action": "gate_open"
            }
            self.mqtt_client.publish(self.mqtt_targ, json.dumps(msg))


    def run(self):
        state_functions = {
            'idle': self.idle,
            'plate_detection': self.plate_detection,
            'chars_detection': self.chars_detection,
            'string_detection': self.string_detection,
            'img_crop': self.img_crop
        }

        while True:
            state_function = state_functions.get(self.state)
            if state_function:
                state_function()
            else:
                dprint(f"Unknown state: {self.state}")
                break
            
            
if __name__ == "__main__":
    sm = Program()
    
    sm.run()
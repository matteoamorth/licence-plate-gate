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


# images libraries
import keras_ocr
from inference_sdk import InferenceHTTPClient

# influxDB 
from influxdb_client import InfluxDBClient, Point, rest
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.rest import ApiException

# mqtt
import paho.mqtt.client as mqtt

# debug
import logging
import colorlog


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

DEPRECATED_PLATE = -1
ACTIVE_PLATE = 1


# Log
log = logging.getLogger('LPG-Server')
log.setLevel(logging.DEBUG)

# File
file_formatter = logging.Formatter('%(asctime)s [%(levelname)s] - %(message)s')
file_handler = logging.FileHandler('log/plate_recognition_server.log')
file_handler.setFormatter(file_formatter)
file_handler.setLevel(logging.DEBUG)
log.addHandler(file_handler)

# Console
console_formatter = colorlog.ColoredFormatter('%(log_color)s%(asctime)s [%(name)s] - %(levelname)s - %(message)s',
    log_colors={
        'DEBUG': 'white',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'bold_red',
    }
)

console_handler = logging.StreamHandler()
console_handler.setFormatter(console_formatter)
console_handler.setLevel(logging.DEBUG)
log.addHandler(console_handler)


log.info('\n######################################################################\n\nPlate recognition server\n\n######################################################################\n')


######################################################################

class Program:
    '''
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
    '''
    def __init__(self):
         
        log.info('Server init ...')
        
        self.state = 'idle'
        self.msg_payload = None
        self.client_mode = None # defined by client
        self.img = None
        self.prediction = None
        self.mode = None
        
        config = configparser.ConfigParser()
        config.read(CONFIG_FILENAME)
        
        
        self.DEVICE_ID = config['Settings']['DEVICE_ID']
        self.CLIENT_ID = config['Settings']['CLIENT_ID'] ## make it an array
        
        self.DEVICE_ID= 'server_01'
        log.info('DEVICE ID: ' + str(self.DEVICE_ID))
        
        # model 
        log.debug('Loading Roboflow model')
        self.MODEL_ID = config['Roboflow']['MODEL_ID']
        self.robo_client =  InferenceHTTPClient(
            api_url = config['Roboflow']['API_URL'],
            api_key = config['Roboflow']['API_KEY'])
        
        # database 
        self.influxdb_setup(config)
        if self.state == "exit":
            return
        # connection
        self.MQTT_setup(config)
        if self.state == "exit":
            return
        
        log.info("[CORE] - Waiting for incoming messages")
        
    """
    #   _____        __ _            _____  ____             _                 
    #  |_   _|      / _| |          |  __ \|  _ \           | |                
    #    | |  _ __ | |_| |_   ___  _| |  | | |_) |  ___  ___| |_ _   _ _ __    
    #    | | | '_ \|  _| | | | \ \/ / |  | |  _ <  / __|/ _ \ __| | | | '_ \   
    #   _| |_| | | | | | | |_| |>  <| |__| | |_) | \__ \  __/ |_| |_| | |_) |  
    #  |_____|_| |_|_| |_|\__,_/_/\_\_____/|____/  |___/\___|\__|\__,_| .__/   
    #                                                                 | |      
    #                                                                 |_|      
    """
        
    # influx
    def influxdb_setup(self,config): 
        try:
            log.debug('[INFLUXDB] - Loading')
            self.influx_client = InfluxDBClient(url=config['InfluxDB']['INFLUXDB_URL'], 
                                                token=config['InfluxDB']['INFLUXDB_TOKEN'],
                                                org=config['InfluxDB']['INFLUXDB_ORG'])
            
            self.influx_write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)
            self.influx_query_api = self.influx_client.query_api()
            self.buckets_api = self.influx_client.buckets_api()
            
            test_query = 'buckets()'
            
            result = self.influx_query_api.query(query=test_query)
            
            for table in result:
                for record in table.records:
                    log.debug(f"[INFLUXDB] - Bucket avaiable: {record.values.get('name')}")

        except rest.ApiException as e:
            log.error(f"[INFLUXDB] - Connection error: {e}")
            self.state = "exit"
            return
        
        except Exception as e:
            log.error(f"[INFLUXDB] - Error: {e}")
            self.state = "exit"
            return
        
        self.influx_org = config['InfluxDB']['INFLUXDB_ORG']
        self.influx_bucket = config['InfluxDB']['INFLUXDB_BUCKET'] 

    """
    #   __  __  ____ _______ _______            _               
    #  |  \/  |/ __ \__   __|__   __|          | |              
    #  | \  / | |  | | | |     | |     ___  ___| |_ _   _ _ __  
    #  | |\/| | |  | | | |     | |    / __|/ _ \ __| | | | '_ \ 
    #  | |  | | |__| | | |     | |    \__ \  __/ |_| |_| | |_) |
    #  |_|  |_|\___\_\ |_|     |_|    |___/\___|\__|\__,_| .__/ 
    #                                                    | |    
    #                                                    |_|    
    """
    
    # MQTT 
    def MQTT_setup(self,config):
        log.debug('[MQTT] - Loading')
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.username_pw_set(config['MQTT Settings']['USER'], config['MQTT Settings']['PASSWORD'])
        
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.on_connect = self.on_connect_MQTT
        
        self.mqtt_sub = str(config['MQTT Topics']['TOPIC_SUBSCRIBE'])
        self.mqtt_targ = str(config['MQTT Topics']['TOPIC_TARGET'])
        self.mqtt_dbg = str(config['MQTT Topics']['TOPIC_DEBUG'])
        

        try:
            self.mqtt_client.connect(config['MQTT Settings']['BROKER'], int(config['MQTT Settings']['PORT']), 60)
        except Exception as e:
            log.error(f'[MQTT] - Connection to broker failed: {e}')
            return
        
        
        try:
            self.mqtt_client.subscribe(config['MQTT Topics']['TOPIC_SUBSCRIBE'])
            log.debug(f"[MQTT] - Sucessufully connected to topic: {config['MQTT Topics']['TOPIC_SUBSCRIBE']}")
        except ValueError as e:
            log.error(f"[MQTT] - Subscription with MQTT topic failed: {e}")
            return
        
        self.mqtt_client.loop_start()
           
    
    def on_connect_MQTT(self, clinet, userdata, flags, rc):

        if rc != mqtt.MQTT_ERR_SUCCESS:
            self.state = "exit"
            log.error(f"[MQTT] - Message not sent: {msg.rc}")
            return
            
        log.info('[MQTT] - Broker connected')
        msg = str(self.DEVICE_ID) + ": handshake connection"
        rc = self.send_msg(self.mqtt_dbg, msg)
        
        
        if rc != mqtt.MQTT_ERR_SUCCESS:
            self.state = "exit"
            log.error(f"[MQTT] - Message not sent: {msg.rc}")
            return
        
        log.debug("[MQTT] - published message to broker")
        
       
       
       
    def idle(self):
        
        pass
    
    """
    #    _____                            _   _               _               _                                      
    #   / ____|                          | | (_)             | |             (_)                                     
    #  | |     ___  _ __  _ __   ___  ___| |_ _  ___  _ __   | |__   __ _ ___ _  ___ ___                             
    #  | |    / _ \| '_ \| '_ \ / _ \/ __| __| |/ _ \| '_ \  | '_ \ / _` / __| |/ __/ __|                            
    #  | |___| (_) | | | | | | |  __/ (__| |_| | (_) | | | | | |_) | (_| \__ \ | (__\__ \                            
    #   \_____\___/|_| |_|_| |_|\___|\___|\__|_|\___/|_| |_| |_.__/ \__,_|___/_|\___|___/                            
    """                                                                                                            
                                                                                                                   
    
    def on_message(self, mqtt_client, userdata, msg):
        log.info('[MQTT] - Reading incoming message...')
        self.mqtt_client.loop_stop()
        
        try:
            msg_dict = json.loads(msg.payload)
            log.debug(f'[MQTT] - Received message: {msg_dict}')
            client_id = msg_dict.get('device_id')
            self.client_mode = msg_dict.get('mode')
            self.msg_payload = msg_dict.get('payload')
            
            if self.CLIENT_ID not in client_id:
                log.warning('[MQTT] - No record match')
                self.client_mode = None
                return
            
            if self.client_mode == CAMERA_MODE: 
                self.state = 'plate_detection' 
                log.debug(f"[CORE] - Plate detection mode")
                return
        
            if self.client_mode == CHARS_MODE: 
                self.state = 'chars_detection'
                log.debug(f"[CORE] - Chars recognition mode")
                return
            
            if self.client_mode == STRING_MODE: 
                self.state = 'string_detection'
                log.debug(f"[CORE] - String evaluation mode")
                return
            
            else: 
                log.debug(f"[MQTT] - Unknown mode {self.client_mode}") 
                self.state = 'idle' 
                self.msg_payload = None
                log.info("[CORE] - Waiting for incoming messages")
            
        except Exception as e:
            log.error(f'[MQTT] - Failed to process message: {e}')
            self.state = 'idle'
        
        
    def send_msg(self, topic_target, message):
        msg = self.mqtt_client.publish(topic_target, message)
        if msg.rc == mqtt.MQTT_ERR_SUCCESS:
            log.debug(f"[MQTT] - Sent message to topic '{topic_target}': {message}")
        else:
            log.warning(f"[MQTT] - Message not sent: {msg.rc}")
        
        return msg.rc
    
    """
    #   _____                                                                _             
    #  |_   _|                                                              (_)            
    #    | |  _ __ ___   __ _  __ _  ___   _ __  _ __ ___   ___ ___  ___ ___ _ _ __   __ _ 
    #    | | | '_ ` _ \ / _` |/ _` |/ _ \ | '_ \| '__/ _ \ / __/ _ \/ __/ __| | '_ \ / _` |
    #   _| |_| | | | | | (_| | (_| |  __/ | |_) | | | (_) | (_|  __/\__ \__ \ | | | | (_| |
    #  |_____|_| |_| |_|\__,_|\__, |\___| | .__/|_|  \___/ \___\___||___/___/_|_| |_|\__, |
    #                          __/ |      | |                                         __/ |
    #                         |___/       |_|                                        |___/ 
    """
    def plate_detection(self):
        log.info('[CORE] - Processing images...')
        self.img = self.base2image(self.msg_payload)
        
        if self.img is None:
            log.warning('[CORE] - No image decoded') 
            self.state = 'idle'
            log.info("[CORE] - Waiting for incoming messages")
            self.mqtt_client.loop_start()
            return
        
        result = self.robo_client.infer(self.img, model_id=self.MODEL_ID)
        
        if result is None:
            log.warning('[CORE] - No plate detected.')
            self.state = 'idle'
            log.info("[CORE] - Waiting for incoming messages")
            self.mqtt_client.loop_start()
            return
        
        predictions = result['predictions']
        best_plate = max(predictions, key=lambda p: p['confidence'])
        
        if self.prediction is None:
            log.debug('[CORE] - New plate detected.')
            self.prediction = best_plate
            self.state = 'idle'
            log.info("[CORE] - Waiting for incoming messages")
            self.mqtt_client.loop_start()
            return

        if self.prediction['width'] > best_plate['width']:
            log.debug('[CORE] - Car leaving ...')
            self.prediction = None
            self.state = 'idle'
            log.info("[CORE] - Waiting for incoming messages")
            self.mqtt_client.loop_start()
            return
        
        
        self.state = 'img_crop'
        
    
    def img_crop(self):
        log.debug('[CORE] - Selecting the plate ...')
        x = self.prediction['x']
        y = self.prediction['y']
        w = self.prediction['width']
        h = self.prediction['height']
        
        L = x - w / 2
        R = x + w / 2
        T = y - h / 2
        B = y + h / 2
        
        self.img = self.img.crop((L, T, R, B))
        
        log.debug('[CORE] - Cropped image created')
        
        self.state = 'chars_detection'
     
        
    def chars_detection(self):
        log.debug('[CORE] - Processing plate...')
        
        def clean_text(text):
            cleaned_text = ''
            for char in text:
                if char.isalnum(): 
                    cleaned_text += char
            return cleaned_text
        
        if self.mode == CHARS_MODE:
            img = self.base2image(self.msg_payload)
            
            if img is None:
                log.warning('[CORE] - No image decoded'); 
                self.state = 'idle'
                log.info("[CORE] - Waiting for incoming messages")
                self.mqtt_client.loop_start()
                return
        
        pipeline = keras_ocr.pipeline.Pipeline()
        
        img = keras_ocr.tools.read(self.img)
        
        predicted_image = pipeline.recognize([img])[0] 
        sorted_res = sorted(predicted_image, key=lambda p: p[1][0][0])  
        merged_red = ''.join([text for text, _ in sorted_res]) 
        cleaned_res = clean_text(merged_red)
        recognized_text = cleaned_res.upper()
        
        log.debug(f"[CORE] - Recognized text: {recognized_text}")
        self.msg_payload = recognized_text
        self.state = 'string_detection'
    
    
    def base2image(self, base64_string):
        img_data = base64.b64decode(base64_string)
        img_array = np.frombuffer(img_data, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        return img
     
     
    #   _____        _                          _             _   _             
    #  |  __ \      | |                        | |           | | (_)            
    #  | |  | | __ _| |_ __ _    _____   ____ _| |_   _  __ _| |_ _  ___  _ __  
    #  | |  | |/ _` | __/ _` |  / _ \ \ / / _` | | | | |/ _` | __| |/ _ \| '_ \ 
    #  | |__| | (_| | || (_| | |  __/\ V / (_| | | |_| | (_| | |_| | (_) | | | |
    #  |_____/ \__,_|\__\__,_|  \___| \_/ \__,_|_|\__,_|\__,_|\__|_|\___/|_| |_|
                                                                              
                                                                              
    
    def string_detection(self):
        log.info(f'[CORE] - Processing STRING_MODE...')
        
        query = f'''
            from(bucket: "{self.influx_bucket}")
            |> range(start: 0) 
            |> filter(fn: (r) => r._measurement == "car_plates")
            |> filter(fn: (r) => r.plate == "{self.msg_payload}")
            |> filter(fn: (r) => r._field == "value")
            |> last()
            '''
            
        try:
            result = self.influx_query_api.query(query=query, org=self.influx_org)
            
            if result:
                log.debug(f'[INFLUXDB] - Record "{self.msg_payload}" found.')
                if result[0].records[0].get_value() == ACTIVE_PLATE:
                    self.store_access_record(self.msg_payload, ACTIVE_PLATE)
                    log.info(f'[INFLUXDB] - Plate "{self.msg_payload}" authorized')
                    self.open_gate()
                    
                else:
                    self.store_access_record(self.msg_payload, DEPRECATED_PLATE)
                    log.info(f'[INFLUXDB] - Plate "{self.msg_payload}" not authorized')
            else:
                log.info(f'[INFLUXDB] - Record "{self.msg_payload}" not found.')

        except Exception as e:
            log.error(f'[INFLUXDB] - Failed to query: {e}')

        log.debug("[CORE] MQTT connection restarted")
        self.mqtt_client.loop_start()
        self.state = "idle" 
        log.info("[CORE] - Waiting for incoming messages")                                              
    
    def store_access_record(self, plate, value):
        log.debug(f'[INFLUXDB] - Writing record: {plate}')
        point = (
                Point("car_plates")
                .tag("plate",plate)
                .field("value", value)
            )
        self.influx_write_api.write(self.influx_bucket, self.influx_org, point)

    def open_gate(self):
        msg = {
            "device_id": self.DEVICE_ID,
            "action": "gate_open"
        }
            
        if self.send_msg(self.mqtt_targ, json.dumps(msg)) == mqtt.MQTT_ERR_SUCCESS:
            log.info('[MQTT] - Sending opening gate..')
        else:
            log.error("[MQTT] - Can't open gate, quitting...")
            self.state = "exit"

    def exit(self):
        log.info("[CORE] - Closing program")
        self.state = 'null'
        
    def run(self):
        state_functions = {
            'idle': self.idle,
            'plate_detection': self.plate_detection,
            'chars_detection': self.chars_detection,
            'string_detection': self.string_detection,
            'img_crop': self.img_crop,
            'exit': self.exit
        }

        while True:
            state_function = state_functions.get(self.state)
            if state_function:
                state_function()
            else:
                log.error(f"[CORE] Unknown state: {self.state}")
                break
            
            
if __name__ == "__main__":
    
    config = configparser.ConfigParser()
    config.read(CONFIG_FILENAME)
    sm = Program()
    
    sm.run()
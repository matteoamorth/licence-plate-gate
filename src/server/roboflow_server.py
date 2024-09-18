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
from influxdb_client import InfluxDBClient, Point, WriteOptions, rest

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
DEBUG = True

# Log
logger = logging.getLogger('LPG-Server')
logger.setLevel(logging.DEBUG)

# File
file_formatter = logging.Formatter('%(asctime)s [%(levelname)s] - %(message)s')
file_handler = logging.FileHandler('plate_recognition_server.log')
file_handler.setFormatter(file_formatter)
file_handler.setLevel(logging.DEBUG)
logger.addHandler(file_handler)

# Console
console_formatter = colorlog.ColoredFormatter('%(log_color)s%(asctime)s [%(levelname)s] - %(name)s - %(message)s',
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
logger.addHandler(console_handler)



# Old debug
#dprint = print if DEBUG else lambda *args, **kwargs: None

logger.info('\n######################################################################\n\nPlate recognition server\n\n######################################################################\n')
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
         
        logger.info('Server init ...')
        
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
        
        self.DEVICE_ID= 'server_01'
        logger.info('DEVICE ID: ' + str(self.DEVICE_ID))
        
        # model 
        logger.debug('Loading Roboflow model')
        self.MODEL_ID = config['Roboflow']['MODEL_ID']
        self.robo_client =  InferenceHTTPClient(
            api_url = config['Roboflow']['API_URL'],
            api_key = config['Roboflow']['API_KEY'])
        
        # database 
        self.influxdb_setup(config)
        
        # connection
        self.MQTT_setup(config)
        
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
            logger.debug('Loading InfluxDB')
            self.influx_client = InfluxDBClient(url=config['InfluxDB']['INFLUXDB_URL'], 
                                                token=config['InfluxDB']['INFLUXDB_TOKEN'],
                                                org=config['InfluxDB']['INFLUXDB_ORG'])
            
            self.influx_write_api = self.influx_client.write_api(write_options=WriteOptions(batch_size=500, 
                                                                                    flush_interval=10_000, 
                                                                                    jitter_interval=2_000, 
                                                                                    retry_interval=5_000))
            
            self.influx_query_api = self.influx_client.query_api()
            t_query = 'buckets()'
            
            result = self.influx_query_api.query(query=t_query)
            
            for table in result:
                for record in table.records:
                    logger.debug(f"Bucket avaiable: {record.values.get('name')}")

        except rest.ApiException as e:
            logger.error(f"Connection error to InfluxDB: {e}")
            self.state = "exit"
            return
        
        except Exception as e:
            logger.error(f"Error: {e}")
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
        logger.debug('Loading MQTT')
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
            logger.error(f'Connection to MQTT broker failed: {e}')
            return
        
        
        try:
            self.mqtt_client.subscribe(config['MQTT Topics']['TOPIC_SUBSCRIBE'])
            logger.debug(f"Sucessufully connected to topic: {config['MQTT Topics']['TOPIC_SUBSCRIBE']}")
        except ValueError as e:
            logger.error(f"Subscription with MQTT topic failed: {e}")
            return
        
        self.mqtt_client.loop_start()
        
        
        
    
    def on_connect_MQTT(self, clinet, userdata, flags, rc):

        if rc != mqtt.MQTT_ERR_SUCCESS:
            self.state = "exit"
            logger.error(f"Message not sent: {msg.rc}")
            return
            
        logger.info('MQTT broker connected')
        msg = str(self.DEVICE_ID) + ": handshake connection"
        rc = self.send_msg(self.mqtt_dbg, msg)
        
        
        if rc != mqtt.MQTT_ERR_SUCCESS:
            self.state = "exit"
            logger.error(f"Message not sent: {msg.rc}")
            return
        
        logger.debug("published message to MQTT broker")
        
       
    def idle(self):
        
        #logger.debug('Server is idle, waiting for messages...')
        self.state = "idle"
        ### end of idle ###
    
    """
    #    _____                            _   _               _               _                                      
    #   / ____|                          | | (_)             | |             (_)                                     
    #  | |     ___  _ __  _ __   ___  ___| |_ _  ___  _ __   | |__   __ _ ___ _  ___ ___                             
    #  | |    / _ \| '_ \| '_ \ / _ \/ __| __| |/ _ \| '_ \  | '_ \ / _` / __| |/ __/ __|                            
    #  | |___| (_) | | | | | | |  __/ (__| |_| | (_) | | | | | |_) | (_| \__ \ | (__\__ \                            
    #   \_____\___/|_| |_|_| |_|\___|\___|\__|_|\___/|_| |_| |_.__/ \__,_|___/_|\___|___/                            
    """                                                                                                            
                                                                                                                   
    
    def on_message(self, mqtt_client, userdata, msg):
        logger.info('Reading incoming MQTT message...')
        
        try:
            msg_dict = json.loads(msg.payload)
            logger.debug(f'Received message: {msg_dict}')
            client_id = msg_dict.get('device_id')
            self.client_mode = msg_dict.get('mode')
            
            if self.CLIENT_ID not in client_id:
                logger.warning('No record match')
                self.client_mode = None
                return
            
            self.mqtt_client.loop_stop() # block mqtt callback 
            self.msg_payload = msg_dict.get('msg')
            
            
            if self.client_mode == CAMERA_MODE: 
                self.state = 'plate_detection' 
                logger.debug(f"Plate detection mode")
                return
            if self.client_mode == CHARS_MODE: 
                self.state = 'chars_detection'
                logger.debug(f"Chars recognition mode")
                return
            if self.client_mode == STRING_MODE: 
                self.state = 'string_detection'
                logger.debug(f"String evaluation mode")
                return
            else: 
                logger.warning('Unknown mode {self.client_mode}') 
                self.state = 'idle'   
            
        except Exception as e:
            logger.error(f'Failed to process message: {e}')
            self.state = 'idle'
        
    def send_msg(self, topic_target, message):
        msg = self.mqtt_client.publish(topic_target, message)
        if msg.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.debug(f"Sent message to topic '{topic_target}': {message}")
        else:
            logger.warning(f"Message not sent: {msg.rc}")
        
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
        logger.info('Processing images...')
        self.img = self.base2image(self.msg_payload)
        
        if self.img is None:
            logger.warning('No image decoded') 
            self.state = 'idle'
            self.mqtt_client.loop_start()
            return
        
        result = self.robo_client.infer(self.img, model_id=self.MODEL_ID)
        
        if result is None:
            logger.warning('No plate detected.')
            self.state = 'idle'
            self.mqtt_client.loop_start()
            return
        
        predictions = result['predictions']
        best_plate = max(predictions, key=lambda p: p['confidence'])
        
        if self.prediction is None:
            logger.debug('New plate detected.')
            self.prediction = best_plate
            self.state = 'idle'
            self.mqtt_client.loop_start()
            return

        if self.prediction['width'] > best_plate['width']:
            logger.debug('Car leaving ...')
            self.prediction = None
            self.state = 'idle'
            self.mqtt_client.loop_start()
            return
        
        
        self.state = 'img_crop'
        
    
    def img_crop(self):
        logger.debug('Selecting the plate ...')
        x = self.prediction['x']
        y = self.prediction['y']
        w = self.prediction['width']
        h = self.prediction['height']
        
        L = x - w / 2
        R = x + w / 2
        T = y - h / 2
        B = y + h / 2
        
        self.img = self.img.crop((L, T, R, B))
        
        logger.debug('Cropped image created')
        
        self.state = 'chars_detection'
     
        
    def chars_detection(self):
        logger.debug('Processing plate...')
        
        if self.mode == CHARS_MODE:
            img = self.base2image(self.msg_payload)
            
            if img is None:
                logger.warning('No image decoded'); 
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

        
        logger.debug("Recognized text: {recognized_text}")
        self.msg_payload = recognized_text
        self.state = 'string_detection'
    
    
    #   _____        _                          _             _   _             
    #  |  __ \      | |                        | |           | | (_)            
    #  | |  | | __ _| |_ __ _    _____   ____ _| |_   _  __ _| |_ _  ___  _ __  
    #  | |  | |/ _` | __/ _` |  / _ \ \ / / _` | | | | |/ _` | __| |/ _ \| '_ \ 
    #  | |__| | (_| | || (_| | |  __/\ V / (_| | | |_| | (_| | |_| | (_) | | | |
    #  |_____/ \__,_|\__\__,_|  \___| \_/ \__,_|_|\__,_|\__,_|\__|_|\___/|_| |_|
                                                                              
                                                                              
    
    def string_detection(self):
        logger.info('Processing STRING_MODE...')
        
        query = 'from(bucket: "{self.influx_bucket}") |> ' \
                'filter(fn: (r) => r["_measurement"] == "plates_registered" and ' \
                'r["plate_number"] == "{self.msg_payload}")'
        try:
            result = self.influx_client.query_api().query(query=query, org=self.influx_org)

            if result:
                logger.debug('Record "{self.msg_payload}" found in InfluxDB.')
                self.store_access_record(self.msg_payload)
                self.open_gate()
            else:
                logger.warning('Record "{self.msg_payload}" not found in InfluxDB.')

        except Exception as e:
            logger.error('Failed to query InfluxDB: {e}')

        self.mqtt_client.loop_start()
        self.state = "idle"
                                                     
    def base2image(self, base64_string):
        img_data = base64.b64decode(base64_string)
        img_array = np.frombuffer(img_data, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        return img
     
    def store_access_record(self, plate):
        logger.debug('writing record on influx {plate}')
        point = Point("accesses").tag("plate_number", plate)
        self.write_api.write(self.influx_bucket, self.influx_org, point)

    def open_gate(self):
        msg = {
            "device_id": self.DEVICE_ID,
            "action": "gate_open"
        }
            
        if self.send_msg(self.mqtt_targ, json.dumps(msg)) == mqtt.MQTT_ERR_SUCCESS:
            logger.info('Sending opening gate..')
        else:
            logger.error("Can't open gate, quitting...")
            self.state = "exit"

    def exit(self):
        logger.info("Closing program")
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
                logger.error(f"Unknown state: {self.state}")
                break
            
            
if __name__ == "__main__":
    sm = Program()
    
    sm.run()
#   _      _ _                    _           
#  | |    (_) |                  (_)          
#  | |     _| |__  _ __ __ _ _ __ _  ___  ___ 
#  | |    | | '_ \| '__/ _` | '__| |/ _ \/ __|
#  | |____| | |_) | | | (_| | |  | |  __/\__ \
#  |______|_|_.__/|_|  \__,_|_|  |_|\___||___/
                                            
                                            
# parsing libraries
import configparser, json, argparse
import numpy as np

# images libraries
import io
from PIL import Image


# images libraries
import keras_ocr
from inference_sdk import InferenceHTTPClient

# influxDB 
from influxdb_client import InfluxDBClient, Point, rest
from influxdb_client.client.write_api import SYNCHRONOUS

# mqtt
import paho.mqtt.client as mqtt

# debug
import logging
import colorlog
import shutil


#   _                     _             _   _   _                 
#  | |                   | |           | | | | (_)                
#  | |     ___   ___ __ _| |   ___  ___| |_| |_ _ _ __   __ _ ___ 
#  | |    / _ \ / __/ _` | |  / __|/ _ \ __| __| | '_ \ / _` / __|
#  | |___| (_) | (_| (_| | |  \__ \  __/ |_| |_| | | | | (_| \__ \
#  |______\___/ \___\__,_|_|  |___/\___|\__|\__|_|_| |_|\__, |___/
#                                                        __/ |    
#                                                       |___/     

STRING_MODE  = 1
CHARS_MODE   = 2
CAMERA_MODE  = 3

DEPRECATED_PLATE = -1
ACTIVE_PLATE = 1
IMG_DIM = 240 
#240


# Log
log = logging.getLogger('LPG-Server')
log.setLevel(logging.DEBUG)

# File
file_formatter = logging.Formatter('%(asctime)s [%(levelname)s]\t%(message)s')
file_handler = logging.FileHandler('log/plate_recognition_server.log')
file_handler.setFormatter(file_formatter)
file_handler.setLevel(logging.DEBUG)
log.addHandler(file_handler)

# Console
console_formatter = colorlog.ColoredFormatter('%(log_color)s%(asctime)s [%(name)s] %(levelname)s\t%(message)s',
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


log.info('[START]    Plate recognition server\n')

def parse_arguments():
    parser = argparse.ArgumentParser(description='Licence-plate-gate server script.')
    parser.add_argument('--config', type=str, default='server_config.ini', help='Configuration file (default: server_config.ini)')
    return parser.parse_args()

############################################################################################################################################

class Roboflow_server:
    
    """
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
    """
    # Setup
    def __init__(self):
         
        log.info('[SETUP]    Server initialization')
        args = parse_arguments()
        config_filename = args.config
        config = configparser.ConfigParser()
        config.read(config_filename)

        if not config.sections():
            log.error(f"[SETUP]    Can't read config file: {config_filename}")
            exit(1)
        
        log.info(f'[SETUP]    Using configuration file: {config_filename}')
        
        
        self.state = 'idle'
        self.msg_next_frame = 0
        self.encoded_img = np.zeros(shape=(IMG_DIM,IMG_DIM,3), dtype=np.uint8)
        self.msg_payload = ""
        self.prediction = None
        self.CLIENT_ID = "edge_device_1234"
        self.busy = True
        
        self.DEVICE_ID = config['Settings']['DEVICE_ID']
        self.CLIENT_LIST = config['Settings']['CLIENT_ID'] ## make it an array
        log.info('[SETUP]    DEVICE ID: ' + str(self.DEVICE_ID))
        
        # model 
        log.debug('[SETUP]    Loading Roboflow model')
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
        
        self.server_free()
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
    # InfluxDB
    def influxdb_setup(self,config): 
        try:
            log.debug('[INFLUXDB] Loading')
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
                    log.debug(f"[INFLUXDB] Bucket avaiable: {record.values.get('name')}")

        except rest.ApiException as e:
            log.error(f"[INFLUXDB] Connection error: {e}")
            self.state = "exit"
            return
        
        except Exception as e:
            log.error(f"[INFLUXDB] Error: {e}")
            self.state = "exit"
            return
        
        self.influx_org = config['InfluxDB']['INFLUXDB_ORG']
        self.influx_bucket = config['InfluxDB']['INFLUXDB_BUCKET'] 

    def store_access_record(self, plate, value):
        log.debug(f'[INFLUXDB] Writing record: {plate}')
        point = (
                Point("car_plates")
                .tag("plate",plate)
                .field("value", value)
            )
        self.influx_write_api.write(self.influx_bucket, self.influx_org, point)


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
        log.debug('[MQTT]     Loading')
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
            log.error(f'[MQTT]     Connection to broker failed: {e}')
            return
        
        
        try:
            self.mqtt_client.subscribe(config['MQTT Topics']['TOPIC_SUBSCRIBE'])
            log.info(f"[MQTT]     Sucessufully connected to topic: {config['MQTT Topics']['TOPIC_SUBSCRIBE']}")
        except ValueError as e:
            log.error(f"[MQTT]     Subscription with MQTT topic failed: {e}")
            return
        
        self.mqtt_client.loop_start()
           
    def on_connect_MQTT(self, clinet, userdata, flags, rc):

        if rc != mqtt.MQTT_ERR_SUCCESS:
            self.state = "exit"
            log.error(f"[MQTT]     Message not sent: {msg.rc}")
            return
            
        log.info('[MQTT]     Broker connected')
        msg = str(self.DEVICE_ID) + ": handshake connection"
        rc = self.send_msg(self.mqtt_dbg, msg)
        
        
        if rc != mqtt.MQTT_ERR_SUCCESS:
            self.state = "exit"
            log.error(f"[MQTT]     Message not sent: {msg.rc}")
            return
        
        log.debug("[MQTT]     published message to broker")
        log.info("[SETUP]    Setup completed")
        log.info("[CORE]     Waiting for incoming messages")
                                                                                                      
    def on_message(self, mqtt_client, userdata, msg):
        if self.busy:
            return
        
        #log.info('[MQTT]     Reading incoming message...')

        try:
            msg = json.loads(msg.payload.decode('utf-8'))

            #log.debug(f'[MQTT]     Received message')
            
            if msg['device_id'] not in self.CLIENT_LIST:
                log.warning('[MQTT]     No record match')
                self.send_msg(self.mqtt_dbg, '[MQTT]     No record match')
                self.state = "idle"
                return
            
            self.CLIENT_ID = msg['device_id']
            
            if msg['mode'] == STRING_MODE: 
                self.mqtt_client.loop_stop()
                self.msg_payload = msg
                self.state = 'string_detection'
                log.debug(f"[CORE]     String evaluation mode")
                self.send_msg(self.mqtt_dbg, f"[CORE]     String evaluation mode")
                return
            
            if msg['mode'] != CAMERA_MODE and msg['mode'] != CHARS_MODE:
                log.debug(f"[MQTT]     Unknown mode {msg['mode']}") 
                self.state = 'idle' 
                self.msg_payload = ""
                log.info("[CORE]     Waiting for incoming messages with known mode")
                self.send_msg(self.mqtt_dbg, "[CORE]     Waiting for incoming messages with known mode")
                return
            
            # full msg reconstruction
            if msg['payload'] == 'END_DATA':
                log.debug("[CORE]     Full image received")
                self.send_msg(self.mqtt_dbg, "[CORE]     Full image received")
                self.server_busy()
                self.msg_payload = Image.fromarray(self.encoded_img, 'RGB')
                self.msg_next_frame = 0
                

                if msg['mode'] == CAMERA_MODE:
                    self.state = 'plate_detection' 
                    log.debug(f"[CORE]     {self.state} mode")
                    self.encoded_img = np.zeros(shape=(IMG_DIM,IMG_DIM,3), dtype=np.uint8)
                    return
                elif msg['mode'] == CHARS_MODE:
                    self.state = 'chars_detection'
                    log.debug(f"[CORE]     {self.state} mode")
                    self.encoded_img = np.zeros(shape=(IMG_DIM,IMG_DIM,3), dtype=np.uint8)
                    return
                else:
                    self.state = 'idle'
                    
                    self.msg_payload = ""
                    self.encoded_img = np.zeros(shape=(IMG_DIM,IMG_DIM,3), dtype=np.uint8)
                    self.server_free()
                    
                    log.info("[CORE]     Waiting for incoming messages with known mode")
                    self.send_msg(self.mqtt_dbg, '[CORE]     Waiting for incoming messages with known mode')
                    return
            
            if self.msg_next_frame != int(msg['fr_n']):
                log.warning(f"[MQTT]     Lost fragment {self.msg_next_frame}")
                self.send_msg(self.mqtt_dbg, f"[MQTT]     Lost fragment {self.msg_next_frame}")
                self.server_busy()
                self.server_free()
                self.msg_next_frame = 0
                
                self.state = 'idle'
                self.msg_payload = ""
                self.encoded_img = np.zeros(shape=(IMG_DIM,IMG_DIM,3), dtype=np.uint8)
                return
                
            fragment = np.array(msg['payload'], dtype=np.uint8)
            self.encoded_img[int(msg['fr_n']), :fragment.shape[0], :] = fragment
            self.msg_next_frame += 1
            
            perc = self.msg_next_frame / IMG_DIM
            terminal_w = shutil.get_terminal_size().columns - 10
            received_step = int(perc * terminal_w)
            bar = "#" * received_step + " " * (terminal_w - received_step)
            print(f"\r[{bar}] {perc * 100:.2f}%", end="")
            
            
            
            

        except Exception as e:
            self.mqtt_client.loop_stop()
            log.error(f"[MQTT]     Failed to process message: {e}")
            self.send_msg(self.mqtt_dbg, f"[MQTT]     Failed to process message: {e}")
            self.state = 'exit'
           
    def send_msg(self, topic_target, message):
        msg = self.mqtt_client.publish(topic_target, message)
        if msg.rc == mqtt.MQTT_ERR_SUCCESS:
            log.debug(f"[MQTT]     Sent message to topic '{topic_target}': {message}")
        else:
            log.warning(f"[MQTT]     Message not sent: {msg.rc}")
        
        return msg.rc
    
    
    """
    #   _____        _                                            _             
    #  |  __ \      | |                                          (_)            
    #  | |  | | __ _| |_ __ _   _ __  _ __ ___   ___ ___  ___ ___ _ _ __   __ _ 
    #  | |  | |/ _` | __/ _` | | '_ \| '__/ _ \ / __/ _ \/ __/ __| | '_ \ / _` |
    #  | |__| | (_| | || (_| | | |_) | | | (_) | (_|  __/\__ \__ \ | | | | (_| |
    #  |_____/ \__,_|\__\__,_| | .__/|_|  \___/ \___\___||___/___/_|_| |_|\__, |
    #                          | |                                         __/ |
    #                          |_|                                        |___/ 
    """
    # Data processing
    def plate_detection(self):
        log.info('[CORE]     Processing images...')
        self.send_msg(self.mqtt_dbg, '[CORE]     Processing images...')
        
        """  if self.msg_payload.size == 0:
            log.warning('[CORE]     No image decoded') 
            self.send_msg(self.mqtt_dbg, '[CORE]     No image decoded')
            self.state = 'idle'
            log.info("[CORE]     Waiting for incoming messages")
            self.server_free()
            return
         """
        #self.msg_payload = Image.open(self.msg_payload)
        self.msg_payload.save("log/openmvcam_image.jpg")
        
        result = self.robo_client.infer(self.msg_payload, model_id=self.MODEL_ID)
        
        if result is None:
            log.warning('[CORE]     No plate detected.')
            self.send_msg(self.mqtt_dbg, '[CORE]     No plate detected.')
            self.state = 'idle'
            self.msg_payload = ""
            log.info("[CORE]     Waiting for incoming messages")
            self.server_free()
            return
        
        predictions = result['predictions']
        
        if not predictions:
            log.debug('[CORE]     No plates detected.')
            self.send_msg(self.mqtt_dbg, '[CORE]     No plates detected.')
            self.state = 'idle'
            self.msg_payload = ""
            log.info("[CORE]     Waiting for incoming messages")
            self.server_free()
            return
        
        
        best_plate = max(predictions, key=lambda p: p['confidence'])

        
        if best_plate['confidence'] < 0.75:
            log.debug('[CORE]     Too low plate confidence.')
            self.send_msg(self.mqtt_dbg, '[CORE]     Too low plate confidence.')
            self.state = 'idle'
            self.msg_payload = ""
            log.info("[CORE]     Waiting for incoming messages")
            self.server_free()
            return
        

        if self.prediction is None:
            log.debug('[CORE]     New plate detected.')
            self.send_msg(self.mqtt_dbg, '[CORE]     New plate detected.')
            self.prediction = best_plate
            self.msg_payload = ""
            self.state = 'idle'
            log.info("[CORE]     Waiting for incoming messages")
            self.server_free()
            return

        if self.prediction['width'] > best_plate['width']:
            log.debug('[CORE]     Car leaving ...')
            self.send_msg(self.mqtt_dbg, '[CORE]     Car leaving ...')
            self.prediction = None
            self.msg_payload = ""
            self.state = 'idle'
            log.info("[CORE]     Waiting for incoming messages")
            self.server_free()
            return
        

        
        self.state = 'img_crop'
        
    def img_crop(self):
        log.debug('[CORE]     Selecting the plate ...')
        self.send_msg(self.mqtt_dbg, '[CORE]     Selecting the plate ...')
        x = self.prediction['x']
        y = self.prediction['y']
        w = self.prediction['width']
        h = self.prediction['height']
        
        L = x - w / 2
        R = x + w / 2
        T = y - h / 2
        B = y + h / 2
        
        #converted_img = Image.fromarray(self.msg_payload)
        #self.msg_payload = converted_img.crop((L, T, R, B))
        self.msg_payload = self.msg_payload.crop((L, T, R, B))
        self.msg_payload.save("log/cropped_image.jpg")
        
        
        byte_arr = io.BytesIO() 
        self.msg_payload.save(byte_arr, format='JPEG')
        byte_arr.seek(0) 
        self.msg_payload = byte_arr
        
        log.debug('[CORE]     Cropped image created')
        self.send_msg(self.mqtt_dbg, '[CORE]     Cropped image created')
        
        self.state = 'chars_detection'
       
    def chars_detection(self):
        log.debug('[CORE]     Processing plate...')
        self.send_msg(self.mqtt_dbg, '[CORE]     Processing plate...')
        
        def clean_text(text):
            cleaned_text = ''
            for char in text:
                if char.isalnum(): 
                    cleaned_text += char
            return cleaned_text
            
        if self.msg_payload == "":
            log.warning('[CORE]     No image decoded'); 
            self.send_msg(self.mqtt_dbg, '[CORE]     No image decoded')
            self.state = 'idle'
            log.info("[CORE]     Waiting for incoming messages")
            self.server_free()
            return
        
        pipeline = keras_ocr.pipeline.Pipeline()
        
        img = keras_ocr.tools.read(self.msg_payload)
        
        predicted_image = pipeline.recognize([img])[0] 
        sorted_res = sorted(predicted_image, key=lambda p: p[1][0][0])  
        merged_red = ''.join([text for text, _ in sorted_res]) 
        cleaned_res = clean_text(merged_red)
        recognized_text = cleaned_res.upper()
        
        log.debug(f"[CORE]     Recognized text: {recognized_text}")
        self.send_msg(self.mqtt_dbg, f"[CORE]     Recognized text: {recognized_text}")
        
        if len(recognized_text) < 6:
            log.warning('[CORE]     String too short'); 
            self.send_msg(self.mqtt_dbg, '[CORE]     String too short')
            self.msg_payload = ""
            self.state = 'idle'
            log.info("[CORE]     Waiting for incoming messages")
            self.server_free()
            return
        
        self.msg_payload = recognized_text
        self.state = 'string_detection'
    
    def string_detection(self):
        log.info(f"[CORE]     Processing STRING_MODE...")
        self.send_msg(self.mqtt_dbg, f"[CORE]     Processing STRING_MODE...")
        
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
                log.debug(f'[INFLUXDB] Record "{self.msg_payload}" found.')
                
                if result[0].records[0].get_value() == ACTIVE_PLATE:
                    self.store_access_record(self.msg_payload, ACTIVE_PLATE)
                    log.info(f'[INFLUXDB] Plate "{self.msg_payload}" authorized')
                    self.send_msg(self.mqtt_dbg, f'[INFLUXDB] Plate "{self.msg_payload}" authorized')
                    self.open_gate()
                    
                else:
                    self.store_access_record(self.msg_payload, DEPRECATED_PLATE)
                    log.info(f'[INFLUXDB] Plate "{self.msg_payload}" not authorized')
                    self.send_msg(self.mqtt_dbg, f'[INFLUXDB] Plate "{self.msg_payload}" not authorized')
            else:
                log.info(f'[INFLUXDB] Record "{self.msg_payload}" not found.')
                self.send_msg(self.mqtt_dbg, f'[INFLUXDB] Record "{self.msg_payload}" not found.')
                self.store_access_record(self.msg_payload, DEPRECATED_PLATE)
                    
        except Exception as e:
            log.error(f'[INFLUXDB] Failed to query: {e}')
            self.send_msg(self.mqtt_dbg, f'[INFLUXDB] Failed to query: {e}')

        log.debug("[CORE] MQTT connection restarting")
        self.state = "idle" 
        self.msg_payload = ""
        self.server_free()
        
        log.info("[CORE]     Waiting for incoming messages")                                            
    
    
    """
    #   _      _  __                     _      
    #  | |    (_)/ _|                   | |     
    #  | |     _| |_ ___  ___ _   _  ___| | ___ 
    #  | |    | |  _/ _ \/ __| | | |/ __| |/ _ \
    #  | |____| | ||  __/ (__| |_| | (__| |  __/
    #  |______|_|_| \___|\___|\__, |\___|_|\___|
    #                          __/ |            
    #                         |___/             
    """                                                                      
    # Lifecycle
    
    def server_busy(self):
        self.busy = True
        msg = {
            "device_id": self.CLIENT_ID,
            "payload": "server_busy"
        }
            
        if self.send_msg(self.mqtt_targ, json.dumps(msg)) == mqtt.MQTT_ERR_SUCCESS:
            log.debug('[MQTT]     Busy')
            self.send_msg(self.mqtt_dbg, '[MQTT]     Busy')
            
        else:
            log.error("[MQTT]     Can't block client")
            self.send_msg(self.mqtt_dbg, "[MQTT]     Can't send messages")
            self.state = "exit"
    
    def server_free(self):
        
        msg = {
            "device_id": self.CLIENT_ID,
            "payload": "server_free"
        }
            
        if self.send_msg(self.mqtt_targ, json.dumps(msg)) == mqtt.MQTT_ERR_SUCCESS:
            log.debug('[MQTT]     Server available')
            self.send_msg(self.mqtt_dbg, '[MQTT]     Server available')
            self.busy = False
        else:
            log.error("[MQTT]     Can't enable client")
            self.send_msg(self.mqtt_dbg, "[MQTT]     Can't send messages")
            self.state = "exit"
            
    def open_gate(self):
        msg = {
            "device_id": self.CLIENT_ID,
            "payload": "gate_open"
        }
            
        if self.send_msg(self.mqtt_targ, json.dumps(msg)) == mqtt.MQTT_ERR_SUCCESS:
            log.info('[MQTT]     Sending opening gate..')
            self.send_msg(self.mqtt_dbg, '[MQTT]     Reading incoming message...')
            
        else:
            log.error("[MQTT]     Can't open gate, quitting...")
            self.send_msg(self.mqtt_dbg, '[MQTT]     Reading incoming message...')
            self.state = "exit"

    def idle(self):
        pass    
    
    def exit(self):
        log.info("[CORE]     Closing program")
        exit(1)
        
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
                self.send_msg(self.mqtt_dbg, '[MQTT]     Unknown state - Closing program')
                break
            
            
if __name__ == "__main__":
    sm = Roboflow_server()
    
    sm.run()
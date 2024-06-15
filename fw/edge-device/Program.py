import sensor, image, time, os, network, utime, pyb, ubinascii, re, json
import functions as fn
from mqtt import MQTTClient
from config import dprint      
from node import Node

CONFIG_FILENAME = "config.ini"
OFFLINE_MODE = 0
STRING_MODE  = 1
CHARS_MODE   = 2
CAMERA_MODE  = 3
DEBUG = True



class Program:
    """    
      _      _  __                     _      
     | |    (_)/ _|                   | |     
     | |     _| |_ ___  ___ _   _  ___| | ___ 
     | |    | |  _/ _ \/ __| | | |/ __| |/ _ \
     | |____| | ||  __/ (__| |_| | (__| |  __/
     |______|_|_| \___|\___|\__, |\___|_|\___|
                             __/ |            
                            |___/             
    """
    
    def __init__(self):
        self.state = "setup"
        self.clock = time.clock()
        self.mode = CAMERA_MODE # default mode
        
        self.id = None
        self.node = None
        self.net_plate = None
        self.labels_plate = None
        self.net_chars = None
        self.labels_chars = None
        
        self.msg_payload = None
        self.in_msg = ""
        self.cf = None

    def mqtt_callback(self, topic, msg):
        dprint("Received message on topic:", topic)
        dprint("Message:", msg.decode('utf-8'))
        
        try:
            msg_dict = json.loads(msg)
            device_id = msg_dict.get('device_id')
            
            if device_id == self.id:
                dprint("Device ID matches")
                self.in_msg = msg_dict.get('action')
                self.state = "decode"
            else:
                dprint(f"Device ID does not match: {device_id} != {self.id}")
                
        except ValueError as e:
            dprint(f"Failed to parse JSON message: {e}")
        
    def dprint(self,*args):
        if self.DEBUG:
            print(*args)
            
    """
      __  __            _     _            _           _        _                                                                                                                                                                              
     |  \/  |          | |   (_)          ( )         | |      | |                                                                                                                                                                             
     | \  / | __ _  ___| |__  _ _ __   ___|/ ___   ___| |_ __ _| |_ ___  ___                                                                                                                                                                   
     | |\/| |/ _` |/ __| '_ \| | '_ \ / _ \ / __| / __| __/ _` | __/ _ \/ __|                                                                                                                                                                  
     | |  | | (_| | (__| | | | | | | |  __/ \__ \ \__ \ || (_| | ||  __/\__ \                                                                                                                                                                  
     |_|  |_|\__,_|\___|_| |_|_|_| |_|\___| |___/ |___/\__\__,_|\__\___||___/                                                                                                                                                                  
                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                               
    """
    
    def setup(self):
        dprint("Starting...")
        
        sensor.reset()                         
        sensor.set_pixformat(sensor.RGB565)    
        sensor.set_framesize(sensor.QVGA)      
        sensor.set_windowing((240, 240))       
        sensor.skip_frames(time=2000)
        
        self.cf = fn.load_config('config.ini')
        self.id = self.cf['Settings']['DEVICE_ID']
        self.mode = self.cf['Settings']['MODE']
        self.DEBUG = self.cf['Settings']['DEBUG']
        
        self.state = 'load_models' if (self.mode != CAMERA_MODE) else 'load_connections'
        
    def load_models(self):
        dprint("Setting up models...")
          
        self.net_plate = fn.load_net_model("trained_plate.tflite", "MODEL_PLATE")
        self.labels_plate = fn.load_label("labels_plate.txt", "LABEL_PLATE")
        
        if not self.net_plate or not self.labels_plate:
            dprint("Error: One or more models/labels failed to load.")
            self.state = "reset"
            return
        
        if self.mode != CHARS_MODE:
            self.net_chars = fn.load_net_model("trained_chars.tflite", "MODEL_CHARS")
            self.labels_chars = fn.load_labels("labels_chars.txt", "LABEL_CHARS")
            
            if not self.net_chars or not self.labels_chars:
                dprint("Error: One or more models/labels failed to load.")
                self.state = "reset"
                return
        
        if self.mode != OFFLINE_MODE:
            self.state = "load_connections"
        else:
            self.state = "load_gpio"
           
    def load_connections(self):
        dprint("Connecting...")
        self.node = Node(   self.cf['WiFI']['WIFI_SSID'], 
                            self.cf['WiFI']['WIFI_PASSWORD'],
                            self.cf['MQTT Settings']['MQTT_SERVER'], 
                            self.cf['MQTT Settings']['MQTT_PORT'],
                            self.cf['MQTT Settings']['MQTT_USER'], 
                            self.cf['MQTT Settings']['MQTT_PASSWORD'],
                            self.cf['MQTT Topics']['TOPIC_DEBUG'],
                            self.cf['TOPIC_DEBUG']['TOPIC_TARGET'],
                            self.cf['TOPIC_DEBUG']['TOPIC_SUBSCRIBE'])
        
        if self.node.connect_wifi():
            self.state = "load_gpio"
            
            dprint("Connected to WIFI. Setting up MQTT...")
            self.node.connect_mqtt()
            self.node.mqtt_client.set_callback(self.mqtt_callback)
            
            # check server status - to be implemented
            """
            self.node.publish_mqtt(self.node.MQTT_TOPIC_DEBUG, "Test")
            dprint("")
            """
            
            return
       
        dprint("Can't connect to WIFI")
        self.mode = OFFLINE_MODE
        self.node = None
        self.state = "load_models"
            
    def load_gpio(self):
        if self.cf['Output']['ACTUATOR']:
            self.pinOut = pyb.Pin(self.cf['Output']['ACTUATOR_OUT_PIN'], pyb.Pin.OUT)
            self.pinClosed = pyb.Pin(self.cf['Output']['ACTUATOR_CLOSED_PIN'], pyb.Pin.IN)
            self.pinOpen = pyb.Pin(self.cf['Output']['ACTUATOR_OPEN_PIN'], pyb.Pin.IN)
            
        self.state = "plate"

    def plate(self):
        dprint("Looking for cars...")
        
        img = sensor.snapshot()
        
        
        # CAMERA_MODE: only images acquired on the device
        if self.mode == CAMERA_MODE:
            self.msg_payload = img.copy()
            self.state = 'img2base64'
            return
        
            
        max_prob_obj = max(self.net_plate.classify(img, min_scale=1.0, scale_mul=0.8, x_overlap=0.5, y_overlap=0.5),
                       key=lambda obj: obj.output()[obj.class_id()],
                       default=None)
        
        # if nothing detected, redirect to other states
        if not max_prob_obj:
            self.state = "idle" if self.mode else "plate"
            self.msg_payload = None
            return
        
        # CHARS_MODE: only plate region is detected on board 
        if self.msg_payload:
            if self.msg_payload[2] <= max_prob_obj.rect()[2]:
                self.msg_payload = img.copy(roi=max_prob_obj.rect())
                self.state = "img2base64" if self.mode == CHARS_MODE else "chars"
                return
            else:
                self.msg_payload = None
                self.state = "idle" if self.state else "plate"
                return
        else:
            self.msg_payload = img.copy(roi=max_prob_obj.rect())    
                
        
        #dprint("Plate at [x=%d,y=%d,w=%d,h=%d]" % max_prob_obj.rect())
        #self.node.publish_mqtt(cf.MQTT_TOPIC_IMAGE, fn.json_rect_string(roi=max_prob_obj.rect()))
        #img.draw_rectangle(max_prob_obj.rect())
   
    def img2base64(self):
        img_bytes = self.msg_payload.compress()
        self.msg_payload = ubinascii.b2a_base64(img_bytes).decode('utf-8')
        self.status = "send_msg"
      
    def chars(self):
        chars_predictions = self.net_chars.classify(self.msg_payload, min_scale=1.0, scale_mul=0.8, x_overlap=0.5, y_overlap=0.5)
        chars_with_positions = []
        
        for char_obj in chars_predictions:
            char_predictions_list = list(zip(self.labels_chars, char_obj.output()))
            dprint(best_prediction)
            
            best_prediction = max(char_predictions_list, key=lambda x: x[1])
            dprint(best_prediction)
            
            if best_prediction[1] > self.cf['Settings']['CONFIDENCE_TH']:
                x, _, _, _ = char_obj.rect()
                chars_with_positions.append((x, best_prediction[0]))

        chars_with_positions.sort(key=lambda item: item[0])
        self.msg_payload = "".join([char for _, char in chars_with_positions])

        if self.msg_payload:
            dprint(f"Recognized plate: {self.msg_payload}")
            self.state = "send_msg" if self.mode != OFFLINE_MODE else "validation"
        
        else:
            dprint("No characters recognized with sufficient confidence")
            self.state = "idle" if self.mode != OFFLINE_MODE else "plate"
        
    def validation(self):
        records = self.cf['Records']['RECORDS']
        if self.msg_payload in records:
            self.state = "action_open"

        self.state = "plate"
     
    def idle(self):
        dprint("Looking for incoming messages...")
        self.node.mqtt_client.check_msg()
        self.state = "plate"

    def decode(self):
        dprint("Decoding msg...")
        
        if(self.in_msg == "reset"):
            self.state = "reset"
            self.in_msg = "" 
            return
        
        if(self.in_msg == "status"):
            self.state = "idle"
            self.in_msg = "" 
            return
        
        if(self.in_msg == "gate_status"):
            self.state = "idle"
            self.in_msg = "" 
            return
        
        if(self.in_msg == "gate_close"):
            self.state = "action_close" 
            self.in_msg = "" 
            return 
        
        if(self.in_msg == "gate_open"):
            self.state = "action_open"  
            self.in_msg = "" 
            return
        
        self.state = "plate"    
    
    def send_msg(self):
        
        msg = {
            "device_id" : self.id,
            "mode" : self.mode,
            "msg"  : self.msg_payload
        }
        
        self.node.publish_mqtt(json.dumps(msg, indent=4))
        time.sleep_ms(50)
        self.msg_payload = None
        self.state = 'plate'
              
    def action_open(self):
        if self.pinOut and self.pinClosed.value():
            self.pinOut.high()
            time.sleep_ms(50)
            self.pinOut.low()
        
        
        
        if self.node.connected:
            self.node.publish_mqtt_devug("gate: 1", qos=0)
            
            
        self.state = "plate"
    
    def action_close(self):
        if self.pinOut and self.pinOpen.value():
            self.pinOut.high()
            time.sleep_ms(50)
            self.pinOut.low()
        
        self.plate_text = ""
        self.in_msg = None
        
        if self.node.connected:
            self.node.publish_mqtt_debug("gate: 0", qos=0)    
            
        self.state = "plate"   
    
    def reset(self):
        dprint("Resetting...")
        self.state = "setup"
        self.clock = time.clock()
        self.mode = CAMERA_MODE # default mode
        
        self.id = None
        self.node = None
        self.net_plate = None
        self.labels_plate = None
        self.net_chars = None
        self.labels_chars = None
        
        self.msg_payload = None
        self.in_msg = ""
        self.cf = None
           
    """
       _____ _        _                              _     _            
      / ____| |      | |                            | |   (_)           
     | (___ | |_ __ _| |_ ___   _ __ ___   __ _  ___| |__  _ _ __   ___ 
      \___ \| __/ _` | __/ _ \ | '_ ` _ \ / _` |/ __| '_ \| | '_ \ / _ \
      ____) | || (_| | ||  __/ | | | | | | (_| | (__| | | | | | | |  __/
     |_____/ \__\__,_|\__\___| |_| |_| |_|\__,_|\___|_| |_|_|_| |_|\___|
                                                                        
                                                                        
    """          
    def run(self):
        while True:
            state_functions = {
                "setup": self.setup,
                "load_models": self.load_models,
                "load_connections": self.load_connections,
                "load_gpio": self.load_gpio,
                "plate": self.plate,
                "img2base64": self.img2base64,
                "chars": self.chars,
                "validation": self.validation,
                "idle": self.idle,
                "decode": self.decode,
                "send_msg": self.send_msg,
                "action_open": self.action_open,
                "action_close": self.action_close,
                "reset": self.reset,
            }
    
            state_function = state_functions.get(self.state)
    
            if state_function:
               state_function()
            else:
                dprint(f"Unknown state: {self.state}")
                break


            dprint(self.clock.fps(), "fps")

"""
  ______       _                            _       _   
 |  ____|     | |                          (_)     | |  
 | |__   _ __ | |_ _ __ _   _   _ __   ___  _ _ __ | |_ 
 |  __| | '_ \| __| '__| | | | | '_ \ / _ \| | '_ \| __|
 | |____| | | | |_| |  | |_| | | |_) | (_) | | | | | |_ 
 |______|_| |_|\__|_|   \__, | | .__/ \___/|_|_| |_|\__|
                         __/ | | |                      
                        |___/  |_|                      
"""
if __name__ == "__main__":
    sm = Program()
    sm.run()

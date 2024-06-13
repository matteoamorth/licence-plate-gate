import sensor, image, time, os, network, utime, pyb, ubinascii
import config as cf
import functions as fn
from mqtt import MQTTClient
from config import dprint      
from node import Node

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
        self.state = "start"
        self.clock = time.clock()
        self.node = None
        self.net_plate = None
        self.labels_plate = None
        self.net_chars = None
        self.labels_chars = None
        self.plate_region = None
        self.plate_text = ""
        self.in_msg = ""    

    def mqtt_callback(self, topic, msg):
        dprint("Received message on topic:", topic)
        dprint("Message:", msg.decode('utf-8'))
        self.in_msg = msg
        self.status = "decode"

    """
      __  __            _     _            _           _        _                                                                                                                                                                              
     |  \/  |          | |   (_)          ( )         | |      | |                                                                                                                                                                             
     | \  / | __ _  ___| |__  _ _ __   ___|/ ___   ___| |_ __ _| |_ ___  ___                                                                                                                                                                   
     | |\/| |/ _` |/ __| '_ \| | '_ \ / _ \ / __| / __| __/ _` | __/ _ \/ __|                                                                                                                                                                  
     | |  | | (_| | (__| | | | | | | |  __/ \__ \ \__ \ || (_| | ||  __/\__ \                                                                                                                                                                  
     |_|  |_|\__,_|\___|_| |_|_|_| |_|\___| |___/ |___/\__\__,_|\__\___||___/                                                                                                                                                                  
                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                               
    """
    
    def start(self):
        dprint("Starting...")
        
        sensor.reset()                         
        sensor.set_pixformat(sensor.RGB565)    
        sensor.set_framesize(sensor.QVGA)      
        sensor.set_windowing((240, 240))       
        sensor.skip_frames(time=2000)
        
        if(cf.ACTUATOR):
            self.pinOut = pyb.Pin(cf.ACTUATOR_OUT_PIN, pyb.Pin.OUT)
            self.pinClosed = pyb.Pin(cf.ACTUATOR_CLOSED_PIN, pyb.Pin.IN)
            self.pinOpen = pyb.Pin(cf.ACTUATOR_OPEN_PIN, pyb.Pin.IN)
            
        self.state = "setup"

    def setup(self):
        dprint("Setting up models...")
        
        self.net_plate = fn.load_net_model("trained_plate.tflite", "MODEL_PLATE")
        self.labels_plate = fn.load_labels("labels_plate.txt", "LABEL_PLATE")
        self.net_chars = fn.load_net_model("trained_chars.tflite", "MODEL_CHARS")
        self.labels_chars = fn.load_labels("labels_chars.txt", "LABEL_CHARS")
 
        if not self.net_plate or not self.labels_plate or not self.net_chars or not self.labels_chars:
            dprint("Error: One or more models/labels failed to load.")
            self.state = "reset"
            return
        
        if cf.CONNECTIONS:
            self.state = "connect_node"
        else:
            self.state = "plate"
      
    def connect_node(self):
        dprint("Connecting...")
        self.node = Node(cf.WIFI_SSID, 
                            cf.WIFI_PASSWORD,
                            cf.MQTT_SERVER, 
                            cf.MQTT_PORT, 
                            cf.MQTT_USER, 
                            cf.MQTT_PASSWORD)
        
        if self.node.connect_wifi():
            self.node.connect_mqtt(cf.HOSTNAME)
            self.node.subscribe_mqtt(cf.MQTT_TOPIC_SUBSCRIBE)
            self.node.mqtt_client.set_callback(self.mqtt_callback)
            dprint("Connected to WIFI")
            self.state = "msg_in"
        else:
            dprint("Can't connect to WIFI")
            self.state = "plate"

    def msg_in(self):
        dprint("Looking for incoming messages...")
        self.node.mqtt_client.check_msg()
        self.state = "plate"

    def decode(self):
        dprint("Decoding...")
        
        if(self.in_msg == "reset"):
            self.state = "reset"
            return
        
        if(self.in_msg == "status"):
            self.state = "plate"
            self.node.publish_mqtt(self.node.MQTT_TOPIC_TARGET, self.node.status())
            return
        
        if(self.in_msg == "gate_status"):
            self.state = "plate"
            self.node.publish_mqtt(self.node.MQTT_TOPIC_TARGET, "Gate : %d" % self.pinClosed.value())
            return
        
        if(self.in_msg == "gate_close"):
            self.state = "action_close"  
            return 
        
        if(self.in_msg == "gate_open"):
            self.state = "action_open"   
            return
        
        self.state = "plate"

    def reset(self):
        dprint("Resetting...")
        self.state = "start"
        self.clock = time.clock()
        self.node = None
        self.net_plate = None
        self.labels_plate = None
        self.net_chars = None
        self.labels_chars = None
        self.plate_region = None
        self.plate_text = ""
        self.in_msg = ""

    def plate(self):
        dprint("Looking for cars...")
        
        img = sensor.snapshot()
        
        if cf.ONLY_CAMERA:
            self.plate_region = img.copy()
            self.state = "img2base64"
            return
  
            
        max_prob_obj = max(self.net_plate.classify(img, min_scale=1.0, scale_mul=0.8, x_overlap=0.5, y_overlap=0.5),
                       key=lambda obj: obj.output()[obj.class_id()],
                       default=None)
        
        if not max_prob_obj:
            self.state = "msg_in" if self.node.get_field("connected") else "plate"
            self.plate_region = None
            return
        
        dprint("Plate at [x=%d,y=%d,w=%d,h=%d]" % max_prob_obj.rect())
        self.node.publish_mqtt(cf.MQTT_TOPIC_IMAGE, fn.json_rect_string(roi=max_prob_obj.rect()))
            
        img.draw_rectangle(max_prob_obj.rect())
            
        if self.plate_region:
            if self.plate_region[2] <= max_prob_obj.rect()[2]:
                self.plate_region = img.copy(roi=max_prob_obj.rect())
                self.state = "chars"
                return
            else:
                self.plate_region = None
                self.state = "msg_in" if self.node.get_field("connected") else "plate"
        else:
            self.plate_region = img.copy(roi=max_prob_obj.rect())
             
    def chars(self):
        self.plate_text = ""
        chars_predictions = self.net_chars.classify(self.plate_region, min_scale=1.0, scale_mul=0.8, x_overlap=0.5, y_overlap=0.5)
        chars_with_positions = []
        
        for char_obj in chars_predictions:
            char_predictions_list = list(zip(self.labels_chars, char_obj.output()))
            dprint(best_prediction)
            
            best_prediction = max(char_predictions_list, key=lambda x: x[1])
            dprint(best_prediction)
            
            if best_prediction[1] > cf.CONFIDENCE_TH:
                x, _, _, _ = char_obj.rect()
                chars_with_positions.append((x, best_prediction[0]))

        chars_with_positions.sort(key=lambda item: item[0])
        self.plate_text = "".join([char for _, char in chars_with_positions])

        if self.plate_text:
            dprint(f"Recognized plate: {self.plate_text}")
            self.state = "validation"
        else:
            dprint("No characters recognized with sufficient confidence")
            self.state = "msg_in" if self.node.get_field("connected") else "plate"
            
    def validation(self):
        if self.node.connected:
            self.node.publish_mqtt(cf.MQTT_TOPIC_TARGET, "plate_string : {self.plate_text}", qos=0)
            self.state = "msg_in"
            time.sleep_ms(50)
            return
        
        # offline check
        if self.plate_text in cf.RECORDS:
            self.state = "action_open"
    
    def action_open(self):
        if cf.ACTUATOR and self.pinClosed.value():
            self.pinOut.high()
            time.sleep_ms(50)
            self.pinOut.low()
        
        self.plate_text = ""
        self.plate_region = None
        
        if self.node.connected:
            self.node.publish_mqtt(cf.MQTT_TOPIC_TARGET, "gate: 1", qos=0)
            
            
        self.state = "msg_in" if self.node.get_field("connected") else "plate"
    
    def action_close(self):
        if cf.ACTUATOR and self.pinOpen.value():
            self.pinOut.high()
            time.sleep_ms(50)
            self.pinOut.low()
        
        self.plate_text = ""
        self.plate_region = None
        
        if self.node.connected:
            self.node.publish_mqtt(cf.MQTT_TOPIC_TARGET, "gate: 0", qos=0)     
    
    def img2base64(self):
        img_bytes = self.plate_region.compress()
        img_base64 = ubinascii.b2a_base64(img_bytes).decode('utf-8')
        self.node.publish_mqtt(cf.MQTT_TOPIC_IMAGE, img_base64)
        self.status = "msg_in"
        
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
                "start": self.start,
                "setup": self.setup,
                "connect_node": self.connect_node,
                "msg_in": self.msg_in,
                "decode": self.decode,
                "reset": self.reset,
                "plate": self.plate,
                "chars": self.chars,
                "validation": self.validation,
                "action_open": self.action_open,
                "action_close": self.action_close,
                "only_camera": self.img2base64
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

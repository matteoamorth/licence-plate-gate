import paho.mqtt.client as mqtt
import numpy as np
import cv2
import base64
from influxdb_client import InfluxDBClient, Point, WriteOptions

# MQTT settings
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_IMAGE = "cam_target"
MQTT_TOPIC_TARGET = "plate_check"
MQTT_TOPIC_DEBUG_INCOMING = ""
MQTT_TOPIC_DEBUG_OUTPUT = ""

# INFLUXDB
INFLUXDB_URL = "http://localhost:8086"
INFLUXDB_TOKEN = "xxx"
INFLUXDB_ORG = "xxx"
INFLUXDB_BUCKET = "plate_records"

class ServerStateMachine:
    def __init__(self):
        self.state = "start"
        self.img = None
        self.plate_region = None
        self.client = mqtt.Client()
        self.client.on_message = self.on_message
        self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
        self.client.subscribe(MQTT_TOPIC_IMAGE)
        self.client.loop_start()
        self.influx_client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN)
        self.write_api = self.influx_client.write_api(write_options=WriteOptions(batch_size=500, flush_interval=10_000, jitter_interval=2_000, retry_interval=5_000))

        
        ## models loading ...
        
    def on_message(self, client, userdata, msg):
        try:
            
            ## need to implement logics to differentiate messages and images
            
            img_data = base64.b64decode(msg.payload)
            np_arr = np.frombuffer(img_data, np.uint8)
            self.img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            self.state == "plate_detection"

        except Exception as e:
            print(f"Failed to process image: {e}")

    def detect_plate(self, img):
        max_prob_obj = max(self.net_plate.classify(img, min_scale=1.0, scale_mul=0.8, x_overlap=0.5, y_overlap=0.5),
                       key=lambda obj: obj.output()[obj.class_id()],
                       default=None)
        
        if not max_prob_obj:
            self.state = "msg_in" if self.node.get_field("connected") else "plate"
            self.plate_region = None
            return
        
        dprint("Plate at [x=%d,y=%d,w=%d,h=%d]" % max_prob_obj.rect())
            
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
            
        

    def recognize_chars(self, img, roi):
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
        # control with database
        return

    def store_to_influx(self, plate_text):
        
        # check if correct
        
        point = Point("features").field("plate_text", plate_text)
        self.write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=point)

    def run(self):
        
        ## remove states uneccessary
        
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

if __name__ == "__main__":
    state_machine = ServerStateMachine()
    state_machine.run()

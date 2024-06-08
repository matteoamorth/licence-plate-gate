import sensor, image, time, os,  network, utime
import config as cf
import functions as fn
# import tf, uos, gc
from mqtt import MQTTClient
from config import dprint      
from node import Node

"""
   _____      _                
  / ____|    | |               
 | (___   ___| |_ _   _ _ __   
  \___ \ / _ \ __| | | | '_ \  
  ____) |  __/ |_| |_| | |_) | 
 |_____/ \___|\__|\__,_| .__/  
                       | |     
                       |_|     
"""     

# Device 
clock = time.clock()

# Camera  
sensor.reset()                         
sensor.set_pixformat(sensor.RGB565)    
sensor.set_framesize(sensor.QVGA)      
sensor.set_windowing((240, 240))       
sensor.skip_frames(time=2000) 

# Connections                                                   
if cf.CONNECTIONS:
    node = Node(cf.WIFI_SSID, 
                cf.WIFI_PASSWORD,
                cf.MQTT_SERVER, 
                cf.MQTT_PORT, 
                cf.MQTT_USER, 
                cf.MQTT_PASSWORD)

    if(node.connect_wifi()):
        node.connect_mqtt(cf.HOSTNAME)
        node.subscribe_mqtt(cf.MQTT_TOPIC_LISTENER)
         

# Neural networks
net_plate = fn.load_net_model("trained_plate.tflite", "MODEL_PLATE")
labels_plate = fn.load_labels("labels_plate.txt", "LABEL_PLATE")
net_chars = fn.load_net_model("trained_chars.tflite", "MODEL_CHARS")
labels_chars = fn.load_labels("labels_chars.txt", "LABEL_CHARS")


"""
   _____               
  / ____|              
 | |     ___  _ __ ___ 
 | |    / _ \| '__/ _ \
 | |___| (_) | | |  __/
  \_____\___/|_|  \___|
                                             
"""
while True:
    clock.tick()
        
    if time.time() % 2 < 0.1:
        node.mqtt_client.check_msg()
    
    
    img = sensor.snapshot()

    for obj in net_plate.classify(img, min_scale=1.0, scale_mul=0.8, x_overlap=0.5, y_overlap=0.5):
        
        dprint("Plate at [x=%d,y=%d,w=%d,h=%d]" % obj.rect())
        node.publish_mqtt(cf.MQTT_TOPIC_PLATE,fn.json_rect_string(roi=obj.rect()))
        
        """
        Next to be done:
        - save width and lenght of plate in a temporary variable
        - save a new width and lenght of plate
        - compare if dimensions are equal or bigger than previous sample
        - perform controls on charset
        """
        img.draw_rectangle(obj.rect())

        plate_region = img.copy(roi=obj.rect())
        plate_region = plate_region.resize(300, 300)

        # more filters
        #threshold = plate_region.get_histogram().get_threshold().value()
        #plate_region.binary([(threshold, 255)], invert=True)

        plate_text = ""
        chars_predictions = net_chars.classify(plate_region, min_scale=1.0, scale_mul=0.8, x_overlap=0.5, y_overlap=0.5)
        chars_with_positions = []
        
        for char_obj in chars_predictions:
            char_predictions_list = list(zip(labels_chars, char_obj.output()))
            dprint(best_prediction)
            
            best_prediction = max(char_predictions_list, key=lambda x: x[1])
            dprint(best_prediction)
            
            if best_prediction[1] > cf.CONFIDENCE_TH:
                x, _, _, _ = char_obj.rect()
                chars_with_positions.append((x, best_prediction[0]))


        chars_with_positions.sort(key=lambda item: item[0])
        plate_text = "".join([char for _, char in chars_with_positions])

        if plate_text:
            dprint(f"Recognized plate: {plate_text}")
            node.publish_mqtt(cf.MQTT_TOPIC_TARGET, "plate_string : {plate_text}", qos=0)
        else:
            dprint("No characters recognized with sufficient confidence")
            node.publish_mqtt(cf.MQTT_TOPIC_TARGET, "{plate_string : 00000}", qos=0)

    dprint(clock.fps(), "fps")

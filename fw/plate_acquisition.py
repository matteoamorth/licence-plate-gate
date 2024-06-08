import sensor, image, time, os, tf, uos, gc, network
from umqtt.simple import MQTTClient

wifi_ssid = "w"
wifi_password = "w"

mqtt_server = "mqtt.example.com"
mqtt_port = 1883
mqtt_user = "usr"
mqtt_password = "psw"
mqtt_topic_debug = "cam_debug"
mqtt_topic_target = "cam_target"
mqtt_topic_plate = "plate_pos"



""""
   _____                            _   _                 
  / ____|                          | | (_)                
 | |     ___  _ __  _ __   ___  ___| |_ _  ___  _ __  ___ 
 | |    / _ \| '_ \| '_ \ / _ \/ __| __| |/ _ \| '_ \/ __|
 | |___| (_) | | | | | | |  __/ (__| |_| | (_) | | | \__ \
  \_____\___/|_| |_|_| |_|\___|\___|\__|_|\___/|_| |_|___/
"""                                                        
                                                          
wifi.connect(wifi_ssid, wifi_password)

while not wifi.isconnected():
    time.sleep_ms(50)

ip_address = wifi.ifconfig()[0]
subnet_mask = wifi.ifconfig()[1]
gateway_address = wifi.ifconfig()[2]
dns_server = wifi.ifconfig()[3]

print("Connected to Wi-Fi")
print("IP Address:", ip_address)
print("Subnet Mask:", subnet_mask)
print("Gateway Address:", gateway_address)
print("DNS Server:", dns_server)

client = MQTTClient("openmv_client", mqtt_server, port=mqtt_port, user=mqtt_user, password=mqtt_password)
client.connect()


"""
   _____                                          _               
  / ____|                                        | |              
 | |     __ _ _ __ ___   ___ _ __ __ _   ___  ___| |_ _   _ _ __  
 | |    / _` | '_ ` _ \ / _ \ '__/ _` | / __|/ _ \ __| | | | '_ \ 
 | |___| (_| | | | | | |  __/ | | (_| | \__ \  __/ |_| |_| | |_) |
  \_____\__,_|_| |_| |_|\___|_|  \__,_| |___/\___|\__|\__,_| .__/ 
                                                           | |    
                                                           |_|    
"""
sensor.reset()                         
sensor.set_pixformat(sensor.RGB565)    
sensor.set_framesize(sensor.QVGA)      
sensor.set_windowing((240, 240))       
sensor.skip_frames(time=2000)          




"""
  _                     _                       _      _     
 | |                   | |                     | |    | |    
 | |     ___   __ _  __| |  _ __ ___   ___   __| | ___| |___ 
 | |    / _ \ / _` |/ _` | | '_ ` _ \ / _ \ / _` |/ _ \ / __|
 | |___| (_) | (_| | (_| | | | | | | | (_) | (_| |  __/ \__ \
 |______\___/ \__,_|\__,_| |_| |_| |_|\___/ \__,_|\___|_|___/                                                             
                                                             
"""

# targa
try:
    net_plate = tf.load("trained_plate.tflite", load_to_fb=uos.stat('trained_plate.tflite')[6] > (gc.mem_free() - (64*1024)))
    labels_plate = [line.rstrip('\n') for line in open("labels_plate.txt")]
except Exception as e:
    client.publish(mqtt_topic_debug, f'Failed to load plate model or labels: {e}\n')
    raise Exception(f'Failed to load plate model or labels: {e}\n')

# caratteri
try:
    net_chars = tf.load("trained_chars.tflite", load_to_fb=uos.stat('trained_chars.tflite')[6] > (gc.mem_free() - (64*1024)))
    labels_chars = [line.rstrip('\n') for line in open("labels_chars.txt")]
except Exception as e:
    client.publish(mqtt_topic_debug, f'Failed to load character model or labels: {e}\n')
    raise Exception(f'Failed to load character model or labels: {e}\n')

confidence_th = 0.75
clock = time.clock()


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
    img = sensor.snapshot()

    # Rileva la targa
    for obj in net_plate.classify(img, min_scale=1.0, scale_mul=0.8, x_overlap=0.5, y_overlap=0.5):
        print("**********\nPlate at [x=%d,y=%d,w=%d,h=%d]" % obj.rect())
        client.publish(mqtt_topic_plate, "Plate at [x=%d,y=%d,w=%d,h=%d]" % obj.rect())
        
        img.draw_rectangle(obj.rect())

        plate_region = img.copy(roi=obj.rect())
        plate_region = plate_region.resize(300, 300)

        # Filtra opzionalmente le targhe
        #threshold = plate_region.get_histogram().get_threshold().value()
        #plate_region.binary([(threshold, 255)], invert=True)

        plate_text = ""
        chars_predictions = net_chars.classify(plate_region, min_scale=1.0, scale_mul=0.8, x_overlap=0.5, y_overlap=0.5)

        chars_with_positions = []

        for char_obj in chars_predictions:
            char_predictions_list = list(zip(labels_chars, char_obj.output()))

            best_prediction = max(char_predictions_list, key=lambda x: x[1])

            if best_prediction[1] > confidence_th:
                x, _, _, _ = char_obj.rect()
                chars_with_positions.append((x, best_prediction[0]))


        chars_with_positions.sort(key=lambda item: item[0])
        plate_text = "".join([char for _, char in chars_with_positions])

        if plate_text:
            print(f"Recognized plate: {plate_text}")
            client.publish(mqtt_topic_target, plate_text)
        else:
            print("No characters recognized with sufficient confidence")
            client.publish(mqtt_topic_target, "00000")

    print(clock.fps(), "fps")

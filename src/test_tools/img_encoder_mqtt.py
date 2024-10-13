import paho.mqtt.client as mqtt
import time
import json
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connessione al broker MQTT riuscita!")
        
        topic_publish = "test/cam_target"
        message = "test msg from img_encoder_mqtt"
        result = client.publish(topic_publish, message)
        
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"Messaggio inviato al topic '{topic_publish}': {message}")
        else:
            print(f"Errore nell'invio del messaggio: {result.rc}")
        
        # topic subscription
        topic_subscribe = 'test/cam_target'
        print(f"Sottoscrizione al topic: {topic_subscribe}")
        client.subscribe(topic_subscribe)
    else:
        print(f"Connessione al broker MQTT fallita con codice di ritorno {rc}")



client = mqtt.Client()
client.username_pw_set("usr", "psw")

topic_publish = "test/cam_target"
topic_subscribe = "test/cam_target"
client.on_connect = on_connect
fragment_size = 16384 #8192 #4096 #1024 2048
device_id = 'edge_device_123'
mode = 3

######################################################
with open("img/plate.jpg",'rb') as file:
    filecontent = file.read()
######################################################

img = bytearray(filecontent)



try:
    # broker connection
    client.connect("localhost", 1883, 60)
    
    # send image to subscribed topic:
    print("sending image")
    topic_publish = "test/cam_target"
    
    for i in range(0, len(img), fragment_size):
        fragment = img[i:i + fragment_size]
        
        
        message = {
            "device_id": device_id,
            "mode": mode,
            "payload": fragment 
        }
        
        # Invia il messaggio
        client.publish(topic_subscribe, json.dumps(message))
        print(f"Inviato frammento di lunghezza {len(fragment)}")
        time.sleep(0.5)
    # Invia un messaggio di fine trasmissione
    end_message = {
        "device_id": device_id,
        "mode": mode,
        "payload": "END_DATA"
    }
    result = client.publish(topic_subscribe, json.dumps(end_message))
    print("Invio completato.")
    
    
    
        
    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        print(f"Messaggio inviato al topic '{topic_publish}'")
    else:
        print(f"Errore nell'invio del messaggio: {result.rc}")
        
    
except KeyboardInterrupt:
    print("Chiusura del client MQTT...")
    client.disconnect()
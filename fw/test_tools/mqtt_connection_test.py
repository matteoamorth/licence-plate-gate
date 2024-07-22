import paho.mqtt.client as mqtt

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connessione al broker MQTT riuscita!")
    else:
        print(f"Connessione al broker MQTT fallita con codice di ritorno {rc}")

client = mqtt.Client()
client.username_pw_set("usr", "psw")

client.on_connect = on_connect

try:
    client.connect("localhost", 1883, 60)
    
    
    topic_subscribe = 'cam_target'
    print(f"Subscribing to topic: {topic_subscribe}")
    client.subscribe(topic_subscribe)
    client.loop_forever()
    
except KeyboardInterrupt:
    print("Chiusura del client MQTT...")
    client.disconnect()

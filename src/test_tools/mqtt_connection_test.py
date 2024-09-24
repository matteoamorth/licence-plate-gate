import paho.mqtt.client as mqtt

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connessione al broker MQTT riuscita!")
        
        topic_publish = "test/topic"
        message = "test msg from util"
        result = client.publish(topic_publish, message)
        
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"Messaggio inviato al topic '{topic_publish}': {message}")
        else:
            print(f"Errore nell'invio del messaggio: {result.rc}")
        
        # topic subscription
        topic_subscribe = 'cam_target'
        print(f"Sottoscrizione al topic: {topic_subscribe}")
        client.subscribe(topic_subscribe)
    else:
        print(f"Connessione al broker MQTT fallita con codice di ritorno {rc}")

def on_message(client, userdata, msg):
    print(f"Messaggio ricevuto su {msg.topic}: {msg.payload.decode()}")

# Config MQTT client 
client = mqtt.Client()
client.username_pw_set("usr", "psw")

client.on_connect = on_connect
client.on_message = on_message

try:
    # broker connection
    client.connect("localhost", 1883, 60)
    
    client.loop_forever()
    
except KeyboardInterrupt:
    print("Chiusura del client MQTT...")
    client.disconnect()

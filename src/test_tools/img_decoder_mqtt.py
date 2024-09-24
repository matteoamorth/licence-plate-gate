import paho.mqtt.client as mqtt
import json
import io
from PIL import Image


received_data = bytearray()
image_complete = False
assembled_image = None  


def on_connect(client, userdata, flags, rc):
    print(f"Connesso con codice: {rc}")
    client.subscribe("test/cam_target")

def on_message(client, userdata, msg):
    global received_data, image_complete, assembled_image

    message = json.loads(msg.payload.decode())
    
    if message['payload'] == "END":
        image_complete = True
        print("Ricezione completata.")
        return

    fragment = bytes.fromhex(message['payload'])
    received_data.extend(fragment) 
    print(f"Ricevuto frammento di lunghezza {len(fragment)}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message


client.connect("localhost", 1883, 60)


client.loop_start()


while not image_complete:
    pass


image_data = io.BytesIO(received_data)
assembled_image = Image.open(image_data)  
assembled_image.save("received_image.jpg")
print("Image saved.")


client.loop_stop()
client.disconnect()

assembled_image.show()

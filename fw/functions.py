import config, uos, gc, tf, json
from config import dprint 
import config as cf



def mqtt_callback(topic, msg):
    dprint("Received message on topic: ", topic)
    dprint("Message: ", msg)
    if(msg == "registered"):
        dprint("perform function")
        

# neural network functions
def load_net_model(model_path, element):
    try:
        model = tf.load(model_path, load_to_fb=uos.stat(model_path)[6] > (gc.mem_free() - (64*1024)))
        setattr(config, element, True)
        return model
    except Exception as e:
        config.CLIENT.publish(config.MQTT_TOPIC_DEBUG, f'Failed to load {element}: {e}\n', qos=0)
        raise Exception(f'Failed to load {element}: {e}\n')

def load_label(label_path, element):
    try:
        labels_plate = [line.rstrip('\n') for line in open(label_path)]
        setattr(config, element, True)
        return labels_plate
    except Exception as e:
        config.CLIENT.publish(config.MQTT_TOPIC_DEBUG, f'Failed to load {element}: {e}\n', qos=0)
        raise Exception(f'Failed to load {element}: {e}\n')



# utility
def json_rect_string(plate_rect):
    plate_data = {
        "plate_x": plate_rect[0],
        "plate_y": plate_rect[1],
        "plate_w": plate_rect[2],
        "plate_h": plate_rect[3]
    }
    
    return json.dumps(plate_data)
import config, uos, gc, tf, json
from config import dprint 
import config as cf


# configuration utilities
def parse_value(value):
    value = value.strip()
    if value.lower() == 'true':
        return True
    elif value.lower() == 'false':
        return False
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value.strip('"').strip("'")

def load_config(filename):
    config = {}
    current_section = None
    with open(filename, 'r') as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith(';'):
                continue
            if line.startswith('[') and line.endswith(']'):
                current_section = line[1:-1].strip()
                config[current_section] = {}
            elif '=' in line and current_section is not None:
                key, value = line.split('=', 1)
                key = key.strip()
                value = parse_value(value)
                config[current_section][key] = value
    return config

# neural network functions
def load_net_model(obj, model_path, element):
    try:
        model = tf.load(model_path, load_to_fb=uos.stat(model_path)[6] > (gc.mem_free() - (64*1024)))
        return model
    except Exception as e:
        dprint(f"Error: {element} failed to load. Exception: {e}")
        obj.state = "exit"
        return None

def load_label(label_path, element):
    try:
        labels_plate = [line.rstrip('\n') for line in open(label_path)]
        return labels_plate
    except Exception as e:
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
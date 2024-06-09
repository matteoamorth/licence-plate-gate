# wifi settings
WIFI_SSID = "w"
WIFI_PASSWORD = "w"

# mqtt settings
HOSTNAME = "openmv_client"
MQTT_SERVER = "mqtt.example.com"
MQTT_PORT = 1883
MQTT_USER = "openmv_client"
MQTT_PASSWORD = "your_mqtt_password"

# topics
MQTT_TOPIC_TARGET = "cam_target"
MQTT_TOPIC_PLATE = "plate_pos"
MQTT_TOPIC_DEBUG = "cam_debug"
MQTT_TOPIC_PUBLISHER = ""
MQTT_TOPIC_SUBSCRIBE = "plate_check"

# settings 
DEBUG = True
CONNECTIONS = True # set True to work with external server, False to work local
CONFIDENCE_TH = 0.75
ACTUATOR = True
ACTUATOR_OUT_PIN = "P6"
ACTUATOR_CLOSED_PIN = "P7"
ACTUATOR_OPEN_PIN = "P8"

# plates (offline usage)
RECORDS = ("XX345TT", "AB123CD", "LS000UT")

# macros
dprint = print if DEBUG else lambda *args, **kwargs: None
HOSTNAME = "openmv_client"
WIFI_SSID = "w"
WIFI_PASSWORD = "w"

MQTT_SERVER = "mqtt.example.com"
MQTT_PORT = 1883
MQTT_USER = "your_mqtt_username"
MQTT_PASSWORD = "your_mqtt_password"
MQTT_TOPIC_DEBUG = "cam_debug"
MQTT_TOPIC_TARGET = "cam_target"
MQTT_TOPIC_PLATE = "plate_pos"

CONFIDENCE_TH = 0.75

# topic listener
MQTT_TOPIC_LISTENER = "plate_check"

# enable print 
DEBUG = True
CONNECTIONS = True

dprint = print if DEBUG else lambda *args, **kwargs: None
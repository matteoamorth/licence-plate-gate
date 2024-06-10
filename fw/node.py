import json
import config
import network, time, utime
from config import dprint
from mqtt import MQTTClient

class Node:
    
    """"
      _      _  __                     _      
     | |    (_)/ _|                   | |     
     | |     _| |_ ___  ___ _   _  ___| | ___ 
     | |    | |  _/ _ \/ __| | | |/ __| |/ _ \
     | |____| | ||  __/ (__| |_| | (__| |  __/
     |______|_|_| \___|\___|\__, |\___|_|\___|
                             __/ |            
                            |___/             
    """
    def __init__(self, wifi_ssid, wifi_password, mqtt_server, mqtt_port, mqtt_user, mqtt_password):
        """
        Initializes a new Node object with the specified parameters.

        Args:
            wifi_ssid (str): Wi-Fi network SSID.
            wifi_password (str): Wi-Fi network password.
            mqtt_server (str): MQTT server address.
            mqtt_port (int): MQTT server port.
            mqtt_user (str): MQTT username for authentication.
            mqtt_password (str): MQTT password for authentication.
        """
        
        self.wifi = ""
        self.connected = False
        self.wifi_ssid = wifi_ssid
        self.wifi_password = wifi_password
        
        self.mqtt_client = ""
        self.mqtt_server = mqtt_server
        self.mqtt_port = mqtt_port
        self.mqtt_user = mqtt_user
        self.mqtt_password = mqtt_password
        
        # default from config file
        self.MQTT_TOPIC_DEBUG = config.MQTT_TOPIC_DEBUG
        self.MQTT_TOPIC_TARGET = config.MQTT_TOPIC_TARGET
        self.MQTT_TOPIC_IMAGE = config.MQTT_TOPIC_IMAGE
        self.MQTT_TOPIC_SUBSCRIBE = config.MQTT_TOPIC_SUBSCRIBE
        
        # before loading set to false
        self.MODEL_PLATES = False
        self.MODEL_CHARS = False
        self.LABEL_PLATES = False
        self.LABEL_CHARS = False
    
    
    """
                                                   
         /\                                        
        /  \   ___ ___ ___  ___ ___  ___  _ __ ___ 
       / /\ \ / __/ __/ _ \/ __/ __|/ _ \| '__/ __|
      / ____ \ (_| (_|  __/\__ \__ \ (_) | |  \__ \
     /_/    \_\___\___\___||___/___/\___/|_|  |___/
                                                   
                                                   
    """
    
    def set_mqtt(self, mqtt_client):
        """Saves connection in object

        Args:
            mqtt_client (Network connection): MQTT object
        """
        self.mqtt_client = mqtt_client
    
    def set_topic(self,topic_field,value):
        """Set a new value to MQTT topics

        Args:
            topic: Topic to be changed
            value: topic name
        """
        setattr(self, topic_field, value)

    def get_field(self, field):
        """Get the value of the specified field

        Args:
            field (str): Field to retrieve.

        Returns:
            str: Value of the field.
        """
        return getattr(self, field)
    
    """
      __  __      _   _               _     
     |  \/  |    | | | |             | |    
     | \  / | ___| |_| |__   ___   __| |___ 
     | |\/| |/ _ \ __| '_ \ / _ \ / _` / __|
     | |  | |  __/ |_| | | | (_) | (_| \__ \
     |_|  |_|\___|\__|_| |_|\___/ \__,_|___/
                                                                                  
    """
    def connect_wifi(self):
        if config.CONNECTIONS:
            self.wifi = network.WINC()
            self.wifi.connect(self.wifi_ssid,self.wifi_password)
            
            start_time = utime.ticks_ms()
            
            while not self.wifi.isconnected():
                if utime.ticks_diff(utime.ticks_ms(), start_time) >= 10000: 
                    self.connected = False
                    break
                time.sleep_ms(50)
            else:
                self.connected = True
                dprint(self.connection_info())
        
        return self.connected
    
    def connect_mqtt(self, hostname):
        self.mqtt_client = MQTTClient(hostname, self.mqtt_server, port=self.mqtt_port, user=self.mqtt_user, password=self.mqtt_password)
        self.mqtt_client.connect()
        
    def subscribe_mqtt(self,topic):
        self.mqtt_client.subscribe(topic)
    
    def publish_mqtt(self, topic, msg):
        if self.connected:
            self.mqtt_client.publish(topic, msg)
        
    def status(self):
        """
        Returns the status of the Node as a JSON object.
        """
        status_dict = {
            "CONNECTION": self.connected,
            "WIFI_SSID": self.wifi_ssid,
            "WIFI_IP": self.wifi.ifconfig()[0],
            "WIFI_SUBNET_MASK": self.wifi.ifconfig()[1],
            "WIFI_GATEWAY_ADDRESS": self.wifi.ifconfig()[2],
            "WIFI_DNS_SERVER": self.wifi.ifconfig()[3],
            "MQTT_SERVER": self.mqtt_server,
            "MQTT_PORT": self.mqtt_port,
            "MQTT_USER": self.mqtt_user,
            "MQTT_PASSWORD": self.mqtt_password,
            "MQTT_TOPIC_DEBUG": self.MQTT_TOPIC_DEBUG,
            "MQTT_TOPIC_TARGET": self.MQTT_TOPIC_TARGET,
            "MQTT_TOPIC_IMAGE": self.MQTT_TOPIC_IMAGE,
            "MQTT_TOPIC_SUBSCRIBE": self.MQTT_TOPIC_SUBSCRIBE,
            "MODEL_PLATES": self.MODEL_PLATES,
            "MODEL_CHARS": self.MODEL_CHARS,
            "LABEL_PLATES": self.LABEL_PLATES,
            "LABEL_CHARS": self.LABEL_CHARS
        }
        return json.dumps(status_dict, indent=4)
    
    def connection_info(self):
        """
        Returns the status of the connection as a JSON object.
        """
        status_dict = {
            "WIFI_SSID": self.wifi_ssid,
            "WIFI_IP": self.wifi.ifconfig()[0],
            "WIFI_SUBNET_MASK": self.wifi.ifconfig()[1],
            "WIFI_GATEWAY_ADDRESS": self.wifi.ifconfig()[2],
            "WIFI_DNS_SERVER": self.wifi.ifconfig()[3]
        }
        return json.dumps(status_dict, indent=4)
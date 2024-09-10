import network, time, utime, json
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
    def __init__(self, wifi_ssid, wifi_password, mqtt_server, mqtt_port, mqtt_user, mqtt_password, topic_dbg, topic_target, topic_sub):
        """
        Initializes a new Node object with the specified parameters.
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
        self.MQTT_TOPIC_DEBUG = topic_dbg
        self.MQTT_TOPIC_TARGET = topic_target
        self.MQTT_TOPIC_SUBSCRIBE = topic_sub
        
    
    """
      __  __      _   _               _     
     |  \/  |    | | | |             | |    
     | \  / | ___| |_| |__   ___   __| |___ 
     | |\/| |/ _ \ __| '_ \ / _ \ / _` / __|
     | |  | |  __/ |_| | | | (_) | (_| \__ \
     |_|  |_|\___|\__|_| |_|\___/ \__,_|___/
                                                                                  
    """
    def connect_wifi(self):

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
    
    def connect_mqtt(self):
        self.mqtt_client.connect()
        self.mqtt_client.subscribe(self.MQTT_TOPIC_SUBSCRIBE)
        
    
    def publish_mqtt(self, msg):
        self.mqtt_client.publish(self.MQTT_TOPIC_TARGET, msg)
    
    def publish_mqtt_debug(self, msg):
        self.mqtt_client.publish(self.MQTT_TOPIC_DEBUG, msg)
        
    def status(self):
        """
        Returns the status of the Node as a JSON object.
        """
        status_dict = {
            "WIFI_SSID": self.wifi_ssid,
            "WIFI_IP": self.wifi.ifconfig()[0],
            "WIFI_SUBNET_MASK": self.wifi.ifconfig()[1],
            "WIFI_GATEWAY_ADDRESS": self.wifi.ifconfig()[2],
            "WIFI_DNS_SERVER": self.wifi.ifconfig()[3],
            "MQTT_SERVER": self.mqtt_server,
            "MQTT_PORT": self.mqtt_port,
            "MQTT_USER": self.mqtt_user,
            "MQTT_TOPIC_DEBUG": self.MQTT_TOPIC_DEBUG,
            "MQTT_TOPIC_TARGET": self.MQTT_TOPIC_TARGET,
            "MQTT_TOPIC_SUBSCRIBE": self.MQTT_TOPIC_SUBSCRIBE
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
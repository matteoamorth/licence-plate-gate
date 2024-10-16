import sensor, pyb, image
import network, time, json
from mqtt import MQTTClient


DEBUG = 1


def dprint(a):
    if DEBUG:
        print(a)

class Edge_camera:

    def __init__(self):
        self.state = "setup"
        dprint("[SETUP] Starting...")

        self.cf = self.load_config("config.ini")

        self.device_id = self.cf['Settings']['DEVICE_ID']

        self.camera_setup()

        self.gpio_setup(self.cf['GPIO']['INPUT_CLOSED_PIN'], self.cf['GPIO']['ACTUATOR_OUT_PIN'])

        self.wireless_setup(self.cf['WiFi']['SSID'], self.cf['WiFi']['PASSWORD'])


        self.mqtt_setup(self.cf['MQTT_settings']['HOSTNAME'],
                        self.cf['MQTT_settings']['SERVER'],
                        self.cf['MQTT_settings']['PORT'],
                        self.cf['MQTT_settings']['USER'],
                        self.cf['MQTT_settings']['PASSWORD'],
                        )

        #self.mqtt_subscribe(self.cf['MQTT_topics']['TOPIC_SUBSCRIBE'])
        self.mqtt_subscribe("test/plate_check")

        self.topic_pub = self.cf['MQTT_topics']['TOPIC_TARGET']

        #self.mqtt_publish(self.topic_pub,f"{self.cf['MQTT_settings']['HOSTNAME']}")

        self.state = "core_loop"

    def on_message(self, topic, msg):
        msg = json.loads(msg.decode())
        dprint(f"msg: {msg}")

        if msg['device_id'] != self.device_id:
            dprint("[MQTT] Not for this device")
            return

        if msg['payload'] == 'gate_open':
            if self.pinClosed.value() == 1:
                dprint("[CORE] Closing gate")
                self.pinOut.high()
                time.sleep_ms(200)
                self.pinOut.low()

        if msg['payload'] == 'gate_close':
            if self.pinClosed.value() == 0:
                dprint("[CORE] Closing gate")
                self.pinOut.high()
                time.sleep_ms(200)
                self.pinOut.low()

        if msg['payload'] == 'server_busy':
            dprint('Server busy, setting idle state')
            self.state = "idle"
            return

        if msg['payload'] == 'server_free':
            dprint('Server free, restarting process')
            self.state = "core_loop"
            return


        msg = ""

    def parse_value(self, value):
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

    def load_config(self, filename):
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
                    value = self.parse_value(value)
                    config[current_section][key] = value
        return config

    def camera_setup(self):
        sensor.reset()
        sensor.set_pixformat(sensor.RGB565)
        sensor.set_framesize(sensor.QVGA)
        sensor.set_windowing((240, 240))
        sensor.skip_frames(time=2000)

    def gpio_setup(self, in_ = "P4", out = "P5"):
        dprint("[SETUP] GPIO")
        self.pinOut = pyb.Pin(out, pyb.Pin.OUT)
        self.pinClosed = pyb.Pin(in_, pyb.Pin.IN)

    def wireless_setup(self, SSID, KEY):
        dprint("[SETUP] WIFI")
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        self.wlan.connect(SSID, KEY)

        while not self.wlan.isconnected():
            dprint('Connecting to "{:s}"...'.format(SSID))
            time.sleep_ms(1000)

        dprint("[Setup] WiFi Connected ")

    def mqtt_setup(self, id_client="openmv", server_="localhost", port_=1883, user_= None, password_= None, frame = 240):
        print("[SETUP] MQTT")
        self.mqtt_client = MQTTClient(id_client, server_, user = user_, password = password_, port=port_)
        self.mqtt_client.connect(timeout = 0.75)
        self.mqtt_client.set_callback(self.on_message)
        self.fragment_size = frame

    def mqtt_subscribe(self, topic):
        self.mqtt_client.subscribe(topic)

    def mqtt_publish(self, topic, message):
        self.mqtt_client.publish(topic, message)


    def core_loop(self):
        self.clock = time.clock()
        self.mqtt_client.wait_msg()
        if self.state != 'core_loop':
            return

        img = sensor.snapshot()

        dprint("[CORE] sending image")

        for i in range(0, 240*240, self.fragment_size):
            fragment = img[i:i + self.fragment_size]

            message = {
                "device_id": self.device_id,
                "mode": 3,
                "fr_n": i / 240,
                "payload": fragment
            }


            dprint(f"{i/240 + 1} / 240 img rows")
            self.mqtt_publish(self.topic_pub, json.dumps(message))
            if i % 14400 == 0:
                self.mqtt_client.wait_msg()
                if self.state != 'core_loop':
                    return

        end_message = {
            "device_id": self.device_id,
            "mode": 3,
            "payload": "END_DATA"
        }

        self.mqtt_client.wait_msg()
        if self.state != 'core_loop':
            return

        self.mqtt_publish(self.topic_pub, json.dumps(end_message))

        img = None

    def idle(self):
        time.sleep_ms(300)
        self.mqtt_client.wait_msg()
        return


    def run(self):
        while True:
            state_functions = {
                "setup": self.__init__,
                "core_loop": self.core_loop,
                "idle": self.idle
            }

            state_function = state_functions.get(self.state)

            if state_function:
               state_function()
            else:
                dprint(f"Unknown state: {self.state}")
                break


            dprint(f"[CORE] {self.clock.fps()} fps")


if __name__ == "__main__":
    sm = Edge_camera()
    sm.run()

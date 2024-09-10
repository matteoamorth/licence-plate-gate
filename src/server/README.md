# 📄 Plate Recognition Server Documentation

## Abstract

This project implements a server for license plate recognition using a machine learning pipeline based on Keras OCR and the Roboflow service for image inference. The server receives images via MQTT, processes them to identify license plates, and stores the results in an InfluxDB database. Additionally, it includes a system to manage gate opening commands based on license plate recognition that will be sent to the actuator of the system.

## Table of Contents

- [📄 Plate Recognition Server Documentation](#-plate-recognition-server-documentation)
  - [Abstract](#abstract)
  - [Table of Contents](#table-of-contents)
  - [⚙️ Requirements](#️-requirements)
  - [🚀 Installation](#-installation)
    - [Upload files](#upload-files)
      - [Run the server](#run-the-server)

---

## ⚙️ Requirements

- Python 3.8 or higher
- External libraries:
  - `configparser`
  - `json`
  - `opencv-python`
  - `Pillow`
  - `numpy`
  - `keras_ocr`
  - `inference_sdk`
  - `influxdb-client`
  - `paho-mqtt`

## 🚀 Installation

To install all necessary dependencies, follow these steps:

1. **Create a virtual environment** (optional but recommended):

  ``` bash
  python3 -m venv env
  source env/bin/activate  # On Windows: env\Scripts\activate
  ```

1. **Install dependencies** using pip:

  ``` bash
    pip install configparser opencv-python Pillow numpy keras_ocr inference_sdk influxdb-client paho-mqtt
  ```

1. **Configuration**: Create a `server_config.ini` file with the following structure:

    ```ini
    [Settings]
    DEVICE_ID = your_device_id
    CLIENT_ID = your_client_id

    [Roboflow]
    MODEL_ID = your_model_id
    API_URL = your_api_url
    API_KEY = your_api_key

    [InfluxDB]
    INFLUXDB_URL = your_influxdb_url
    INFLUXDB_TOKEN = your_influxdb_token
    INFLUXDB_ORG = your_org
    INFLUXDB_BUCKET = your_bucket

    [MQTT Settings]
    USER = your_mqtt_user
    PASSWORD = your_mqtt_password
    BROKER = your_broker_url
    PORT = your_broker_port

    [MQTT Topics]
    TOPIC_SUBSCRIBE = your_topic_subscribe
    TOPIC_TARGET = your_topic_target
    TOPIC_DEBUG = your_topic_debug
    ```

1. **MQTT Broker**

Execute the following commands in the Raspberry Pi's shell:

```bash
sudo apt update
sudo apt install mosquitto mosquitto-clients
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
```

### Upload files

Copy the files contained in the server folder into the raspberry storage

#### Run the server

Browse into the folder containing previous files and run this command:

``` bash
python3 mqtt_image_receiver.py
```

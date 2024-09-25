# 📄 Plate Recognition Server Documentation

## Abstract

This project implements a server for license plate recognition using a machine learning pipeline based on Keras OCR and the Roboflow service for image inference. The server receives images via MQTT, processes them to identify license plates, and checks and stores the results in a InfluxDB database. Additionally, it includes a system to manage gate opening commands based on license plate recognition that will be sent to the actuator of the system.

## Table of Contents

- [📄 Plate Recognition Server Documentation](#-plate-recognition-server-documentation)
  - [Abstract](#abstract)
  - [Table of Contents](#table-of-contents)
  - [⚙️ Requirements](#️-requirements)
  - [🛠️ Installation](#️-installation)
    - [🐍 Python script](#-python-script)
    - [🛜 MQTT Broker](#-mqtt-broker)
    - [💾 InfluxDB](#-influxdb)
  - [🚀 Run the server](#-run-the-server)

---

## ⚙️ Requirements

- Python 3.8 or higher
- External libraries:
  - `configparser`
  - `argparse`
  - `pillow`
  - `keras_ocr`
  - `inference_sdk`
  - `influxdb-client`
  - `paho-mqtt`
  - `colorlog`
  - `tensorflow==2.15`

## 🛠️ Installation

To install all necessary dependencies, follow these steps:

### 🐍 Python script

1. **Create a virtual environment** (optional):

  ``` bash
  python3 -m venv env
  source env/bin/activate  # On Windows: env\Scripts\activate
  ```

1. **Install dependencies** (if not present) using pip:

  ``` bash
    pip install configparser argparser pillow keras_ocr inference_sdk influxdb-client paho-mqtt tensorflow==2.15
  ```

> Note: More recent versions of tensorflow library do not work properly.

1. **Configuration**: The config file named `server_config.ini` file is avaiable in this folder. It is possible to use your own config file.

1. **Sources installation**: copy the `server` folder inside the server device.

### 🛜 MQTT Broker

Execute the following commands in the server's shell:

```bash
sudo apt update
sudo apt install mosquitto mosquitto-clients
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
```

A copy of the configuration file is avaiable as `mqtt_broker.conf`.

### 💾 InfluxDB

1. Download and install influxdb on the target device.
2. Run the program and connect to the web interface (usually at <http://localhost:8086>).
3. Register a new user.
4. Create a bucket with the name used in the configuration file of the server (for example *license_plate_data*) and copy the token and organization in the configuration file.
5. Browse to src/test_tools/influx_connection.py and edit the `configuration example` and the `add plate profile` sections in order to establish a connection and add custom plates. This script can be reused to add or remove allowed plates.

## 🚀 Run the server

Browse into the server folder and launch the program with this shell command:

``` bash
python3 roboflow_server
```

If a custom configuration file is present, launch the program with this shell command:

``` bash
python3 roboflow_server --config your_config_file.ini
```

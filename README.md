# licence-plate-gate
An IoT system that reads license plates of vehicles with an OpenMV Cam and activates gates.

## Introduction
The project's goal is to develop an IoT system that allow registered vehicles to open any type of gate, barrier and automated door without any remote control. The system has three main sections:
+ an edge device that collects images from field and identifies features about the licence plate;
+ a lightweight server that collects data and publishes the results;
+ an edge device that perform actions published by the server.
  
These three functions can be on a **single device** (stand alone configuration - local) or spread among **many devices** (connected - online).

## Logic flow
The functioning of this systems follows these steps. 
1. **Plates detection**: identify car's plate from camera acquisition;

2. **Chars recognition**: identify chars inside the licence plate;

3. **Data transmission (only connected version)**: establish a connection with the server and forward the data;

4. **Evaluation**: define if the record is present;

5. **Actuation**: perform actions based on previous.

## Hardware

### Edge device 
It is the most critical element of the system. It has to be sufficiently powerfull (in stand alone configuration) to load and execute neural network models and perform connections over wifi. However, if the system is online, the operations on image recognition might be performed by server side.

In conclusion, any device with a discrete quality camera and a connection can achieve acceptable results. For this project a OpenMV Cam H7 Plus has been used. 

### Server
The server can be used in two ways:
- as a **database**, where it has to perform simple operations to check plate records
- as a **fog device**, where it has to analyze images and perform comparisons

### Actuator
The actuator can be the same edge device or a stand alone solution with GPIOs avaiable and MQTT support. 

## Software

### Visual recognition

The **plates** and **chars** recognition is perfomed with machine learning models trained with two different datasets. 

The first model has been trained to recognize whether there are plates in the image or not. The model is capable of detecting plates even if the area captured is very wide.

The second model has been trained to recognize chars in a image. This model needs a very small area to perform at best. Therefore, it is necessary to first define the area of the plate and then recognize chars.

### Connection (online version)

The connection between devices relies on MQTT over WIFI. Therefore, a LAN connection is sufficient to perform all tasks.

### Security

In the online configuration, plates detection and chars recognition can be performed on server side. Therefore, no critical data is stored on the edge device. 

However, if the connection drops or the system is in stand alone configuration, the records must be stored on the device. This could be a serious vulnerability if it is not well protected.

Another concern about security is the protection of the connection between devices. In this case the server act as the most critic element, because the publication of data on mqtt topics defines what other devices can do or not.

## Installation 

### Edge-device

Open edge-device folder and copy all the files in the device folder. To decide which mode to use, open the `config.ini` file and edit the `MODE` field 

### Server

To set up a Raspberry Pi as an MQTT server to receive and process the images sent by your program, follow these steps:

+ Install MQTT Broker (Mosquitto)
+ Install Python and libraries
+ Upload the files
+ Run the server

#### MQTT Broker

Copy and paste these commands in a raspberry's shell:

``` bash
sudo apt update
sudo apt install mosquitto mosquitto-clients
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
```

#### Python and libraries

Copy and paste these commands in a raspberry's shell:

``` bash
sudo apt install python3 python3-pip
pip3 install paho-mqtt numpy opencv-python
```
#### Upload files 

Copy the files contained in the server folder into the raspberry storage

#### Run the server

Browse into the folder containing previous files and run this command:

``` bash
python3 mqtt_image_receiver.py
```



\begin{equation*}
\begin{cases}
\sqrt{(x_2 - x)^2 + (y_2 - y)^2} - \sqrt{(x_1 - x)^2 + (y_1 - y)^2} = r_{21} \\
\sqrt{(x_3 - x)^2 + (y_3 - y)^2} - \sqrt{(x_1 - x)^2 + (y_1 - y)^2} = r_{31}
\end{cases}
\tag{1}
\end{equation*}
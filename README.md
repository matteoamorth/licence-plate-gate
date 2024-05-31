# licence-plate-gate
An IoT system that reads license plates of vehicles with an OpenMV Cam and activates gates.

## Introduction
The project's goal is to develop an IoT system that allow registered vehicles to open any type of gate, barrier and automated door without any remote control. The system has three different parts:
+ an edge device that collects images from field and identifies features about the licence plate;
+ a lightweight server that collects data and publishes the results;
+ an edge device that perform actions published by the server
  
These three components can be a single device or spread among many devices.

## Logic flow


## Hardware

### Edge device 
In order to collect images from the environment, a powerfull but compact device is suggested. However, any device with a discrete camera can achieve the results. For this project an OpenMV Cam has been used. 

### Server
The server has to perform simple operations. It can be hosted wherever you like: local, cloud or raspberryPi.

### Actuator
The actuator can be the same edge device or a stand alone solution with GPIOs avaiable to perform operations. 

## Software

### Plates recognition

### Chars recognition

### Connection and transmission

### Evaluation and pubblication (security actions)

### Actuation
# licence-plate-gate
An IoT system that reads license plates of vehicles with an OpenMV Cam and activates gates.

## Introduction
The project's goal is to develop an IoT system that allow registered vehicles to open any type of gate, barrier and automated door without any remote control. The system has three different parts:
+ an edge device that collects images from field and identifies features about the licence plate;
+ a lightweight server that collects data and publishes the results;
+ an edge device that perform actions published by the server
  
These three components can be a single device or spread among many devices.

## Logic flow
The project is organized following several steps. 
+ **Plates recognition**: identify car's plate from camera acquisition;

+ **Chars recognition**: identify chars present in the plates obtained in the previous step and build a string;

+ **Data transmission**: establish a connection with the server and forward the string;

+ **Evaluation and pubblication**: compare recived strings with database and publish resuts;

+ **Actuation**: perform actions based on previous results

## Hardware

### Edge device 
In order to collect images from the environment, a powerfull and compact device is suggested. However, any device with a discrete quality camera can achieve the results. For this project a OpenMV Cam H7 Plus has been used. 

### Server
The server has to perform simple operations. It can be hosted wherever you like: local, cloud or raspberryPi.

### Actuator
The actuator can be the same edge device or a stand alone solution with GPIOs avaiable to perform operations. 

## Software

### Visual recognition

The **plates** and **chars** recognition is perfomed with machine learning models that have been trained on external platforms and then uploaded on the edge device. 

### Connection 

The connection between devices has to be defined

### Evaluation and pubblication (security actions)

Security has to be defined

### Actuation

Actuation hasn't been analyzed yet.
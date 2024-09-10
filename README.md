# 🏠 🚧 🚗  License Plate Gate

An IoT system that reads license plates of vehicles and activates gates.

## Table of Contents

- [🏠 🚧 🚗  License Plate Gate](#----license-plate-gate)
  - [Table of Contents](#table-of-contents)
  - [📜 Introduction](#-introduction)
  - [🔄 Logic Flow](#-logic-flow)
  - [💡 Hardware](#-hardware)
    - [📹 Edge Device](#-edge-device)
    - [💻 Server](#-server)
    - [🦾 Actuator](#-actuator)
  - [📀 Software](#-software)
    - [🎯 Visual Recognition](#-visual-recognition)
    - [⚙️ Configurations](#️-configurations)
      - [1. All on board (offline mode)](#1-all-on-board-offline-mode)
      - [2. Simple database](#2-simple-database)
      - [3. Balanced configuration](#3-balanced-configuration)
      - [4. Lightweight camera](#4-lightweight-camera)
    - [🛜 Connection (only online version)](#-connection-only-online-version)
    - [🚨 Security](#-security)
  - [🛠 Installation](#-installation)
    - [Edge Device](#edge-device)
    - [Server](#server)


## 📜 Introduction

The goal of this project is to develop an IoT system that allows registered vehicles to open various types of gates, barriers, and automated doors without the usage of a remote control. The system consists of three main components:

- **Edge Device**: Collects images from the field and identifies features of the license plate.
- **Lightweight Server**: Collects data and publishes results.
- **Actuator Device**: Performs actions based on the results published by the server.

These components can be implemented on a **single device** (stand-alone configuration - local) or distributed across **multiple devices** (connected - online).

In other words, the system is designed to operate either in a stand-alone configuration or in a connected, online setup.

## 🔄 Logic Flow

The system operates through the following steps:

1. **Plate Detection**: Identify the vehicle's license plate from the camera acquisition.
2. **Character Recognition**: Recognize characters within the license plate.
3. **Data Transmission** (Connected Version Only): Establish a connection with the server and forward the data.
4. **Evaluation**: Determine if the record is present on the database.
5. **Actuation**: Perform actions based on the previous evaluation.

## 💡 Hardware

### 📹 Edge Device

The edge device is the critical element of the system. It must be powerful enough (expecially in stand-alone configuration) to load and execute neural network models and perform Wi-Fi connections. In an online system, image recognition tasks can be handled server-side, with lower minimum specs required.

A device with a good-quality camera and a connection can achieve good results. For this project, an OpenMV Cam H7 Plus has been selected.

### 💻 Server

The server can operate in two modes:

- **Database**: Performs simple operations to check license plate records.
- **Fog Device**: Analyzes images and performs comparisons.

### 🦾 Actuator

The actuator can be the same edge device or a separate solution with GPIOs and MQTT support. For this project the actuator has been merged with the edge-device.

## 📀 Software

### 🎯 Visual Recognition

License plate and character recognition are performed using machine learning models trained with different datasets:

- **Plate Detection Model**: Trained to identify the presence of license plates in images, even if the captured area is wide.
- **Character Recognition Model**: Trained to recognize characters within a defined plate area.

The sources used to train the two neural networks are avaiable in the `datasets` folders.

### ⚙️ Configurations

The software provided in this project allow to select different solutions based on the hardware constraints. There are four possible alternatives.

#### 1. All on board (offline mode)

In the offline mode, plate detection, characters recognition, record evaluation and actuation are performed on the device stand-alone.

**Key features**
➕ Configure a single device without a server.

➕ Connection is not requested.

➖ Higher hardware specs required.

➖ Database not accessible.

This flow can be selected setting the field `MODE = 0`;

#### 2. Simple database

In simple database, plate detection and characters recognition are performed on board, while record evaluation is left to the server-side.

**Key features**
➕ Database easily updatable.

➕ Perform actions with remote commands.

➖ Two devices required.

➖ Server has very poor tasks.

This flow can be selected setting the field `MODE = 1`;

#### 3. Balanced configuration

In the balanced configuration, plate detection is performed on board, while characters recognition and evaluation is performed by server-side.

**Key features**
➕ Better tasks and resources organization.

➕ Edge-device filters data for server, acting as a fog-device.

➖ Both devices need good specs to work correctly.

➖ The total evaluation time might increase.

#### 4. Lightweight camera

On lightweight camera, image acquisition is the only task installed on the board, all the other operations are performed on the connected server.

**Key features**
➕ Low specs required for edge-device.

➕ Server can deliver results faster.

➖ Edge-device can't filter the images acquired.

➖ Connection must have large bandwidth.

### 🛜 Connection (only online version)

Devices connect together using MQTT over Wi-Fi. A LAN connection is sufficient for performing all the tasks included.

### 🚨 Security

In the online configuration, plate detection and character recognition are handled server-side, minimizing sensitive data storage on the edge device. However, if the connection drops or in stand-alone configuration, records must be stored on the device, which could pose a security risk if not properly protected.

Another security concern is the protection of the connection between devices. The server is a critical element, as MQTT topic publication controls the actions of other devices.

## 🛠 Installation

### Edge Device

1. Open the `src/edge-device` folder and copy all files to the device folder.
2. To select the desired recognition mode, open the `config.ini` file and edit the `MODE` field. 
  
### Server

You can find the installation guide in the `src/server` folder .

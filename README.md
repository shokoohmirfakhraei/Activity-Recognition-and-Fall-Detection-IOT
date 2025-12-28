# Project Overview

This project implements an **activity recognition and fall detection** system using a Raspberry Pi Pico W. The system collects motion data from an **MPU6050 sensor**, processes it locally using **TinyML**, and sends activity and fall detection results wirelessly to a server for visualization and analysis.

The goal of the project is to demonstrate an end-to-end IoT + TinyML pipeline, including sensing, on-device processing, wireless communication, and cloud integration.

## How It's Made

Tech used: MicroPython, TinyML, MQTT Server, InfuxDB

Devices used: Raspberry Pi Pico W, MPU6050 sensor, 0.96" OLED display, LED indicator

## File Descriptions

> IOT_ML.ipynb

This is used for training and exporting the TinyML activity recognition and fall detection model.

> model.py

Contains the trained TinyML model. A single decision tree model was used.

> main_new.py

Main application script executed on the Raspberry Pi Pico W. This file handles sensor data collection from the MPU6050, runs TinyML inference using the model, controls output devices (LED and OLED), and transmits results to the server via MQTT.

## Notes

This project was developed for an academic course and focuses on demonstrating core IoT and TinyML concepts.

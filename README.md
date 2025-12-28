# Project Overview

This project implements an **activity recognition and fall detection** system using a Raspberry Pi Pico W. The system collects motion data from an **MPU6050 sensor**, processes it locally using **TinyML**, and sends activity and fall detection results wirelessly to a server for visualization and analysis.

The goal of the project is to demonstrate an end-to-end IoT + TinyML pipeline, including sensing, on-device processing, wireless communication, and cloud integration.

## How it's made

Tech used: MicroPython, TinyML, MQTT Server, InfuxDB

Devices used: Raspberry Pi Pico W, MPU6050 sensor, 0.96" OLED display, LED indicator

## Notes

This project was developed for an academic course and focuses on demonstrating core IoT and TinyML concepts rather than production-level optimization.

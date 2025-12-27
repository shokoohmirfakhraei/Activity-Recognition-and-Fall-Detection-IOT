import machine
import time
import math
import network
import ssd1306
import mini_model
import sys

# ===== TLS FIX =====
import ssl
sys.modules["ussl"] = ssl
from umqtt.simple import MQTTClient

# =========================
# Feature Extractor
# =========================
class FeatureExtractor:
    def __init__(self, window_size=50, step_size=12):
        self.window_size = window_size
        self.step_size = step_size
        self.buffer = []
        self.samples_since_last = 0

    def add_sample(self, ax, ay, az, gx, gy, gz):
        a_mag = math.sqrt(ax*ax + ay*ay + az*az)
        g_mag = math.sqrt(gx*gx + gy*gy + gz*gz)
        self.buffer.append([ax, ay, az, gx, gy, gz, a_mag, g_mag])

        if len(self.buffer) > self.window_size:
            self.buffer.pop(0)

        self.samples_since_last += 1

    def is_ready(self):
        return len(self.buffer) == self.window_size and \
               self.samples_since_last >= self.step_size

    def get_features(self):
        if not self.is_ready():
            return None

        features = []
        for i in range(8):
            signal = []
            for row in self.buffer:
                signal.append(row[i])

            mean = sum(signal) / self.window_size
            var = 0
            energy = 0
            diff = 0

            for j in range(self.window_size):
                v = signal[j]
                var += (v - mean) * (v - mean)
                energy += v * v
                if j > 0:
                    diff += abs(signal[j] - signal[j-1])

            std = math.sqrt(var / self.window_size)
            features.extend([
                mean,
                std,
                max(signal),
                min(signal),
                max(signal) - min(signal),
                energy / self.window_size,
                diff
            ])

        self.samples_since_last = 0
        return features

# =========================
# CONFIGURATION
# =========================
SSID = "POCOM"
PASSWORD = "Hadi1375"

MQTT_BROKER = "ff63906c314d497795e263eb6a953153.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USER = "Iot13"
MQTT_PASS = "Hadi1375"
CLIENT_ID = "pico_proto"

TOPIC_STEPS = b"picow/steps"
TOPIC_ACTIVITY = b"picow/activity"

# Timing & thresholds
MIN_STEP_INTERVAL = 600        # ms
ACTIVITY_HOLD_MS = 3000        # ms
FALL_PERSIST_MS = 10000        # ms

# =========================
# WIFI & MQTT
# =========================
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(SSID, PASSWORD)
time.sleep(3)

mqtt = MQTTClient(
    CLIENT_ID,
    MQTT_BROKER,
    port=MQTT_PORT,
    user=MQTT_USER,
    password=MQTT_PASS,
    ssl=True,
    ssl_params={"server_hostname": MQTT_BROKER}
)
mqtt.connect()

# =========================
# OLED
# =========================
time.sleep(1)
i2c = machine.I2C(0, scl=machine.Pin(1), sda=machine.Pin(0))
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

oled.fill(0)
oled.text("BOOT OK", 0, 0)
oled.show()
time.sleep(1)

# =========================
# LED (FALL INDICATOR)
# =========================
fall_led = machine.Pin(15, machine.Pin.OUT)
fall_led.off()

# =========================
# MPU6050
# =========================
MPU_ADDR = 0x68
i2c.writeto_mem(MPU_ADDR, 0x6B, b'\x00')

def read_word_2c(reg):
    h = i2c.readfrom_mem(MPU_ADDR, reg, 1)[0]
    l = i2c.readfrom_mem(MPU_ADDR, reg+1, 1)[0]
    v = (h << 8) | l
    return v - 65536 if v & 0x8000 else v

def read_accel_g():
    return (
        read_word_2c(0x3B)/16384,
        read_word_2c(0x3D)/16384,
        read_word_2c(0x3F)/16384
    )

def read_gyro_dps():
    return (
        read_word_2c(0x43)/131,
        read_word_2c(0x45)/131,
        read_word_2c(0x47)/131
    )

# =========================
# MAIN LOOP
# =========================
extractor = FeatureExtractor()
step_count = 0
last_step_time = 0
prev_mag_high = False

last_label = "WAIT"
last_activity_time = 0
fall_start_time = None

last_mqtt = 0
led_state = False
last_led_toggle = 0

print("System Started")

while True:
    now = time.ticks_ms()

    ax, ay, az = read_accel_g()
    gx, gy, gz = read_gyro_dps()
    extractor.add_sample(ax, ay, az, gx, gy, gz)

    # -------- STEP COUNT --------
    g_mag = math.sqrt(gx*gx + gy*gy + gz*gz)
    if g_mag > 15.0 and not prev_mag_high:
        if time.ticks_diff(now, last_step_time) > MIN_STEP_INTERVAL:
            step_count += 1
            last_step_time = now
    prev_mag_high = g_mag > 15.0

    # -------- FALL HEURISTIC --------
    a_mag = math.sqrt(ax*ax + ay*ay + az*az)
    fall_detected = a_mag > 2.5 and g_mag > 120

    # -------- FALL PERSISTENCE --------
    if fall_detected:
        last_label = "FALL"
        fall_start_time = now

    if fall_start_time is not None:
        if time.ticks_diff(now, fall_start_time) > FALL_PERSIST_MS:
            fall_start_time = None
        else:
            last_label = "FALL"

    # -------- ML ACTIVITY (ONLY IF NOT FALL) --------
    if fall_start_time is None and extractor.is_ready():
        features = extractor.get_features()
        _, new_label = mini_model.predict(features)

        if new_label == "FALL DETECTED!":
            new_label = "FALL"

        if new_label != last_label:
            if time.ticks_diff(now, last_activity_time) > ACTIVITY_HOLD_MS:
                last_label = new_label
                last_activity_time = now
        else:
            last_activity_time = now

    # -------- LED BLINK ON FALL --------
    if last_label == "FALL":
        if time.ticks_diff(now, last_led_toggle) > 300:
            led_state = not led_state
            fall_led.value(led_state)
            last_led_toggle = now
    else:
        fall_led.off()

    # -------- MQTT --------
    if time.ticks_diff(now, last_mqtt) > 5000:
        mqtt.publish(TOPIC_STEPS, str(step_count))
        mqtt.publish(TOPIC_ACTIVITY, last_label)
        last_mqtt = now

    # -------- OLED --------
    oled.fill(0)
    oled.text("AI Monitor", 20, 0)
    oled.text(last_label, 0, 20)
    oled.text("Steps:", 0, 40)
    oled.text(str(step_count), 60, 40)
    oled.show()

    print(last_label, "| Steps:", step_count)
    time.sleep_ms(50)

import glob
import time
import json
import paho.mqtt.client as mqtt

# -------------------------------
# Configuration
# -------------------------------

MQTT_BROKER = "broker.hivemq.com"   # Replace with your MQTT broker
MQTT_PORT = 1883
MQTT_TOPIC = "home/temperature"
DEVICE_NAME = "raspberry-pi-temperature"

TEMP_LIMIT = 30.0  # Warning limit in Celsius
READ_INTERVAL = 10  # Seconds

# DS18B20 sensor file
BASE_DIR = "/sys/bus/w1/devices/"
DEVICE_FOLDER = glob.glob(BASE_DIR + "28-*")

if not DEVICE_FOLDER:
    raise RuntimeError("DS18B20 sensor not found")

DEVICE_FILE = DEVICE_FOLDER[0] + "/w1_slave"


# -------------------------------
# Read temperature
# -------------------------------

def read_temperature():
    with open(DEVICE_FILE, "r") as file:
        lines = file.readlines()

    # Check whether the sensor reading is valid
    if lines[0].strip()[-3:] != "YES":
        return None

    # Extract temperature in millidegrees Celsius
    temperature_data = lines[1].split("t=")

    if len(temperature_data) < 2:
        return None

    temperature_c = float(temperature_data[1]) / 1000.0
    return temperature_c


# -------------------------------
# MQTT connection
# -------------------------------

def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        print("Connected to MQTT broker")
    else:
        print("MQTT connection failed:", reason_code)


mqtt_client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id=DEVICE_NAME
)

mqtt_client.on_connect = on_connect

print("Connecting to MQTT broker...")
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_start()


# -------------------------------
# Main monitoring loop
# -------------------------------

try:
    while True:
        temperature = read_temperature()

        if temperature is None:
            print("Invalid temperature reading")
            time.sleep(READ_INTERVAL)
            continue

        status = "NORMAL"

        if temperature >= TEMP_LIMIT:
            status = "WARNING"

        data = {
            "device": DEVICE_NAME,
            "temperature": round(temperature, 2),
            "unit": "C",
            "status": status,
            "timestamp": time.time()
        }

        message = json.dumps(data)

        mqtt_client.publish(MQTT_TOPIC, message)

        print(
            f"Temperature: {temperature:.2f} °C | "
            f"Status: {status} | "
            f"Published: {message}"
        )

        time.sleep(READ_INTERVAL)

except KeyboardInterrupt:
    print("\nStopping temperature monitor...")

finally:
    mqtt_client.loop_stop()
    mqtt_client.disconnect()

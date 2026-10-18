
import json
import logging
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from config import (
    MQTT_HOST,
    MQTT_PORT,
    MQTT_TOPIC,
    MQTT_CLIENT_ID,
    INFLUX_URL,
    INFLUX_ORG,
    INFLUX_BUCKET,
    INFLUX_TOKEN,
    DEVICE_ID,
    NUMERIC_FIELDS,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

seen_sequences = set()
last_sequence = None
message_count = 0
write_api = None


# ==================== KIEM TRA JSON ====================
def valid_payload(payload):
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, f"JSON khong hop le: {exc}"

    required_fields = ("temperature", "humidity", "distance_cm")
    missing = [key for key in required_fields if key not in data]

    if missing:
        return None, f"Thieu truong bat buoc: {missing}"

    cleaned = {}

    for key in NUMERIC_FIELDS:
        if key not in data:
            continue

        value = data[key]

        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None, f"Truong {key} khong phai so"

        cleaned[key] = (
            int(value)
            if key in ("sequence", "uptime_s", "rssi")
            else float(value)
        )

    cleaned["device_id"] = str(data.get("device_id", DEVICE_ID))
    cleaned["sequence"] = int(data.get("sequence", -1))
    cleaned["uptime_s"] = int(data.get("uptime_s", 0))

    return cleaned, None


# ==================== MQTT CONNECT ====================
def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        logging.info(
            "Da ket noi MQTT %s:%s",
            MQTT_HOST,
            MQTT_PORT
        )

        result, mid = client.subscribe(MQTT_TOPIC, qos=0)

        if result == mqtt.MQTT_ERR_SUCCESS:
            logging.info("Da subscribe topic: %s", MQTT_TOPIC)
        else:
            logging.error("Subscribe that bai, result=%s", result)

    else:
        logging.error(
            "Ket noi MQTT that bai: reason_code=%s",
            reason_code
        )


# ==================== MQTT DISCONNECT ====================
def on_disconnect(
    client,
    userdata,
    disconnect_flags,
    reason_code,
    properties
):
    logging.warning(
        "MQTT bi ngat ket noi: reason_code=%s",
        reason_code
    )


# ==================== NHAN DU LIEU MQTT ====================
def on_message(client, userdata, msg):
    global last_sequence, message_count

    started = time.perf_counter()

    data, error = valid_payload(msg.payload)

    if error:
        logging.warning(
            "Bo qua message: %s | payload=%s",
            error,
            msg.payload[:200]
        )
        return

    seq = data["sequence"]
    dev = data["device_id"]
    dedupe_key = (dev, seq)

    # Phat hien ban tin trung
    if seq >= 0 and dedupe_key in seen_sequences:
        logging.warning(
            "Ban tin trung: device=%s sequence=%s",
            dev,
            seq
        )
        return

    # Phat hien kha nang mat ban tin
    if seq >= 0:
        if last_sequence is not None and seq > last_sequence + 1:
            logging.warning(
                "Co the mat du lieu: sequence truoc=%s, hien tai=%s",
                last_sequence,
                seq
            )

        if last_sequence is None or seq > last_sequence:
            last_sequence = seq

        seen_sequences.add(dedupe_key)

        if len(seen_sequences) > 10000:
            seen_sequences.clear()
            seen_sequences.add(dedupe_key)

    # Tao ban ghi InfluxDB
    point = Point("sensor_raw").tag("device_id", dev)

    for key in NUMERIC_FIELDS:
        if key in data:
            point = point.field(key, data[key])

    point = (
        point
        .field("valid", True)
        .time(datetime.now(timezone.utc), WritePrecision.NS)
    )

    # Ghi du lieu vao InfluxDB
    try:
        write_api.write(
            bucket=INFLUX_BUCKET,
            org=INFLUX_ORG,
            record=point
        )

        elapsed_ms = (time.perf_counter() - started) * 1000
        message_count += 1

        logging.info(
            "Luu #%s | seq=%s | temp=%s | hum=%s | "
            "distance=%s cm | ghi DB=%.2f ms",
            message_count,
            seq,
            data.get("temperature"),
            data.get("humidity"),
            data.get("distance_cm"),
            elapsed_ms
        )

    except Exception:
        logging.exception(
            "Khong ghi duoc vao InfluxDB. "
            "Kiem tra URL, token, organization va bucket."
        )


# ==================== MAIN ====================
def main():
    global write_api

    if (
        not INFLUX_TOKEN
        or INFLUX_TOKEN == "THAY_BANG_TOKEN_INFLUXDB_CUA_BAN"
    ):
        raise SystemExit(
            "Hay dien INFLUX_TOKEN trong file .env truoc khi chay."
        )

    logging.info(
        "Kiem tra InfluxDB: url=%s, org=%s, bucket=%s",
        INFLUX_URL,
        INFLUX_ORG,
        INFLUX_BUCKET
    )

    with InfluxDBClient(
        url=INFLUX_URL,
        token=INFLUX_TOKEN,
        org=INFLUX_ORG
    ) as db:

        health = db.health()
        logging.info("InfluxDB health: %s", health.status)

        write_api = db.write_api(
            write_options=SYNCHRONOUS
        )

        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=MQTT_CLIENT_ID,
            protocol=mqtt.MQTTv311
        )

        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.on_message = on_message

        client.reconnect_delay_set(
            min_delay=1,
            max_delay=30
        )

        logging.info(
            "Dang ket noi MQTT broker %s:%s ...",
            MQTT_HOST,
            MQTT_PORT
        )
        logging.info("MQTT Client ID: %s", MQTT_CLIENT_ID)
        logging.info("MQTT topic: %s", MQTT_TOPIC)

        try:
            client.connect(
                MQTT_HOST,
                MQTT_PORT,
                keepalive=60
            )
            client.loop_forever()

        except KeyboardInterrupt:
            logging.info("Da dung collector.")

        except Exception:
            logging.exception("Collector gap loi.")

        finally:
            client.disconnect()
            write_api.close()


if __name__ == "__main__":
    main()

import pandas as pd
import streamlit as st
import plotly.express as px
from streamlit_autorefresh import st_autorefresh
from influxdb_client import InfluxDBClient
from config import INFLUX_URL, INFLUX_ORG, INFLUX_BUCKET, INFLUX_TOKEN

st.set_page_config(page_title="IoT Bài 2", page_icon="📡", layout="wide")
st.title("IoT Bài thực hành số 2")
st.caption("ESP32 · DHT22 · HC-SR04 · MQTT · InfluxDB 2.x")

if not INFLUX_TOKEN or INFLUX_TOKEN == "THAY_BANG_TOKEN_INFLUXDB_CUA_BAN":
    st.error("Hãy điền INFLUX_TOKEN trong file .env rồi khởi động lại dashboard.")
    st.stop()

period = st.selectbox("Khoảng thời gian", ["1 giờ", "6 giờ", "24 giờ", "7 ngày"], index=1)
hours = {"1 giờ": 1, "6 giờ": 6, "24 giờ": 24, "7 ngày": 168}[period]

def load_measurement(client, measurement, hours):
    flux = f'''
from(bucket: "{INFLUX_BUCKET}")
  |> range(start: -{hours}h)
  |> filter(fn: (r) => r._measurement == "{measurement}")
  |> pivot(rowKey:["_time", "device_id"], columnKey: ["_field"], valueColumn: "_value")
  |> sort(columns: ["_time"])
'''
    result = client.query_api().query_data_frame(flux, org=INFLUX_ORG)
    if isinstance(result, list):
        frames = [x for x in result if isinstance(x, pd.DataFrame) and not x.empty]
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return result if isinstance(result, pd.DataFrame) else pd.DataFrame()

try:
    with InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG) as client:
        raw = load_measurement(client, "sensor_raw", hours)
        processed = load_measurement(client, "sensor_processed", hours)
except Exception as exc:
    st.error(f"Không đọc được InfluxDB: {exc}")
    st.stop()

if raw.empty:
    st.warning("Chưa có dữ liệu thô. Chạy collector.py và để ESP32 publish MQTT.")
else:
    raw["_time"] = pd.to_datetime(raw["_time"], utc=True, errors="coerce")
    raw = raw.dropna(subset=["_time"]).sort_values("_time")
    st.subheader("1. Dữ liệu thô")
    cols = st.columns(4)
    for col, field, label, suffix in zip(cols, ["temperature", "humidity", "distance_cm", "rssi"],
                                         ["Nhiệt độ", "Độ ẩm", "Khoảng cách", "RSSI"],
                                         [" °C", " %", " cm", " dBm"]):
        if field in raw.columns:
            vals = pd.to_numeric(raw[field], errors="coerce").dropna()
            col.metric(label, f"{vals.iloc[-1]:.2f}{suffix}" if not vals.empty else "N/A")
    chart_fields = [f for f in ["temperature", "humidity", "distance_cm"] if f in raw.columns]
    if chart_fields:
        long = raw.melt(id_vars=["_time"], value_vars=chart_fields, var_name="Thông số", value_name="Giá trị")
        st.plotly_chart(px.line(long, x="_time", y="Giá trị", color="Thông số", title="Dữ liệu cảm biến theo thời gian"), use_container_width=True)
    st.dataframe(raw.tail(100), use_container_width=True)

st.subheader("2. Dữ liệu sau tiền xử lý")
if processed.empty:
    st.info("Chưa có dữ liệu đã xử lý. Chạy: python preprocess.py")
else:
    processed["_time"] = pd.to_datetime(processed["_time"], utc=True, errors="coerce")
    fields = [f for f in ["temperature", "humidity", "distance_cm"] if f in processed.columns]
    if fields:
        long = processed.melt(id_vars=["_time"], value_vars=fields, var_name="Thông số", value_name="Giá trị")
        st.plotly_chart(px.line(long, x="_time", y="Giá trị", color="Thông số", title="Dữ liệu đã resample theo phút"), use_container_width=True)
    st.dataframe(processed.tail(100), use_container_width=True)

st.subheader("3. Chỉ số thu thập và lưu trữ")
if not raw.empty:
    st.metric("Số bản ghi thô trong khoảng đã chọn", len(raw))
    if "sequence" in raw.columns:
        seq = pd.to_numeric(raw["sequence"], errors="coerce").dropna().sort_values().drop_duplicates()
        gaps = int(max(0, (seq.max() - seq.min() + 1) - len(seq))) if not seq.empty else 0
        st.metric("Ước tính sequence bị thiếu", gaps)
    st.caption("Log collector đo thời gian từ lúc Python nhận message đến khi ghi xong InfluxDB; đây là độ trễ xử lý phía collector, không phải độ trễ đầu-cuối.")

from datetime import timezone
import logging
import numpy as np
import pandas as pd
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from config import INFLUX_URL, INFLUX_ORG, INFLUX_BUCKET, INFLUX_TOKEN, DEVICE_ID

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
FIELDS = ["temperature", "humidity", "distance_cm", "rssi"]

def read_raw(query_api, hours=24):
    flux = f'''
from(bucket: "{INFLUX_BUCKET}")
  |> range(start: -{int(hours)}h)
  |> filter(fn: (r) => r._measurement == "sensor_raw")
  |> filter(fn: (r) => r._field == "temperature" or r._field == "humidity" or r._field == "distance_cm" or r._field == "rssi" or r._field == "sequence" or r._field == "uptime_s")
  |> pivot(rowKey:["_time", "device_id"], columnKey: ["_field"], valueColumn: "_value")
  |> sort(columns: ["_time"])
'''
    result = query_api.query_data_frame(flux, org=INFLUX_ORG)
    if isinstance(result, list):
        frames = [x for x in result if isinstance(x, pd.DataFrame) and not x.empty]
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return result if isinstance(result, pd.DataFrame) else pd.DataFrame()

def remove_outliers_iqr(series):
    s = pd.to_numeric(series, errors="coerce")
    valid = s.dropna()
    if len(valid) < 4:
        return s
    q1, q3 = valid.quantile(.25), valid.quantile(.75)
    iqr = q3 - q1
    if iqr == 0:
        return s
    return s.mask((s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr))

def main():
    if not INFLUX_TOKEN or INFLUX_TOKEN == "THAY_BANG_TOKEN_INFLUXDB_CUA_BAN":
        raise SystemExit("Bạn cần điền INFLUX_TOKEN trong file .env.")
    with InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG) as db:
        raw = read_raw(db.query_api(), hours=24)
        if raw.empty:
            raise SystemExit("Chưa có sensor_raw. Hãy chạy collector và chờ ESP32 gửi dữ liệu.")
        raw["_time"] = pd.to_datetime(raw["_time"], utc=True, errors="coerce")
        raw = raw.dropna(subset=["_time"]).sort_values("_time").drop_duplicates(subset=["_time", "device_id"], keep="last")
        raw = raw.set_index("_time")
        for field in FIELDS:
            if field not in raw.columns:
                raw[field] = np.nan
            raw[field] = remove_outliers_iqr(raw[field])
        numeric = raw[FIELDS].resample("1min").mean()
        missing_before = int(numeric.isna().sum().sum())
        numeric = numeric.interpolate(method="time", limit=3).ffill(limit=1).bfill(limit=1).dropna(how="all")
        if numeric.empty:
            raise SystemExit("Không còn dữ liệu hợp lệ sau tiền xử lý.")
        for field in FIELDS:
            numeric[f"{field}_rolling_mean_3"] = numeric[field].rolling(3, min_periods=1).mean()
            numeric[f"{field}_delta"] = numeric[field].diff().fillna(0)
            min_v, max_v = numeric[field].min(), numeric[field].max()
            numeric[f"{field}_normalized"] = 0.0 if pd.isna(min_v) or pd.isna(max_v) or max_v == min_v else (numeric[field] - min_v) / (max_v - min_v)
        write_api = db.write_api(write_options=SYNCHRONOUS)
        try:
            written = 0
            for ts, row in numeric.iterrows():
                point = Point("sensor_processed").tag("device_id", DEVICE_ID)
                for col, value in row.items():
                    if pd.notna(value) and np.isfinite(float(value)):
                        point = point.field(col, float(value))
                point = point.field("missing_values_before_fill", missing_before).time(ts.to_pydatetime(), WritePrecision.NS)
                write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
                written += 1
            logging.info("Đã xử lý %s dòng và ghi vào sensor_processed.", written)
            logging.info("Số ô thiếu trước khi điền: %s", missing_before)
        finally:
            write_api.close()

if __name__ == "__main__":
    main()

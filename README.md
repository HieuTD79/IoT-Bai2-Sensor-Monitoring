# Bài thực hành số 2 — Thu thập, lưu trữ và tiền xử lý dữ liệu IoT

## 1. Kiến trúc
ESP32 (DHT22 + HC-SR04) -> MQTT broker -> Python collector -> InfluxDB 2.x.
Python preprocess đọc dữ liệu thô, xử lý chuỗi thời gian và ghi measurement `sensor_processed`.
Streamlit hiển thị dữ liệu thô và dữ liệu đã xử lý.

> Broker HiveMQ công khai chỉ dùng cho học tập. Topic công khai; không gửi dữ liệu riêng tư.

## 2. Cài đặt
1. Cài Python 3.11/3.12 và InfluxDB OSS 2.x.
2. Khởi động InfluxDB, mở `http://localhost:8086`.
3. Tạo organization `ptit`, bucket `iot_bai2`, tạo API token có quyền đọc/ghi bucket.
4. Sao chép `.env.example` thành `.env`, điền token vào `INFLUX_TOKEN`.
5. Mở terminal tại thư mục dự án và chạy:

```bash
python -m venv .venv
```

Windows CMD:
```bat
.venv\Scripts\activate
pip install -r requirements.txt
```

## 3. Cấu hình Wokwi
1. Tạo/sửa project ESP32 theo `firmware/diagram.json` và `firmware/sketch.ino`.
2. Thêm thư viện `DHTesp` và `PubSubClient` trong Library Manager của Wokwi.
3. Run simulation. Kiểm tra Serial Monitor có Wi-Fi, MQTT và `Publish thanh cong`.
4. Topic: `ptit/b23dccn311/iot_bai2/telemetry`, JSON được gửi mỗi 5 giây.
5. Nếu đổi topic, sửa cả firmware và `.env`.

## 4. Chạy collector và dashboard
Terminal 1:
```bash
python collector.py
```
Để ESP32 chạy 2–5 phút và kiểm tra log `Lưu #...`.

Terminal 2:
```bash
python preprocess.py
```
Chạy lại sau khi có thêm dữ liệu để cập nhật dữ liệu đã xử lý.

Terminal 3:
```bash
streamlit run dashboard.py
```
Mở URL Streamlit (thường là `http://localhost:8501`).

## 5. Quy tắc xử lý
- Kiểm tra JSON và trường bắt buộc.
- Phát hiện sequence trùng trong phiên collector và cảnh báo sequence bị nhảy.
- IQR: đánh dấu điểm ngoại lai thành NaN.
- Resampling trung bình theo phút.
- Điền thiếu bằng nội suy thời gian tối đa 3 mẫu, sau đó forward/backward fill tối đa 1 mẫu.
- Rolling mean 3 mẫu, delta sai phân, min-max normalization.
- Dữ liệu thô ở `sensor_raw`; dữ liệu đã xử lý ở `sensor_processed`.

## 6. Giới hạn
- Broker công khai có thể không ổn định và topic không riêng tư.
- Phát hiện trùng trong phiên collector; khởi động lại sẽ reset bộ nhớ.
- Log đo độ trễ xử lý từ lúc Python nhận message đến khi ghi InfluxDB xong, không phải độ trễ đầu-cuối.

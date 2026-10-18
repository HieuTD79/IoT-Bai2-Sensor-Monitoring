# BÁO CÁO BÀI THỰC HÀNH SỐ 2
## Thu thập, lưu trữ và tiền xử lý dữ liệu IoT

**Sinh viên:** Trần Duy Hiếu  
**Mã sinh viên:** B23DCCN311  
**Đơn vị:** Học viện Công nghệ Bưu chính Viễn thông

## 1. Mục tiêu
Xây dựng pipeline thu thập dữ liệu IoT qua MQTT, kiểm tra và lưu dữ liệu chuỗi thời gian, tiền xử lý dữ liệu cảm biến, trực quan hóa dữ liệu và đánh giá hoạt động thu thập/lưu trữ.

## 2. Mô hình hệ thống
ESP32 DevKit V1 trên Wokwi dùng DHT22 để lấy nhiệt độ/độ ẩm và HC-SR04 để đo khoảng cách. ESP32 gửi JSON qua MQTT mỗi 5 giây. Python collector subscribe topic, xác thực JSON và ghi measurement `sensor_raw` vào InfluxDB 2.x. Chương trình tiền xử lý tạo measurement `sensor_processed`. Dashboard Streamlit hiển thị hai nhóm dữ liệu.

**Chèn ảnh:** sơ đồ Wokwi, Serial Monitor, bucket InfluxDB, dashboard.

## 3. Thu thập và lưu trữ
Các trường thu thập: `temperature`, `humidity`, `distance_cm`, `rssi`, `sequence`, `uptime_s` và `device_id`. Collector kiểm tra JSON, trường bắt buộc và kiểu dữ liệu, cảnh báo sequence trùng hoặc nhảy. Dữ liệu thô được lưu ở `sensor_raw` với thời gian ghi UTC.

**Điền số liệu sau khi chạy thực nghiệm:**
- Thời gian chạy: … phút
- Số bản ghi thô: …
- Số message lỗi: …
- Số cảnh báo sequence trùng/nhảy: …
- Thời gian ghi DB trung bình từ log: … ms

## 4. Tiền xử lý
Chương trình đọc dữ liệu trong 24 giờ gần nhất. Điểm ngoại lai được phát hiện bằng IQR và chuyển thành giá trị thiếu. Dữ liệu được resample theo phút bằng trung bình; giá trị thiếu được nội suy theo thời gian trong giới hạn quy định. Sau đó tính rolling mean 3 mẫu, delta và chuẩn hóa min-max. Kết quả ghi vào `sensor_processed`.

## 5. Dashboard và đánh giá
Dashboard hiển thị giá trị mới nhất, đồ thị theo thời gian, bảng dữ liệu thô và dữ liệu đã xử lý. Log collector đo thời gian từ callback nhận message đến khi ghi InfluxDB hoàn tất. Đây là độ trễ xử lý phía collector, không phải độ trễ đầu-cuối.

**Chèn ảnh:** dashboard dữ liệu thô và dữ liệu đã xử lý.

## 6. Kết luận
Pipeline gồm thu thập MQTT, xác thực dữ liệu, lưu trữ chuỗi thời gian, tiền xử lý và trực quan hóa. Sau khi chạy thực nghiệm, bổ sung số liệu và ảnh chụp màn hình. Nêu rõ giới hạn quan sát được, ví dụ broker công khai, dữ liệu thiếu, sequence bị nhảy và thời gian ghi DB.

## Phụ lục
`firmware/sketch.ino`, `collector.py`, `preprocess.py`, `config.py`, `.env` (không đưa token thật vào báo cáo/nộp công khai), `dashboard.py`, `requirements.txt`, `README.md`.

from flask import Flask, render_template, jsonify, Response
from datetime import datetime
import cv2
import time
import csv
import os
import threading

app = Flask(__name__)

# ==========================================
# Mini 4WD Finish Line Detection
# ==========================================

CAMERA_INDEX = 0
MIN_OBJECT_AREA = 350
COOLDOWN_SECONDS = 1.5

# Detection Zone: fractions of camera image
# Adjust these after placing the camera over the track.
ROI_X1 = 0.15
ROI_X2 = 0.85
ROI_Y1 = 0.30
ROI_Y2 = 0.90

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(BASE_DIR, "mini4wd_results.csv")

camera = None
camera_lock = threading.Lock()
data_lock = threading.Lock()

lap_count = 0
last_crossing_time = None
best_lap = None
current_lap = 0.0
car_color = "Unknown"
detection_status = "WAITING"
last_crossing_clock = None

lap_records = []


def detect_color(roi):
    if roi is None or roi.size == 0:
        return "Unknown"

    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    h, s, v = hsv.mean(axis=(0, 1))

    if v < 50:
        return "Black"
    if s < 40 and v > 190:
        return "White"
    if s < 40:
        return "Gray"
    if h < 10 or h >= 170:
        return "Red"
    if h < 25:
        return "Orange"
    if h < 35:
        return "Yellow"
    if h < 85:
        return "Green"
    if h < 130:
        return "Blue"
    return "Other"


def save_record(record):
    file_exists = os.path.exists(CSV_FILE)

    with open(CSV_FILE, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)

        if not file_exists or os.path.getsize(CSV_FILE) == 0:
            writer.writerow([
                "Date", "Lap", "Lap_Time_sec", "Best_Lap_sec", "Color"
            ])

        writer.writerow([
            record["timestamp"],
            record["lap"],
            record["time"],
            record["best"],
            record["color"]
        ])


def record_crossing(now, color):
    global lap_count, last_crossing_time
    global best_lap, current_lap, last_crossing_clock

    with data_lock:
        # The first crossing starts the timing reference.
        if last_crossing_time is None:
            lap_count += 1
            last_crossing_time = now
            last_crossing_clock = datetime.now().strftime("%H:%M:%S")
            car_color = color
            print(f"First crossing detected. Lap count: {lap_count}")
            return

        lap_time = now - last_crossing_time

        # Ignore implausibly short detections.
        if lap_time < COOLDOWN_SECONDS:
            return

        last_crossing_time = now
        last_crossing_clock = datetime.now().strftime("%H:%M:%S")
        lap_count += 1
        current_lap = lap_time

        if best_lap is None or lap_time < best_lap:
            best_lap = lap_time

        record = {
            "lap": lap_count,
            "time": round(lap_time, 3),
            "best": round(best_lap, 3),
            "color": color,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "CAMERA"
        }

        lap_records.append(record)

    save_record(record)
    print(
        f"Lap {record['lap']} | Time: {record['time']} sec "
        f"| Best: {record['best']} sec | Color: {color}"
    )


def get_camera():
    global camera

    with camera_lock:
        if camera is None or not camera.isOpened():
            camera = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)

            if not camera.isOpened():
                camera.release()
                camera = None

        return camera


def generate_frames():
    global detection_status, car_color

    background = cv2.createBackgroundSubtractorMOG2(
        history=250,
        varThreshold=50,
        detectShadows=False
    )

    previous_side = None
    last_detection_time = 0.0

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))

    while True:
        cam = get_camera()

        if cam is None:
            with data_lock:
                detection_status = "CAMERA ERROR"
            time.sleep(1)
            continue

        with camera_lock:
            success, frame = cam.read()

        if not success:
            time.sleep(0.05)
            continue

        height, width = frame.shape[:2]

        # Limit detection to the selected track area.
        x1 = int(width * ROI_X1)
        x2 = int(width * ROI_X2)
        y1 = int(height * ROI_Y1)
        y2 = int(height * ROI_Y2)

        roi = frame[y1:y2, x1:x2]
        roi_h, roi_w = roi.shape[:2]
        finish_x = roi_w // 2

        mask = background.apply(roi)
        _, mask = cv2.threshold(mask, 200, 255, cv2.THRESH_BINARY)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        candidate = None
        largest_area = MIN_OBJECT_AREA

        for contour in contours:
            area = cv2.contourArea(contour)
            if area > largest_area:
                x, y, w, h = cv2.boundingRect(contour)
                candidate = (x, y, w, h)
                largest_area = area

        now = time.perf_counter()

        # Draw the detection zone and finish line.
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
        line_x = x1 + finish_x
        cv2.line(frame, (line_x, y1), (line_x, y2), (255, 0, 0), 2)

        status_text = "SEARCHING"

        if candidate is not None:
            x, y, w, h = candidate
            center_x = x + w // 2

            # Use only the central part of the detected object for color.
            pad_x = max(1, int(w * 0.2))
            pad_y = max(1, int(h * 0.2))
            color_roi = roi[
                y + pad_y:max(y + pad_y + 1, y + h - pad_y),
                x + pad_x:max(x + pad_x + 1, x + w - pad_x)
            ]
            color = detect_color(color_roi)

            cv2.rectangle(
                frame,
                (x1 + x, y1 + y),
                (x1 + x + w, y1 + y + h),
                (0, 255, 0),
                2
            )

            side = "left" if center_x < finish_x else "right"
            crossed = previous_side is not None and side != previous_side

            # Count only a detected crossing of the finish line.
            if crossed and now - last_detection_time >= COOLDOWN_SECONDS:
                record_crossing(now, color)
                last_detection_time = now

            previous_side = side
            status_text = "OBJECT DETECTED"

            with data_lock:
                car_color = color

        else:
            previous_side = None

        with data_lock:
            laps = lap_count
            color_text = car_color
            detection_status = status_text

        cv2.putText(
            frame, f"Laps: {laps}", (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2
        )
        cv2.putText(
            frame, f"Color: {color_text}", (20, 70),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2
        )

        ok, buffer = cv2.imencode(".jpg", frame)
        if ok:
            yield (
                b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
                + buffer.tobytes() + b"\r\n"
            )


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/video_feed")
def video_feed():
    return Response(
        generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/api/status")
def status():
    with data_lock:
        return jsonify({
            "status": detection_status,
            "lap_count": lap_count,
            "current_lap": round(current_lap, 3),
            "best_lap": round(best_lap, 3) if best_lap is not None else None,
            "speed_cm_s": None,
            "car_color": car_color,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })


@app.route("/api/laps")
def laps_api():
    with data_lock:
        return jsonify(list(reversed(lap_records)))


if __name__ == "__main__":
    app.run(debug=False, threaded=True, use_reloader=False)

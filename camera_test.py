import cv2
import time
import csv
import os
from datetime import datetime

# ==========================================
# Mini 4WD Camera + Lap Timer System
# ==========================================

CAMERA_INDEX = 0
MIN_OBJECT_AREA = 150
COOLDOWN_SECONDS = 0.8

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(BASE_DIR, "mini4wd_results.csv")

crossing_count = 0
last_crossing_time = None
previous_side = None
previous_position = None
previous_position_time = None

best_lap_time = None
total_distance_cm = 0.0

# ==========================================
# CSV Setup
# ==========================================

if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Date",
            "Lap",
            "Timestamp",
            "Lap_Time_sec",
            "Speed_cm_s",
            "Distance_cm",
            "Color"
        ])

# ==========================================
# Lap Timer
# ==========================================

def record_lap(now, color_name, speed_cm_s=None, distance_cm=None):
    global crossing_count, last_crossing_time, best_lap_time

    crossing_count += 1

    lap_time = None
    if last_crossing_time is not None:
        lap_time = now - last_crossing_time
        if best_lap_time is None or lap_time < best_lap_time:
            best_lap_time = lap_time

    last_crossing_time = now

    print("--------------------------------")
    print(f"Lap: {crossing_count}")
    print(
        f"Lap Time: {lap_time:.3f} sec"
        if lap_time is not None
        else "Lap Time: First crossing"
    )
    print(
        f"Best Lap: {best_lap_time:.3f} sec"
        if best_lap_time is not None
        else "Best Lap: Waiting for next lap"
    )
    print(f"Color: {color_name}")

    with open(CSV_FILE, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            crossing_count,
            f"{now:.3f}",
            f"{lap_time:.3f}" if lap_time is not None else "",
            f"{speed_cm_s:.2f}" if speed_cm_s is not None else "",
            f"{distance_cm:.2f}" if distance_cm is not None else "",
            color_name
        ])


def reset_timer():
    global crossing_count, last_crossing_time, best_lap_time
    global previous_side, previous_position, previous_position_time

    crossing_count = 0
    last_crossing_time = None
    best_lap_time = None
    previous_side = None
    previous_position = None
    previous_position_time = None

    print("Lap timer reset.")


# ==========================================
# Camera
# ==========================================

def main():
    global previous_side, previous_position, previous_position_time
    global total_distance_cm

    cap = cv2.VideoCapture(CAMERA_INDEX)

    if not cap.isOpened():
        print("Camera could not be opened.")
        return

    background = cv2.createBackgroundSubtractorMOG2(
        history=300,
        varThreshold=40,
        detectShadows=False
    )

    print("Mini 4WD Camera + Lap Timer started.")
    print("Move the car across the blue finish line to test.")
    print("Press t = manual test lap")
    print("Press r = reset")
    print("Press q = quit")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Could not read camera image.")
                break

            now = time.perf_counter()
            height, width = frame.shape[:2]
            finish_x = width // 2

            mask = background.apply(frame)
            mask = cv2.medianBlur(mask, 5)

            contours, _ = cv2.findContours(
                mask,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE
            )

            detected_object = None
            largest_area = MIN_OBJECT_AREA

            for contour in contours:
                area = cv2.contourArea(contour)
                if area > largest_area:
                    x, y, w, h = cv2.boundingRect(contour)
                    detected_object = (x, y, w, h)
                    largest_area = area

            color_name = "Unknown"
            speed_cm_s = None
            distance_cm = None

            if detected_object is not None:
                x, y, w, h = detected_object
                center_x = x + w // 2
                center_y = y + h // 2

                roi = frame[y:y+h, x:x+w]
                if roi.size > 0:
                    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                    h_mean, s_mean, v_mean = hsv.mean(axis=(0, 1))

                    if v_mean < 50:
                        color_name = "Black"
                    elif s_mean < 40 and v_mean > 190:
                        color_name = "White"
                    elif s_mean < 40:
                        color_name = "Gray"
                    elif h_mean < 10 or h_mean >= 170:
                        color_name = "Red"
                    elif h_mean < 25:
                        color_name = "Orange"
                    elif h_mean < 35:
                        color_name = "Yellow"
                    elif h_mean < 85:
                        color_name = "Green"
                    elif h_mean < 130:
                        color_name = "Blue"
                    else:
                        color_name = "Other"

                cv2.rectangle(
                    frame, (x, y), (x+w, y+h), (0, 255, 0), 2
                )
                cv2.circle(
                    frame, (center_x, center_y), 5, (0, 0, 255), -1
                )

                current_side = "left" if center_x < finish_x else "right"

                crossed_line = (
                    previous_side is not None
                    and current_side != previous_side
                )

                if crossed_line and (
                    last_crossing_time is None
                    or now - last_crossing_time >= COOLDOWN_SECONDS
                ):
                    record_lap(now, color_name, speed_cm_s, distance_cm)

                previous_side = current_side
                previous_position = (center_x, center_y)
                previous_position_time = now

            cv2.line(
                frame, (finish_x, 0), (finish_x, height), (255, 0, 0), 2
            )

            cv2.putText(
                frame, f"Laps: {crossing_count}", (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2
            )
            cv2.putText(
                frame, f"Color: {color_name}", (20, 70),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2
            )
            cv2.putText(
                frame, "Speed: calibrate at school", (20, 105),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2
            )

            cv2.imshow("Mini 4WD Lap Timer", frame)

            key = cv2.waitKey(1) & 0xFF

            if key == ord("q") or key == 13:
                break
            if cv2.getWindowProperty("Mini 4WD Lap Timer", cv2.WND_PROP_VISIBLE) < 1:
                break

            elif key == ord("r"):
                reset_timer()
            elif key == ord("t"):
                # Manual test while the car is unavailable
                record_lap(time.perf_counter(), "Manual Test")

    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("System closed.")
        print(f"Results saved to: {CSV_FILE}")


if __name__ == "__main__":
    main()


import csv
import os
import time
from datetime import datetime

# ==========================================
# Mini 4WD Lap Timer Test System
# ==========================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(BASE_DIR, "mini4wd_results.csv")

lap_count = 0
start_time = None
last_lap_time = None
best_lap_time = None


# ==========================================
# Create CSV file
# ==========================================

def create_csv():
    if not os.path.exists(CSV_FILE):
        with open(
            CSV_FILE, "w", newline="", encoding="utf-8-sig"
        ) as file:
            writer = csv.writer(file)

            writer.writerow([
                "Date",
                "Lap",
                "Timestamp",
                "Lap_Time_sec",
                "Best_Lap_sec"
            ])


# ==========================================
# Start timer
# ==========================================

def start_timer():
    global start_time
    global lap_count
    global last_lap_time
    global best_lap_time

    start_time = time.perf_counter()
    lap_count = 0
    last_lap_time = None
    best_lap_time = None

    print("\nTimer started!")
    print("Press ENTER every time the car passes the finish line.")
    print("Press r to reset.")
    print("Press q to quit.\n")


# ==========================================
# Record a lap
# ==========================================

def record_lap():
    global lap_count
    global start_time
    global last_lap_time
    global best_lap_time

    if start_time is None:
        print("Please start the timer first.")
        return

    now = time.perf_counter()
    elapsed = now - start_time

    lap_count += 1

    if last_lap_time is None:
        lap_time = elapsed
    else:
        lap_time = elapsed - last_lap_time

    last_lap_time = elapsed

    if best_lap_time is None or lap_time < best_lap_time:
        best_lap_time = lap_time

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("--------------------------------")
    print(f"Lap: {lap_count}")
    print(f"Lap Time: {lap_time:.3f} seconds")
    print(f"Best Lap: {best_lap_time:.3f} seconds")

    with open(
        CSV_FILE, "a", newline="", encoding="utf-8-sig"
    ) as file:
        writer = csv.writer(file)

        writer.writerow([
            timestamp,
            lap_count,
            f"{elapsed:.3f}",
            f"{lap_time:.3f}",
            f"{best_lap_time:.3f}"
        ])

    print("Result saved to CSV.")


# ==========================================
# Main program
# ==========================================

def main():
    create_csv()

    print("====================================")
    print(" Mini 4WD Lap Timer Test System")
    print("====================================")
    print("ENTER = Start timer / Record lap")
    print("r     = Reset timer")
    print("q     = Quit program")

    while True:
        command = input("\nEnter command: ").strip().lower()

        if command == "q":
            print("Program closed.")
            break

        elif command == "r":
            start_timer()

        elif command == "":
            if start_time is None:
                start_timer()
            else:
                record_lap()

        else:
            print("Unknown command. Press ENTER, r, or q.")


if __name__ == "__main__":
    main()


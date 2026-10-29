const lapCountElement = document.getElementById("lapCount");
const currentLapElement = document.getElementById("currentLap");
const bestLapElement = document.getElementById("bestLap");
const speedElement = document.getElementById("speed");
const systemStatusElement = document.getElementById("systemStatus");
const lapHistoryElement = document.getElementById("lapHistory");

const startButton = document.getElementById("startButton");
const lapButton = document.getElementById("lapButton");
const stopButton = document.getElementById("stopButton");
const resetButton = document.getElementById("resetButton");
const exportButton = document.getElementById("exportButton");

let running = false;
let startTime = null;
let lastLapTime = null;
let timerInterval = null;
let lapCount = 0;
let bestLap = null;
let lapRecords = [];

function formatTime(seconds) {
    if (!Number.isFinite(seconds) || seconds < 0) {
        return "00.000";
    }

    return seconds.toFixed(3);
}

function updateClock() {
    const now = new Date();

    document.getElementById("currentClock").textContent =
        now.toLocaleTimeString();

    document.getElementById("currentDate").textContent =
        now.toLocaleDateString();
}

function updateTimerDisplay() {
    if (!running || startTime === null) {
        return;
    }

    const elapsed = (performance.now() - startTime) / 1000;
    const currentLap = lastLapTime === null
        ? elapsed
        : elapsed - lastLapTime;

    currentLapElement.textContent = formatTime(currentLap);
}

function startRace() {
    if (running) {
        return;
    }

    running = true;
    startTime = performance.now();
    lastLapTime = null;

    systemStatusElement.textContent = "DEMO RUNNING";
    startButton.disabled = true;
    lapButton.disabled = false;
    stopButton.disabled = false;

    timerInterval = setInterval(updateTimerDisplay, 50);
}

function recordLap() {
    if (!running || startTime === null) {
        return;
    }

    const elapsed = (performance.now() - startTime) / 1000;

    const lapTime = lastLapTime === null
        ? elapsed
        : elapsed - lastLapTime;

    lastLapTime = elapsed;
    lapCount++;

    if (bestLap === null || lapTime < bestLap) {
        bestLap = lapTime;
    }

    const record = {
        lap: lapCount,
        time: lapTime,
        best: bestLap,
        speed: "",
        status: "DEMO"
    };

    lapRecords.push(record);

    lapCountElement.textContent = lapCount;
    currentLapElement.textContent = formatTime(lapTime);
    bestLapElement.textContent = formatTime(bestLap);

    renderHistory();
}

function stopRace() {
    if (!running) {
        return;
    }

    running = false;

    if (timerInterval !== null) {
        clearInterval(timerInterval);
        timerInterval = null;
    }

    systemStatusElement.textContent = "DEMO STOPPED";
    startButton.disabled = false;
    lapButton.disabled = true;
    stopButton.disabled = true;
}

function resetRace() {
    stopRace();

    lapCount = 0;
    bestLap = null;
    lastLapTime = null;
    startTime = null;
    lapRecords = [];

    lapCountElement.textContent = "0";
    currentLapElement.textContent = "00.000";
    bestLapElement.textContent = "--.---";
    speedElement.textContent = "--";

    systemStatusElement.textContent = "SYSTEM READY";

    renderHistory();
}

function renderHistory() {
    lapHistoryElement.replaceChildren();

    if (lapRecords.length === 0) {
        const row = document.createElement("tr");
        const cell = document.createElement("td");

        cell.colSpan = 5;
        cell.className = "empty-state";
        cell.textContent = "No lap records yet. Start a demo session.";

        row.appendChild(cell);
        lapHistoryElement.appendChild(row);
        return;
    }

    for (const record of [...lapRecords].reverse()) {
        const row = document.createElement("tr");

        const values = [
            record.lap,
            `${formatTime(record.time)} sec`,
            `${formatTime(record.best)} sec`,
            record.speed || "Not calibrated",
            record.status
        ];

        for (const value of values) {
            const cell = document.createElement("td");
            cell.textContent = value;
            row.appendChild(cell);
        }

        lapHistoryElement.appendChild(row);
    }
}

function exportCSV() {
    if (lapRecords.length === 0) {
        alert("No lap records to export yet.");
        return;
    }

    const rows = [
        ["Lap", "Lap_Time_sec", "Best_Lap_sec", "Speed_cm_s", "Status"],
        ...lapRecords.map(record => [
            record.lap,
            record.time.toFixed(3),
            record.best.toFixed(3),
            record.speed,
            record.status
        ])
    ];

    const csvContent = rows
        .map(row => row.map(value => {
            const text = String(value);
            return `"${text.replaceAll('"', '""')}"`;
        }).join(","))
        .join("\r\n");

    const blob = new Blob(
        ["\uFEFF" + csvContent],
        { type: "text/csv;charset=utf-8;" }
    );

    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");

    link.href = url;
    link.download = "mini4wd_demo_results.csv";
    link.click();

    URL.revokeObjectURL(url);
}

startButton.addEventListener("click", startRace);
lapButton.addEventListener("click", recordLap);
stopButton.addEventListener("click", stopRace);
resetButton.addEventListener("click", resetRace);
exportButton.addEventListener("click", exportCSV);

updateClock();
setInterval(updateClock, 1000);
renderHistory();
async function updateCameraStatus() {
    try {
        const response = await fetch("/api/status");
        if (!response.ok) {
            throw new Error("API connection failed");
        }

        const data = await response.json();

        document.getElementById("lapCount").textContent =
            data.lap_count;

        document.getElementById("currentLap").textContent =
            Number(data.current_lap).toFixed(3);

        document.getElementById("bestLap").textContent =
            data.best_lap === null
                ? "--.---"
                : Number(data.best_lap).toFixed(3);

        document.getElementById("carColor").textContent =
            data.car_color || "UNKNOWN";

        document.getElementById("detectionStatus").textContent =
            data.status || "WAITING";

    } catch (error) {
        console.error("Camera status error:", error);
    }
}

updateCameraStatus();
setInterval(updateCameraStatus, 500);

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
(() => {
  const video = document.getElementById("browserCamera");
  const canvas = document.getElementById("cameraCanvas");
  const startBtn = document.getElementById("startCamera");
  const stopBtn = document.getElementById("stopCamera");
  const status = document.getElementById("cameraStatus");
  const lapDisplay = document.getElementById("browserLapCount");
  const lastLapDisplay = document.getElementById("browserLastLap");

  if (!video || !canvas || !startBtn || !stopBtn) return;

  const ctx = canvas.getContext("2d", {
    willReadFrequently: true
  });

  let stream = null;
  let running = false;
  let previousFrame = null;
  let lastLapTime = 0;
  let lapCount = 0;
  let lastMotionTime = 0;
  let animationId = null;

  const cooldownMs = 1500;
  const motionThreshold = 0.12;

  startBtn.addEventListener("click", startCamera);
  stopBtn.addEventListener("click", stopCamera);

  async function startCamera() {
    if (running) return;

    if (!navigator.mediaDevices?.getUserMedia) {
      status.textContent =
        "Camera is unavailable. Open this website using HTTPS.";
      return;
    }

    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: "environment" },
          width: { ideal: 640 },
          height: { ideal: 480 }
        },
        audio: false
      });

      video.srcObject = stream;
      await video.play();

      running = true;
      previousFrame = null;
      startBtn.disabled = true;
      stopBtn.disabled = false;
      status.textContent = "Camera running. Detecting motion...";

      detectMotion();
    } catch (error) {
      status.textContent =
        "Cannot open camera: " + error.message +
        ". Check browser camera permission.";
    }
  }

  function stopCamera() {
    running = false;

    if (animationId) {
      cancelAnimationFrame(animationId);
      animationId = null;
    }

    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      stream = null;
    }

    video.srcObject = null;
    previousFrame = null;
    startBtn.disabled = false;
    stopBtn.disabled = true;
    status.textContent = "Camera is stopped";
  }

  function detectMotion() {
    if (!running || video.readyState < 2) {
      if (running) animationId = requestAnimationFrame(detectMotion);
      return;
    }

    const width = 160;
    const height = 60;

    canvas.width = width;
    canvas.height = height;

    // Sample a narrow horizontal detection zone
    // across the middle of the video.
    const sourceX = video.videoWidth * 0.4;
    const sourceY = video.videoHeight * 0.45;
    const sourceWidth = video.videoWidth * 0.2;
    const sourceHeight = video.videoHeight * 0.1;

    ctx.drawImage(
      video,
      sourceX, sourceY, sourceWidth, sourceHeight,
      0, 0, width, height
    );

    const pixels = ctx.getImageData(
      0, 0, width, height
    ).data;

    const gray = new Uint8Array(width * height);

    for (let i = 0, p = 0; i < pixels.length; i += 4, p++) {
      gray[p] =
        0.299 * pixels[i] +
        0.587 * pixels[i + 1] +
        0.114 * pixels[i + 2];
    }

    if (previousFrame) {
      let changed = 0;

      for (let i = 0; i < gray.length; i++) {
        if (Math.abs(gray[i] - previousFrame[i]) > 35) {
          changed++;
        }
      }

      const motionRatio = changed / gray.length;
      const now = performance.now();

      if (motionRatio > motionThreshold) {
        lastMotionTime = now;

        if (now - lastLapTime > cooldownMs) {
          lapCount++;
          lastLapTime = now;

          lapDisplay.textContent = lapCount;
          lastLapDisplay.textContent =
            new Date().toLocaleTimeString();
          status.textContent =
            "Motion detected — Lap " + lapCount;
        }
      } else if (now - lastMotionTime > 2000) {
        status.textContent = "Camera running. Waiting for car...";
      }
    }

    previousFrame = gray;
    animationId = requestAnimationFrame(detectMotion);
  }
})();

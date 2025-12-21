from fastapi import FastAPI
from pydantic import BaseModel
import psutil
import time
import threading
import statistics
import random
import smtplib
from email.message import EmailMessage
from typing import List

# ================== CONFIG ==================
EMAIL_SENDER = "masculinedivine1@gmail.com"       # <-- change
EMAIL_PASSWORD = "jcjhymwnrfkrhlva"  # <-- change
EMAIL_RECEIVER = "masculinedivine1@gmail.com"     # <-- change

COLLECT_INTERVAL = 10  # seconds

# ============================================

app = FastAPI(title="Cloud Monitoring Backend")

# ---------------- DATA MODEL ----------------
class Metric(BaseModel):
    timestamp: float
    node_id: str
    cpu: float
    memory: float
    disk: float

class Alert(BaseModel):
    timestamp: float
    level: str
    message: str

# ---------------- STORAGE ----------------
METRICS_DB: List[Metric] = []
ALERT_HISTORY: List[Alert] = []

NODES = ["vm-1", "vm-2", "vm-3"]

LAST_EMAIL_TIME = 0
EMAIL_COOLDOWN = 120  # seconds

# ---------------- EMAIL FUNCTION ----------------
def send_email(subject, body):
    global LAST_EMAIL_TIME

    if time.time() - LAST_EMAIL_TIME < EMAIL_COOLDOWN:
        return

    msg = EmailMessage()
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
        LAST_EMAIL_TIME = time.time()
    except Exception as e:
        print("Email error:", e)

# ---------------- Z-SCORE ----------------
def z_score(values, current):
    if len(values) < 5:
        return 0
    mean = statistics.mean(values)
    std = statistics.stdev(values)
    if std == 0:
        return 0
    return abs((current - mean) / std)

# ---------------- METRIC COLLECTOR ----------------
def collect_metrics():
    while True:
        for node in NODES:
            cpu = psutil.cpu_percent() + random.uniform(-5, 5)
            memory = psutil.virtual_memory().percent + random.uniform(-5, 5)
            disk = psutil.disk_usage("/").percent + random.uniform(-3, 3)

            metric = Metric(
                timestamp=time.time(),
                node_id=node,
                cpu=round(max(0, min(cpu, 100)), 2),
                memory=round(max(0, min(memory, 100)), 2),
                disk=round(max(0, min(disk, 100)), 2),
            )

            METRICS_DB.append(metric)

            if len(METRICS_DB) > 1000:
                METRICS_DB.pop(0)

        time.sleep(COLLECT_INTERVAL)

# ---------------- ANOMALY CHECK ----------------
def check_anomaly():
    while True:
        if len(METRICS_DB) < 20:
            time.sleep(5)
            continue

        recent = METRICS_DB[-30:]
        latest = METRICS_DB[-1]

        cpu_vals = [m.cpu for m in recent]
        mem_vals = [m.memory for m in recent]
        disk_vals = [m.disk for m in recent]

        cpu_z = z_score(cpu_vals, latest.cpu)
        mem_z = z_score(mem_vals, latest.memory)
        disk_z = z_score(disk_vals, latest.disk)

        anomaly_score = max(cpu_z, mem_z, disk_z)

        if anomaly_score >= 2.5:
            level = "CRITICAL"
            msg = f"""
CRITICAL ANOMALY DETECTED

Node: {latest.node_id}
CPU: {latest.cpu}%
Memory: {latest.memory}%
Disk: {latest.disk}%

Z-Scores:
CPU: {round(cpu_z,2)}
Memory: {round(mem_z,2)}
Disk: {round(disk_z,2)}
"""
            ALERT_HISTORY.append(Alert(
                timestamp=time.time(),
                level=level,
                message=msg
            ))

            send_email("🚨 CRITICAL SYSTEM ALERT", msg)

        time.sleep(10)

# ---------------- API ROUTES ----------------
@app.get("/")
def root():
    return {"message": "Cloud Monitoring Backend Running"}

@app.get("/metrics")
def get_metrics():
    return METRICS_DB

@app.get("/metrics/{node_id}")
def get_node_metrics(node_id: str):
    return [m for m in METRICS_DB if m.node_id == node_id]

@app.get("/status")
def system_status():
    if len(METRICS_DB) < 10:
        return {"status": "Collecting data"}

    recent = METRICS_DB[-30:]
    latest = METRICS_DB[-1]

    cpu_vals = [m.cpu for m in recent]
    mem_vals = [m.memory for m in recent]
    disk_vals = [m.disk for m in recent]

    score = max(
        z_score(cpu_vals, latest.cpu),
        z_score(mem_vals, latest.memory),
        z_score(disk_vals, latest.disk),
    )

    if score < 1.5:
        status = "Normal"
    elif score < 2.5:
        status = "Warning"
    else:
        status = "Critical"

    return {
        "status": status,
        "anomaly_score": round(score, 2)
    }

@app.get("/alerts")
def get_alerts():
    return ALERT_HISTORY

# ---------------- START THREADS ----------------
threading.Thread(target=collect_metrics, daemon=True).start()
threading.Thread(target=check_anomaly, daemon=True).start()

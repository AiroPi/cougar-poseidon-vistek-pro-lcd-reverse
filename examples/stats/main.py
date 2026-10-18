import cougar_lcd
import subprocess
import io
import time
from overlay_svg import get_svg, convert_svg
import psutil
from pynvml import *
from pathlib import Path

nvmlInit()
handle = nvmlDeviceGetHandleByIndex(0)
screen = cougar_lcd.CougarLCD()

screen.connect()
screen.resume()

psutil.cpu_percent()

def get_stats():
    s = time.time()
    cpu_percent = psutil.cpu_percent()
    mem = psutil.virtual_memory()
    nvml_util = nvmlDeviceGetUtilizationRates(handle)
    gpu_mem = nvmlDeviceGetMemoryInfo(handle)
    gpu_temp = nvmlDeviceGetTemperature(handle, NVML_TEMPERATURE_GPU)

    temps = psutil.sensors_temperatures()
    cpu_temp = next(s.current for s in temps["k10temp"] if s.label == "Tctl")

    return {
        "cpu_percent": round(cpu_percent),
        "cpu_temp": round(cpu_temp),
        "gpu_percent": round(nvml_util.gpu),
        "gpu_temp": round(gpu_temp)
    }

screen.send_png(Path.home() / ".config/cougar-lcd/background.png")
while True:
    stats = get_stats()
    svg = get_svg(stats)
    png = convert_svg(svg)

    screen.send_osd(io.BytesIO(png))
    time.sleep(1)

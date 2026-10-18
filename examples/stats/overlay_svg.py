from lxml import etree
import subprocess
from random import randint
import time
from pathlib import Path


with (Path.home() / ".config/cougar-lcd/template.svg").open() as f:
    tree = etree.parse(f)

ns = "{http://www.w3.org/2000/svg}"
frame = tree.getroot().xpath(".//svg:g[@id='Frame 1']", namespaces={"svg": "http://www.w3.org/2000/svg"})

def get_svg(stats):
    for e in frame[0]:
        id_ = e.get("id")
        if not id_:
            continue
    
        if id_.startswith("GPU TEMP"):
            span = next(iter(e))
            span.text = f"{stats['gpu_temp']}°"
        if id_.startswith("CPU TEMP"):
            span = next(iter(e))
            span.text = f"{stats['cpu_temp']}°"
        if id_.startswith("GPU USAGE"):
            span = next(iter(e))
            span.text = f"{stats['gpu_percent']}%"
        if id_.startswith("CPU USAGE"):
            span = next(iter(e))
            span.text = f"{stats['cpu_percent']}%"

    return etree.tostring(tree)

def convert_svg(svg: bytes):
    config_path = (Path.home() / ".config/cougar-lcd/").absolute()
    font_path = config_path / "StickNoBills-ExtraBold.ttf"
    process = subprocess.Popen(["resvg", "-", "-c", "--use-font-file", str(font_path), "--resources-dir", str(config_path)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    png_bytes, error = process.communicate(input=svg)

    if error:
        print(f"Error: {error.decode('utf-8')}")


    return png_bytes


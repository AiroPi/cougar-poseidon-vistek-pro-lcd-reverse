# cougar-poseidon-vistek-pro-lcd-reverse

Because the Cougar LCD Editor was only available on Windows, my POSEIDON VISTEK PRO ARGB wasn't working at all in my linux system.
I had to find a solution to have it working, and a Windows VM on my Linux was not a consideration.

This repo contains an unofficial protocol description to communicate with this product throught USB.

---

## Supported Products

|Model|Vendor USB ID|Product USB ID|
|-|-|-|
|Poseidon Vistek Pro ARGB|1D6B|0110|
|CFV235 Vision screen (not tested)|?|?|

## USB packets

The communication with the SCREEN device is made through USB.

### Normal packet

| Prefix | Length | Data | Checksum | Suffix |
|-|-|-|-|-|
| 1 byte | 2 bytes | ... | 1 byte | 1 byte |

| Part | Length | Description | Example |
| - | - | - | - |
| Prefix | 1 byte | Start delimiter | `Ox5a` |
| Length | 2 bytes | This is the **total** number of **bytes** in the packet. It must be exactly egal. <br> ⚠️ Sometimes it seems to be 1 byte bigger, the exact behavior needs to be determined. | `0x006c` if packet length is 108 |
| Data | x bytes | ASCII-encoded structured data to send/receive from the screen. Check bellow | `...` |
| Checksum | 1 byte | Sum of all bytes in "Length" + "Data" % 256 | `0xfa` |
| Suffix | 1 byte | End delimiter | `Ox5a` |


Packets data are structured as method & command + headers + content like this:

```
METHOD command
Header1=data
Header2=data

content
```

The line separator is `\r\n` (`\n` seems to be working for some requests).

Headers are:
| Header name | Optional | Value |
| - | - | - |
| Date | Yes (but recommanded) | Timestamp in milliseconds |
| SeqNumber | Yes (but recommanded) | Incremental number to identify the response |
| ContentType | Yes | If content is present, the type of the content (`json`) |
| Content Length | Yes | If content is present, the length of the content |

Commands are:
| Command | Method | Description | Content Example | Response Example |
|-|-|-|-|-|
| conn 1 | POST | Init the connection & ask for display informations | none | json `{"attribute": ["Status","Fan","Pump"] ,"OS": "Linux", "productId": "1", "version": {"app": "V1.0.3", "firmware":"V1.2.7", "hardware":"V2.0"}, "space": 82076, "brightness": 100, "degree": 0, "sn": "BY[L2520WC07AM001556", "osdState":0, "mode":0, "logo":2, "timeout": 60}` |
| all 1 | STATE | Send status informations data to the screens (seems no used by Poseidon Vistek Pro) | json `{"network": {"upload": 256, "download": 68}, "memory": {"total": 32304, "used": 11754, "load": 36, "temperature": 0, "speed": 3000}, "cpu": {"load": 11, "temperature": 44, "speedAverage": 4396, "power": 22, "voltage": 1.115, "usage": 10}, "gpu": {"load":4, "temperature":40, "fan":0, "speed":630, "power":14, "voltage": 0.825}, "disk": {"total": 1862, "used": 746, "load": 40, "activity": 0, "temperature": 0, "readSpeed": 0, "writeSpeed": 0}, "fans": [{"onBoard": true, "type": "Chassis", "name": "Fan System 1", "value": 612}, {"onBoard": true, "type": "Pump", "name": "PUMP SYS1", "value": 2771}], "motherboard": {"temperature": 38}, "timestamp": 1769170957389}` | none |
| power 1 | POST | Control power state | json `{"event": "resume"}` | none (ACK) |
| transport 1 | POST | Init an image send request | json `{"type": "media", "fileSize": 10692, "fileName": "720X720.png"}` | json `{"state": "success", "blockMaxSize": 1024}` |
| transported 1 | POST | End image send request | json `{"md5": "todo", "fileName": "720X720.png"}` | json `{"state": "success"}` |
| brightness 1 | POST | Set the brightness | json `{"value": 100}` | none (ACK) |
| rotate 1 | POST | Set the rotation | json `{"degree": 0}` | none (ACK) |
| osdState 1 | POST | Toggle the "osd overlay" | json `{"enable": false}` | none (ACK) |

### Normal packet reply structure

Packets data are structured as nb? & status code + headers + content like this:
```
nb status_code
Header1=value

content
```

`nb` is always "1".
`status_code` can be "200" for success, or "400" for (?) and probably other values.

Headers are:
| Header name | Value |
| - | - |
| AckNumber | Request SeqNumber + 1 |
| ContentType | If content is present, the type of the content (`json`) |
| Content Length | If content is present, the length of the content |

### File transfert packet

Between transport and transported packets, raw file data is send.

#TODO

## How widget overlay works ?

Even if there is a packet type to send all the computer stats to the LCD (CPU usage, CPU temp, network, GPU...), this is NOT the method the data are displayed on screen.
In fact, the LCD contains a `.png` or `.mp4` image (sent using transport/transported commands) that is displayed in the "background", and it regularly receives a `.osd` image (that is just a PNG file with transparent backgroud) that is displayed in the "foreground".

This means that we can't just send the statistics, we needs to generate the foreground image.

Apart from that, it is pretty simple to display dynamic data on screen :)

## How to test

The `cougar_lcd_controller.py` library contains implementation in python to send things to the display. You will need to install `pyusb`.

For example:
```py
cougar_lcd = CougarLCD()
cougar_lcd.connect()
cougar_lcd.resume()
cougar_lcd.send_png("demo.png")
```
(Or simply run `python cougar_lcd_controller.py`)

Send images in the right dimensions.

There is also other examples to send a template to the screen with an overlay.

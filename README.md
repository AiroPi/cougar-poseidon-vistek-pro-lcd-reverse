# cougar-poseidon-vistek-pro-lcd-reverse

Because the Cougar LCD Editor was only available on Windows, my POSEIDON VISTEK PRO ARGB wasn't working at all in my linux.
I had to find a solution to have it working, and a Windows VM on my Linux was not a condideration.

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

#### Prefix & Suffix

The prefix and suffix is always the same byte : `Ox5a`

#### Length

This is the **total** number of **bytes** in the packet. It must be exactly egal.

⚠️ Sometimes it seems to be 1 byte bigger, the exact behavior needs to be determined.

#### Data

ASCII-encoded structured data to send/receive from the screen. Mode details later.

#### Checksum

Sum of all bytes in "Length" + "Data" % 25

### Normal packet data

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
| Date | Probably not | Timestamp in milliseconds |
| SeqNumber | Probably not | Incremental number to identify the response |
| ContentType | Yes | If content is present, the type of the content. Known values : "json" |
| Content Length | Yes | If content is present, the length of the content |

Commands are:
| Command | Method | Description | Content | Example |
|-|-|-|-|-|
| conn 1 | POST | Init the connection & ask for display informations | none | none |
| all 1 | STATE | Send status informations data to the screens (seems no used by Poseidon Vistek Pro) | ... | |
| power 1 | POST | Control power state | json `{"event": Literal["resume"]}` | `{"event":"resume"}` |
| transport 1 | POST | Init an image send request | json `{"type": Literal["media"], "fileSize": int, "fileName": str}` | `{"type":"media","fileSize":10692,"fileName":"720X720.png"}` |
| transported 1 | POST | End image send request | json `{"md5": Literal["todo"], "fileName": str}` | `{"md5":"todo","fileName":"720X720.png"}` |
| brightness 1 | POST | Set the brightness | json `{"value": int}` | `{"value":100}` |
| rotate 1 | POST | Set the rotation | json `{"degree": int}` | `{"degree":0}` |
| osdState 1 | POST | Toggle the "osd overlay" | json `{"enable": bool}` | `{"enable":false}` |

### File transfert packet

Between transport and transported packets, raw file data is send.

#TODO

## How widget overlay works ?

Even if there is a packet type to send all the computer stats to the LCD (CPU usage, CPU temp, network, GPU...), this is NOT the method the data are displayed on screen.
In fact, the LCD contains a `.png` or `.mp4` image (sent using transport/transported commands) that is displayed in the "background", and it regularly receives a `.osd` image (that is just a PNG file with transparent backgroud) that is displayed in the "foreground".

This means that we can't just send the statistics, we needs to generate the foreground image.

Apart from that, it is pretty simple to display dynamic data on screen :)

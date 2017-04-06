# Pi-Wetterstation
Wetterstation mit Raspberry Pi, Sensortag und kleinem Bildschirm, um die aktuellen Werte anzuzeigen.

## Setup

```bash
# installieren der benötigten Packete und Librarys
sudo apt install python-pip virtualenvwrapper libglib2.0-dev python-dev python3-dev
mkvirtualenv wetterstation  # OPTIONAL: virtualenv erstellen
pip install bluepy adafruit-io ZODB
```
## Sourcen
http://www.instructables.com/id/Raspberry-Pi-Internet-Weather-Station/?ALLSTEPS

https://github.com/yxtay/raspberry-pi-sensortag

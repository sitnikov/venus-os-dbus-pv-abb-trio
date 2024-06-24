# Driver for ABB TRIO PV Inverter for Cerbo / Cerbo GX / Victron Venus OS over sunspec protocol

This project is a Python application that implements ABB Trio PV Inverter for Victron Venus OS

## Requirements
- Python 3.8 or higher
- pysunspec package
 
## Getting Started

Install to /data/dbus-pv-abb-trio directory on your Cerbo / Cerbo GX / Victron Venus OS device.

## Config
Copy or rename the config.sample.ini to config.ini in the dbus-pv-abb-trio folder and change it as you need it.

## Install service
```
Run /data/dbus-pv-abb-trio/install.sh script to install service.
```

## Uninstall service
```
Run data/dbus-pv-abb-trio/uninstall.sh script to uninstall service.
```

## Restart service
```
Run /data/dbus-pv-abb-trio/restart.sh script to restart service.
```

## Testings
Run
```bash
opkg update && opkg install python3-pip
python -m pip install sunspecs

python /usr/bin/suns.py -a 247 -i <ipaddress>
or
python /usr/bin/suns.py -a 2 -i <ipaddress>
...
```
Output most be like as this

```
model: Common (1)
       Manufacturer (Mn):                            Power-One
       Model (Md):                                      -3M97-
       Options (Opt):                                        r
       Version (Vr):                                      CAA8
       Serial Number (SN):                    113987-3M97-2119
 model: Inverter (Three Phase) (103)
       Amps (A):                                          0.34 A
       Amps PhaseA (AphA):                                0.34 A
       Amps PhaseB (AphB):                                 0.0 A
       Amps PhaseC (AphC):                                0.24 A
       Phase Voltage AB (PPVphAB):          397.70000000000005 V
       Phase Voltage BC (PPVphBC):                       402.3 V
       Phase Voltage CA (PPVphCA):          400.70000000000005 V
       Phase Voltage AN (PhVphA):           230.70000000000002 V
       Phase Voltage BN (PhVphB):                        230.8 V
       Phase Voltage CN (PhVphC):                        232.8 V
       Watts (W):                                           63 W
       Hz (Hz):                                          50.01 Hz
       WattHours (WH):                                18050862 Wh
       DC Watts (DCW):                                      75 W
       Cabinet Temperature (TmpCab):                      31.8 C
       Other Temperature (TmpOt):                         32.1 C
       Operating State (St):                                 4
       Vendor Operating State (StVnd):                       6
       Event1 (Evt1):                               0x00000000
       Event Bitfield 2 (Evt2):                     0x00000000
   ```

#!/usr/bin/env python
from gi.repository import GLib  # pyright: ignore[reportMissingImports]
import platform
import logging
import sys
import os
from time import sleep
from typing import Optional
import configparser
import _thread
import sunspec.core.client as client

# import Victron Energy packages
sys.path.insert(1, os.path.join(os.path.dirname(__file__), 'ext', 'velib_python'))
from vedbus import VeDbusService


# get values from config.ini file
def check_config(data):
    if 'PV' not in data:
        raise configparser.NoSectionError("PV section not found in config")

    for key in ['slave_addr', 'ipaddr', 'ipport', 'timeout', 'name', 'instance']:
        if not data.has_option('PV', key):
            raise configparser.NoOptionError(key, 'PV')


config_file = (os.path.dirname(os.path.realpath(__file__))) + "/config.ini"

if not os.path.exists(config_file):
    logging.critical("The \"" + config_file + "\" is not found. The driver restarts in 60 seconds.")
    sleep(60)
    sys.exit()

config: Optional[configparser.ConfigParser] = None

try:
    config = configparser.ConfigParser()
    config.read(config_file)
    check_config(config)
except configparser.NoSectionError as e:
    logging.critical(f"Configuration error: {e}")
    sleep(60)
    sys.exit()
except configparser.NoOptionError as e:
    logging.critical(f"Configuration error: {e}")
    sleep(60)
    sys.exit()
except Exception:
    exception_type, exception_object, exception_traceback = sys.exc_info()
    file = exception_traceback.tb_frame.f_code.co_filename
    line = exception_traceback.tb_lineno
    logging.critical(f"Exception occurred: {repr(exception_object)} of type {exception_type} in {file} line #{line}")
    logging.critical("ERROR: The driver restarts in 60 seconds.")
    sleep(60)
    sys.exit()

# Get logging level from config.ini
# ERROR = shows errors only
# WARNING = shows ERROR and warnings
# INFO = shows WARNING and running functions
# DEBUG = shows INFO and data/values
if 'DEFAULT' in config and 'logging' in config['DEFAULT']:
    if config['DEFAULT']['logging'] == 'DEBUG':
        logging.basicConfig(level=logging.DEBUG)
    elif config['DEFAULT']['logging'] == 'INFO':
        logging.basicConfig(level=logging.INFO)
    elif config['DEFAULT']['logging'] == 'ERROR':
        logging.basicConfig(level=logging.ERROR)
    else:
        logging.basicConfig(level=logging.WARNING)
else:
    logging.basicConfig(level=logging.WARNING)


def read_sunspec_device(local_config):
    # sd = client.SunSpecClientDevice(client.TCP, config['PV']['slave_addr'], ipaddr=config['PV']['ipaddr'],
    #                               ipport=int(config['PV']['ipport']), timeout=float(config['PV']['timeout']))
    device = client.ClientDevice(client.TCP,
                                 slave_id=local_config['PV']['slave_addr'],
                                 ipaddr=local_config['PV']['ipaddr'],
                                 ipport=int(local_config['PV']['ipport']),
                                 timeout=float(local_config['PV']['timeout'])
                                 )

    if local_config.has_option('PV', 'base_addr'):
        device.base_addr_list = [int(local_config['PV']['base_addr'])]

    device.scan()
    device.read_points()

    result = {}

    for model in device.models_list:
        result['ModelID'] = {'label': model.model_type.label, 'value': model.id, 'units': ''}

        for block in model.blocks:
            for point in block.points_list:
                if point.value is not None:
                    units = point.point_type.units
                    if units is None:
                        units = ''

                    key = point.point_type.id
                    if units in ["A", "W", "V", "Hz", "C"]:
                        value = str(point.value).rstrip('\0')
                        value = round(float(value), 2)
                    elif key in ["St", "StVnd"]:
                        value = str(point.value).rstrip('\0')
                        value = int(value)
                    elif key == "WH":
                        value = str(point.value).rstrip('\0')
                        value = round(float(value) / 1000, 2)
                        key = "kWH"
                        units = "kWH"
                    else:
                        value = str(point.value).rstrip('\0')

                    result[key] = {'label': point.point_type.label, 'value': value, 'units': units}
    device.close()
    return result


values = read_sunspec_device(config)

if 'ModelID' not in values:
    logging.critical("No inverters found. Sleep 60 sec and Exiting.")
    sleep(60)
    sys.exit()


class DbusABBPvService:
    def __init__(self, servicename, deviceinstance, paths, productname='ABB-TRIO PV', customname='ABB-TRIO PV',
                 connection='ABB-TRIO PV VNS300'):

        self._dbusservice = VeDbusService(servicename)
        self._paths = paths

        logging.debug("%s /DeviceInstance = %d" % (servicename, deviceinstance))

        # Create the management objects, as specified in the ccgx dbus-api document
        self._dbusservice.add_path('/Mgmt/ProcessName', __file__)
        self._dbusservice.add_path('/Mgmt/ProcessVersion',
                                   'Unknown version, and running on Python ' + platform.python_version())
        self._dbusservice.add_path('/Mgmt/Connection', connection)

        # Create the mandatory objects
        self._dbusservice.add_path('/DeviceInstance', deviceinstance)
        self._dbusservice.add_path('/ProductId', 0xFFFF)

        # Md: {'label': 'Model', 'units': '', 'value': '-3M97-'},
        # Mn: {'label': 'Manufacturer', 'units': '', 'value': 'Power-One'},
        self._dbusservice.add_path('/ProductName', productname)

        self._dbusservice.add_path('/CustomName', customname)
        self._dbusservice.add_path('/FirmwareVersion', values['Vr']['value'])

        # self._dbusservice.add_path('/HardwareVersion', '')
        self._dbusservice.add_path('/Connected', 1, writeable=True)

        self._dbusservice.add_path('/Latency', None)

        # only needed for pvinverter
        self._dbusservice.add_path('/Position', int(config['PV']['position']))

        # moved to paths
        #self._dbusservice.add_path('/StatusCode', self._sunspec_status_code_convert(3))

        # 0 = No Error
        # For Victron devices/services the ErrorCode path should be used.
        # For thirdparty devices the /Error/n/Id path should be used
        # https://github.com/victronenergy/venus/wiki/dbus#generic-paths
        # The format of the /Error/n/Id payload is as follows: man:[ewi]-code.
        # Where man is the manufacturer, [ewi] can be used to indicate the level of the alarm (e=error, w=warning,
        # i=informational), and code is the device specific error code/id as found in the manual or on a display of the
        # third party device
        # If there is no error, the code should be an empty string without manufacturer prefix, i.e. "".
        # self._dbusservice.add_path('/ErrorCode', 0)
        self._dbusservice.add_path('/Error/0/Id', "")

        for path, settings in self._paths.items():
            self._dbusservice.add_path(
                path, settings['initial'], gettextcallback=settings['textformat'], writeable=True,
                onchangecallback=self._handlechangedvalue
            )

        GLib.timeout_add(1000, self._update)  # pause 1000ms before the next request

    # StatusCode
    # 0 = Startup, 1 = Startup, 2 = Startup, 3 = Startup, 4 = Startup, 5 = Startup
    # 6 = Startup, 7 = Running, 8 = Standby, 9 = Boot, 10 = Error
    #
    # St: 'label': 'Operating State', 'units': '', 'value': '4'
    # 1 = Off
    # 2 = Sleeping(auto - shutdown)
    # 3 = Starting up
    # 4 = Tracking power point
    # 5 = Forced power reduction
    # 6 = Shutting down
    # 7 = One or more faults exist
    # 8 = Standby(service on unit)*might be in Events
    def _sunspec_status_code_convert(self, code):
        if code == 2 or code == 8:
            return 8
        elif code == 4:
            return 7
        elif code == 7:
            return 10
        else:
            return 0

    def _update(self):
        global values

        values = read_sunspec_device(config)

        if 'ModelID' not in values:
            logging.critical("ERROR: No compatible inverters found. Sleep 60 sec and Exiting.")
            sleep(60)
            sys.exit()

        for k, v in values.items():
            if v['units']:
                logging.debug(f"values: {v['label']} ({k}) to {v['value']} {v['units']}")
            else:
                logging.debug(f"values: {v['label']} ({k}) to {v['value']}")

        for path, settings in self._paths.items():
            v = None
            if 'sunspec' in settings and settings['sunspec'] in values:
                v = values[settings['sunspec']]['value']
            elif path in ['/Ac/L1/Power', '/Ac/L2/Power', '/Ac/L3/Power']:
                v = round(values['Aph' + settings['ph']]['value'] * values['PhVph' + settings['ph']]['value'], 2)
            elif path in ['/Ac/L1/Energy/Forward', '/Ac/L2/Energy/Forward', '/Ac/L3/Energy/Forward']:
                v = round(values['kWH']['value'] / 3, 2)
            elif path == '/StatusCode':
                v = self._sunspec_status_code_convert(values['St']['value'])

            if v is not None:
                logging.debug("Set {0} => {1}".format(path, v))
                self._dbusservice[path] = v

        err_code = ""
        if values['St']['value'] == 7:
            err_code = "e-{:#08d}".format(values['Evt1']['value'])

        logging.debug("Set {0} = {1}".format('/Error/0/Id', err_code))
        self._dbusservice['/Error/0/Id'] = err_code

        # increment UpdateIndex - to show that new data is available
        update_index = self._dbusservice['/UpdateIndex'] + 1  # increment index
        if update_index > 255:  # maximum value of the index
            update_index = 0  # overflow from 255 to 0

        self._dbusservice['/UpdateIndex'] = update_index

        return True

    def _handlechangedvalue(self, path, value):
        logging.debug("someone else updated %s to %s" % (path, value))
        return True  # accept the change


def main():
    _thread.daemon = True  # allow the program to quit

    from dbus.mainloop.glib import DBusGMainLoop

    # Have a mainloop, so we can send/receive asynchronous calls to and from dbus
    DBusGMainLoop(set_as_default=True)

    # formatting
    def _kwh(p, v):
        return (str("%.2f" % v) + "kWh")

    def _a(p, v):
        return (str("%.1f" % v) + "A")

    def _w(p, v):
        return (str("%i" % v) + "W")

    def _v(p, v):
        return (str("%.2f" % v) + "V")

    def _hz(p, v):
        return (str("%.4f" % v) + "Hz")

    def _n(p, v):
        return (str("%i" % v))

    paths_dbus = {
        '/Ac/Power': {'initial': 0, 'textformat': _w, 'sunspec': 'W'},
        '/Ac/Current': {'initial': 0, 'textformat': _a, 'sunspec': 'A'},
        # deprecated
        # '/Ac/Voltage': {'initial': 0, 'textformat': _v, 'sunspec': ''},
        '/Ac/Energy/Forward': {'initial': 0, 'textformat': _kwh, 'sunspec': 'kWH'},

        '/Ac/MaxPower': {'initial': int(config['PV']['max']), 'textformat': _w},
        '/Ac/Position': {'initial': int(config['PV']['position']), 'textformat': _n},

        '/StatusCode': {'initial': 0, 'textformat': _n},
        '/UpdateIndex': {'initial': 0, 'textformat': _n},
    }

    paths_dbus.update({
        '/Ac/L1/Power': {'initial': 0, 'textformat': _w, 'ph': 'A'},
        '/Ac/L1/Current': {'initial': 0, 'textformat': _a, 'sunspec': 'AphA'},
        '/Ac/L1/Voltage': {'initial': 0, 'textformat': _v, 'sunspec': 'PhVphA'},
        '/Ac/L1/Frequency': {'initial': 0, 'textformat': _hz, 'sunspec': 'Hz'},
        '/Ac/L1/Energy/Forward': {'initial': 0, 'textformat': _kwh},
    })

    paths_dbus.update({
        '/Ac/L2/Power': {'initial': 0, 'textformat': _w, 'ph': 'B'},
        '/Ac/L2/Current': {'initial': 0, 'textformat': _a, 'sunspec': 'AphB'},
        '/Ac/L2/Voltage': {'initial': 0, 'textformat': _v, 'sunspec': 'PhVphB'},
        '/Ac/L2/Frequency': {'initial': 0, 'textformat': _hz, 'sunspec': 'Hz'},
        '/Ac/L2/Energy/Forward': {'initial': 0, 'textformat': _kwh},
    })

    paths_dbus.update({
        '/Ac/L3/Power': {'initial': 0, 'textformat': _w, 'ph': 'C'},
        '/Ac/L3/Current': {'initial': 0, 'textformat': _a, 'sunspec': 'AphC'},
        '/Ac/L3/Voltage': {'initial': 0, 'textformat': _v, 'sunspec': 'PhVphC'},
        '/Ac/L3/Frequency': {'initial': 0, 'textformat': _hz, 'sunspec': 'Hz'},
        '/Ac/L3/Energy/Forward': {'initial': 0, 'textformat': _kwh},
    })

    DbusABBPvService(servicename='com.victronenergy.pvinverter.pv_abb_trio_' + str(config['PV']['instance']),
                     deviceinstance=int(config['PV']['instance']), paths=paths_dbus,
                     customname=config['PV']['name'])

    logging.info('Connected to dbus and switching over to GLib.MainLoop() (= event based)')
    mainloop = GLib.MainLoop()
    mainloop.run()


if __name__ == "__main__":
    main()

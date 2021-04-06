#!/usr/bin/python
# coding=utf-8
#

import sys
import os
import subprocess
import argparse
import syslog
import dbus
import dbus.mainloop.glib

PY_MAJOR_VER = sys.version_info[0]
PY2 = PY_MAJOR_VER == 2

if PY2:
    if sys.hexversion < 0x2070000:
        raise ImportError('Python >= 2.7 is required')
    import gobject
else:
    from gi.repository import GLib

here = os.path.dirname(os.path.abspath(__file__))

# To get names of current connman technologies you can use:
# connmanctl technologies | awk '/Type/ { print $NF }'
technologies = ['wifi', 'ethernet']
runOn = {
    'post-connect': None,
    'post-disconnect': None,
}

_services = {}

def runInShell(cmd):
    syslog.syslog("running command: %s" % cmd)
    try:
        output = subprocess.check_output(cmd, shell = True)
    except subprocess.CalledProcessError as ex:
        syslog.syslog(ex)
        sys.exit(ex.returncode)
    syslog.syslog(output.decode(sys.stdout.encoding))

def handleServicePropSignal(name, value, path):
    name = str(name)
    if name != 'State':
        return

    if path not in _services:
        _services[path] = {}
    sinfo = _services[path]
    sinfo['connected'] = str(value) in ('ready', 'online')
    sinfo['changed'] = True

def handleTechSignal(paramName, paramVal):

    connected = bool(paramVal)
    if connected:
        cmd = runOn['post-connect']
    else:
        cmd = runOn['post-disconnect']

    if not cmd:
        return

    bus = dbus.SystemBus()
    manager = dbus.Interface(bus.get_object("net.connman", "/"),
                                            "net.connman.Manager")
    services = manager.GetServices()
    for service in services:
        path = str(service[0])
        if path not in _services:
            # it's not active service
            continue

        sinfo = _services[path]
        if not sinfo['changed']:
            # state was not changed
            continue

        serviceConnected = sinfo['connected']
        if serviceConnected == connected:
            name = str(service[1]["Name"])
            contype = str(service[1]["Type"])
            cmd += " %s %s" % (contype, name)
            runInShell(cmd)

        sinfo['changed'] = False

def run():

    dbus.mainloop.glib.DBusGMainLoop(set_as_default = True)

    bus = dbus.SystemBus()

    for technology in technologies:
        bus.add_signal_receiver(
            handleTechSignal,
            signal_name    = "PropertyChanged",
            dbus_interface = "net.connman.Technology",
            path           = "/net/connman/technology/%s" % technology,
            arg0           = "Connected"
        )

    bus.add_signal_receiver(
        handleServicePropSignal,
        bus_name       = "net.connman",
        dbus_interface = "net.connman.Service",
        signal_name    = "PropertyChanged",
        path_keyword   = "path",
    )

    if PY2:
        mainloop = gobject.MainLoop()
    else:
        mainloop = GLib.MainLoop()
    mainloop.run()

def main():

    parser = argparse.ArgumentParser(
        formatter_class = argparse.RawTextHelpFormatter)
    parser.add_argument('-C', '--postconnect', nargs = '?', default = None, \
        metavar = 'PATH_TO_SCRIPT', dest = 'postconnect',
        help = "path to script which will be called after connection")
    parser.add_argument('-D', '--postdisconnect', nargs = '?', default = None, \
        metavar = 'PATH_TO_SCRIPT', dest = 'postdisconnect',
        help = "path to script which will be called after disconnection")

    if len(sys.argv) == 1:
        parser.print_help()
        return 0

    args = parser.parse_args()

    runOn['post-connect']    = args.postconnect
    runOn['post-disconnect'] = args.postdisconnect

    for event, path in runOn.items():
        if not path:
            continue

        _path = path
        if not os.path.isfile(_path):
            # try to find existing paths

            _path = os.path.join(here, path)
            if not os.path.isfile(_path):
                _path = os.path.realpath(path)
                if not os.path.isfile(_path):
                    msg = "Path '%s' not found or not a file" % path
                    print(msg)
                    syslog.syslog(msg)
                    sys.exit(1)

        runOn[event] = _path

    run()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nInterrupted by keyboard')
        sys.exit(0)

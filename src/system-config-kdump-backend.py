#!/usr/bin/python

import gobject

import dbus
import dbus.service
import dbus.mainloop.glib

import os
try:
    # try to import the module installed in the system
    import slip.dbus.service
except ImportError:
    # try to find the module in the unpacked source tree
    import sys
    import os.path
    import import_marker

    # try to find the slip.dbus module

    modfile = import_marker.__file__
    path = os.path.dirname (modfile)
    found = False
    oldsyspath = sys.path
    while not found and path and path != "/":
        path = os.path.abspath (os.path.join (path, os.path.pardir))
        sys.path = oldsyspath + [path]
        try:
            import slip.dbus.service
            found = True
        except ImportError:
            pass
    if not found:
        import slip.dbus.service
    sys.path = oldsyspath

#######
GRUBBY_CMD        = "/sbin/grubby"
KDUMP_CONFIG_FILE = "/etc/kdump.conf"


#             bootloader : (config file, kdump offset, kernel path)
bootloaders = { "grub"   : ("/boot/grub/grub.conf", 16, "/boot"),
                "yaboot" : ("/boot/etc/yaboot.conf", 32, "/boot"),
                "elilo"  : ("/boot/efi/EFI/redhat/elilo.conf", 256, "/boot/efi/EFI/redhat") }




class systemConfigKdumpObject(slip.dbus.service.Object):
    def __init__ (self, *p, **k):
        super (systemConfigKdumpObject, self).__init__ (*p, **k)
        self.bootloader = self.setBootloader()


# Get default kernel name from grubby
    @slip.dbus.polkit.require_auth ("org.fedoraproject.systemconfig.kdump.getdefaultkernel")
    @dbus.service.method ("org.fedoraproject.systemconfig.kdump.mechanism",
                          in_signature='', out_signature='s')
    def getdefaultkernel (self):
        return os.popen(GRUBBY_CMD + " --default-kernel").read()

# Get command line arguments for kernel from grubby
    @slip.dbus.polkit.require_auth ("org.fedoraproject.systemconfig.kdump.getcmdline")
    @dbus.service.method ("org.fedoraproject.systemconfig.kdump.mechanism",
                          in_signature='s', out_signature='s')
    def getcmdline (self, kernel):
        for line in os.popen(GRUBBY_CMD + " --info " + kernel).readlines():
            (name, value) = line.strip().split("=",1)
            if name == "args":
                return value.strip('"')
        return ""

# Get all kernel names from grubby
    @slip.dbus.polkit.require_auth ("org.fedoraproject.systemconfig.kdump.getallkernels")
    @dbus.service.method ("org.fedoraproject.systemconfig.kdump.mechanism",
                          in_signature='', out_signature='s')
    def getallkernels (self):
        return os.popen(GRUBBY_CMD + " --info ALL").read()

# Write kdump configuration to /etc/kdump.conf
# and return what we write into kdump config file
    @slip.dbus.polkit.require_auth ("org.fedoraproject.systemconfig.kdump.writedumpconfig")
    @dbus.service.method ("org.fedoraproject.systemconfig.kdump.mechanism",
                          in_signature='s', out_signature='s')
    def writedumpconfig (self, configString):
        if os.access(KDUMP_CONFIG_FILE, os.W_OK):
            # make a minimal effort at backing up an existing config
            try:
                os.rename(KDUMP_CONFIG_FILE, KDUMP_CONFIG_FILE + ".backup")
            except:
                pass

        fd = open(KDUMP_CONFIG_FILE, "w")
        fd.write(configString)
        fd.close()

        # re-read
        return open(KDUMP_CONFIG_FILE).read()

# Write bootloader configuration
    @slip.dbus.polkit.require_auth ("org.fedoraproject.systemconfig.kdump.writebootconfig")
    @dbus.service.method ("org.fedoraproject.systemconfig.kdump.mechanism",
                          in_signature='s', out_signature='s')
    def writebootconfig (self, configString):
        what = os.popen(GRUBBY_CMD + " --" + self.bootloader + configString).read()
        return what


    def setBootloader(self):
        for (name, (conf, offset, kpath)) in bootloaders.items():
            # I hope order doesn't matter
            if os.access(conf, os.W_OK):
                self.bootloader = name

        if self.bootloader is None:
            return ""

        return self.bootloader




#    @slip.dbus.polkit.require_auth ("org.fedoraproject.systemconfig.kdump.write")
#    @dbus.service.method("org.fedoraproject.systemconfig.kdump.mechanism",
#                         in_signature='s', out_signature='')
#    def write (self, config_data):
#        print "%s.write ('%s')" % (self, config_data)

if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    bus = dbus.SystemBus ()

    name = dbus.service.BusName ("org.fedoraproject.systemconfig.kdump.mechanism", bus)
    object = systemConfigKdumpObject (bus, '/org/fedoraproject/systemconfig/kdump/object')

    mainloop = gobject.MainLoop ()
    slip.dbus.service.set_mainloop (mainloop)
    mainloop.run ()

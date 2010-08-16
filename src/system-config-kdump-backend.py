#!/usr/bin/python

import gobject

import dbus
import dbus.service
import dbus.mainloop.glib

import os
import slip.dbus.service
import subprocess


#######
GRUBBY_CMD        = "/sbin/grubby"
KDUMP_CONFIG_FILE = "/etc/kdump.conf"


# can be replaced by using booty?
#             bootloader : (config file, kdump offset, kernel path)
BOOTLOADERS = { "grub"   : ("/boot/grub/grub.conf", 16, "/boot"),
                "yaboot" : ("/boot/etc/yaboot.conf", 32, "/boot"),
                "elilo"  : ("/boot/efi/EFI/redhat/elilo.conf", 256, "/boot/efi/EFI/redhat") }

class SystemConfigKdumpObject(slip.dbus.service.Object):
    def __init__ (self, *p, **k):
        super (SystemConfigKdumpObject, self).__init__ (*p, **k)
        self.bootloader = self.set_bootloader()


    @slip.dbus.polkit.require_auth ("org.fedoraproject.systemconfig.kdump.getdefaultkernel")
    @dbus.service.method ("org.fedoraproject.systemconfig.kdump.mechanism",
                          in_signature='', out_signature='(iss)')
    def getdefaultkernel (self):
        """ Get default kernel name from grubby """
        return self.gtkcall(GRUBBY_CMD, "--default-kernel")


    @slip.dbus.polkit.require_auth ("org.fedoraproject.systemconfig.kdump.getcmdline")
    @dbus.service.method ("org.fedoraproject.systemconfig.kdump.mechanism",
                          in_signature='s', out_signature='(iss)')
    def getcmdline (self, kernel):
        """ Get command line arguments for kernel from grubby """
        (retcode, std, err) = self.gtkcall(GRUBBY_CMD, "--info", kernel)
        if retcode > 0:
            return (retcode, std, err)
        else:
            for line in std.splitlines():
                (name, value) = line.strip().split("=", 1)
                if name == "args":
                    return (retcode, value.strip('"'), err)

    @slip.dbus.polkit.require_auth ("org.fedoraproject.systemconfig.kdump.getxencmdline")
    @dbus.service.method ("org.fedoraproject.systemconfig.kdump.mechanism",
                          in_signature='s', out_signature='(iss)')
    def getxencmdline (self, kernel):
        """ Get command line arguments for xen kernel from grubby """
        (retcode, std, err) = self.gtkcall(GRUBBY_CMD, "--info", kernel)
        if retcode > 0:
            return (retcode, std, err)
        else:
            for line in std.splitlines:
                (name, value) = line.strip().split("=", 1)
                if name == "module":
                    return (retcode, value.strip('"'), err)

    @slip.dbus.polkit.require_auth ("org.fedoraproject.systemconfig.kdump.getallkernels")
    @dbus.service.method ("org.fedoraproject.systemconfig.kdump.mechanism",
                          in_signature='', out_signature='(iss)')
    def getallkernels (self):
        """ Get all kernel names from grubby """
        return self.gtkcall(GRUBBY_CMD,"--info", "ALL")

    @slip.dbus.polkit.require_auth ("org.fedoraproject.systemconfig.kdump.writedumpconfig")
    @dbus.service.method ("org.fedoraproject.systemconfig.kdump.mechanism",
                          in_signature='s', out_signature='(is)')
    def writedumpconfig (self, config_string):
        """ Write kdump configuration to /etc/kdump.conf
            and return what we write into kdump config file """
        try:
            fd = open(KDUMP_CONFIG_FILE, "w")
            fd.write(config_string)
            fd.close()
        except IOError,(errno, strerror):
            return (errno, strerror)

        # re-read
        return (0, open(KDUMP_CONFIG_FILE).read())

    @slip.dbus.polkit.require_auth ("org.fedoraproject.systemconfig.kdump.writebootconfig")
    @dbus.service.method ("org.fedoraproject.systemconfig.kdump.mechanism",
                          in_signature='s', out_signature='(iss)')
    def writebootconfig (self, config_string):
        """
        Write bootloader configuration.
        in config_string are arguments for grubby divided by `;'
        """
        return self.gtkcall(*([GRUBBY_CMD] + ["--" + self.bootloader]  + config_string.split(";")))

    def set_bootloader(self):
        """ Choose which bootloader is on the system """
        bootloader = None
        for (name, (conf, offset, kpath)) in BOOTLOADERS.items():
            # I hope order doesn't matter
            if os.access(conf, os.W_OK):
                bootloader = name

        if bootloader is None:
            return ""

        return bootloader

    @slip.dbus.polkit.require_auth ("org.fedoraproject.systemconfig.kdump.handledumpservice")
    @dbus.service.method ("org.fedoraproject.systemconfig.kdump.mechanism",
                          in_signature='(ss)', out_signature='(iss)')
    def handledumpservice (self, (chkconfig_status, service_op)):
        """ Turn on/off kdump initscript. Start/stop kdump service """
        status = 0
        std = ""
        err = ""
        (status, std, err) = self.gtkcall("/sbin/chkconfig", "kdump",
                                          chkconfig_status)
        if status > 0:
            return (status, std, err)

        if service_op != "":
            (status, std, err) = self.gtkcall("/sbin/service", "kdump",
                                              service_op)
        if status > 0:
            return (status, std, err)

        if self.bootloader == 'yaboot':
            (status, std, err) = self.gtkcall('/sbin/ybin')
            if status > 0:
                return (status, std, err)

        return (status, std, err)

    @slip.dbus.polkit.require_auth ("org.fedoraproject.systemconfig.kdump.handledumpservice")
    @dbus.service.method ("org.fedoraproject.systemconfig.kdump.mechanism",
                          in_signature='', out_signature='(iss)')
    def getservicestatus (self):
        """ Get current status of the kdump service """
        return self.gtkcall("/sbin/service", "kdump", "status")

    def gtkcall (self, *args):
        """
        Call command args[0] with args arguments
        Return the tuple with (retcode, stdout, stderr)
        """
        the_call = subprocess.Popen(args, stdout = subprocess.PIPE,
                                    stderr = subprocess.PIPE)
        stdout, stderr = the_call.communicate()
        print "subprocess call:"
        print args 
        if stdout:
            print "-> stdout = " + stdout
        if stderr:
            print "-> stderr = " + stderr
        return (the_call.returncode, stdout or "", stderr or "")

if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    BUS = dbus.SystemBus ()

    NAME = dbus.service.BusName ("org.fedoraproject.systemconfig.kdump.mechanism", BUS)
    OBJECT = SystemConfigKdumpObject (BUS, '/org/fedoraproject/systemconfig/kdump/object')

    MAINLOOP = gobject.MainLoop ()
    slip.dbus.service.set_mainloop (MAINLOOP)
    MAINLOOP.run ()

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
# bootloader : possible conf locations
BOOTLOADERS = {
  "grub"   : ("/boot/grub/grub.conf", "/boot/efi/EFI/redhat/grub.conf"),
  "grub2"  : ("/boot/grub2/grub.cfg", "/boot/efi/EFI/redhat/grub.cfg",
              "/boot/efi/EFI/fedora/grub.cfg"),
  "yaboot" : ("/boot/etc/yaboot.conf",),
  "elilo"  : ("/boot/efi/EFI/redhat/elilo.conf",),
  "zipl"   : ("/etc/zipl.conf",)
}

AUTH         = "org.fedoraproject.systemconfig.kdump.auth"
NOAUTH         = "org.fedoraproject.systemconfig.kdump.noauth"
MECHANISM    = "org.fedoraproject.systemconfig.kdump.mechanism"
KDUMP_OBJECT = "/org/fedoraproject/systemconfig/kdump/object"

class SystemConfigKdumpObject(slip.dbus.service.Object):
    def __init__ (self, *p, **k):
        super (SystemConfigKdumpObject, self).__init__ (*p, **k)
        self.bootloader = self.set_bootloader()


    @slip.dbus.polkit.require_auth (NOAUTH)
    @dbus.service.method (MECHANISM,
                          in_signature = '', out_signature = '(siss)')
    def getdefaultkernel (self):
        """ Get default kernel name from grubby """
#        return self.gtkcall(GRUBBY_CMD, "--default-kernel")
        (cmd, retcode, std, err) = self.gtkcall(GRUBBY_CMD, "--default-kernel")
        if (std != ""):
            return (cmd, retcode, std, err)
        else:
            # default kernel is not set, we will use the first one
            # which is linux kernel entry
            name, value = "", ""
            (cmd, retcode, std, err) = self.gtkcall(GRUBBY_CMD, "--info", "ALL")
            for line in std.splitlines():
                try:
                    (name, value) = line.strip().split("=", 1)
                    if name == "kernel":
                        break
                except ValueError:
                    pass
            return (cmd, retcode, value, err)



    @slip.dbus.polkit.require_auth (NOAUTH)
    @dbus.service.method (MECHANISM,
                          in_signature = 's', out_signature = '(siss)')
    def getcmdline (self, kernel):
        """ Get command line arguments for kernel from grubby """
        (cmd, retcode, std, err) = self.gtkcall(GRUBBY_CMD, "--info", kernel)
        if retcode > 0:
            return (cmd, retcode, std, err)
        else:
            for line in std.splitlines():
                (name, value) = line.strip().split("=", 1)
                if name == "args":
                    return (cmd, retcode, value.strip('"'), err)

    @slip.dbus.polkit.require_auth (NOAUTH)
    @dbus.service.method (MECHANISM,
                          in_signature = 's', out_signature = '(siss)')
    def getxencmdline (self, kernel):
        """ Get command line arguments for xen kernel from grubby """
        (cmd, retcode, std, err) = self.gtkcall(GRUBBY_CMD, "--info", kernel)
        if retcode > 0:
            return (cmd, retcode, std, err)
        else:
            for line in std.splitlines:
                (name, value) = line.strip().split("=", 1)
                if name == "module":
                    return (cmd, retcode, value.strip('"'), err)

    @slip.dbus.polkit.require_auth (NOAUTH)
    @dbus.service.method (MECHANISM,
                          in_signature = '', out_signature = '(siss)')
    def getallkernels (self):
        """ Get all kernel names from grubby """
        return self.gtkcall(GRUBBY_CMD, "--info", "ALL")

    @slip.dbus.polkit.require_auth (AUTH)
    @dbus.service.method (MECHANISM,
                          in_signature = 's', out_signature = '(is)')
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

    @slip.dbus.polkit.require_auth (AUTH)
    @dbus.service.method (MECHANISM,
                          in_signature = 's', out_signature = '(siss)')
    def writebootconfig (self, config_string):
        """
        Write bootloader configuration.
        in config_string are arguments for grubby divided by `;'
        """
        return self.gtkcall(*([GRUBBY_CMD] + ["--" + self.bootloader] +
                            config_string.split(";")))

    def set_bootloader(self):
        """ Choose which bootloader is on the system """
        bootloader = ""
        for (name, conf_locations) in BOOTLOADERS.items():
            for conf in conf_locations:
                if os.access(conf, os.W_OK):
                    bootloader = name

        return bootloader

    @slip.dbus.polkit.require_auth (AUTH)
    @dbus.service.method (MECHANISM,
                          in_signature = '(ss)', out_signature = '(siss)')
    def handledumpservice (self, (chkconfig_status, service_op)):
        """ Turn on/off kdump initscript. Start/stop kdump service """
        status = 0
        std = ""
        err = ""
        (cmd, status, std, err) = self.gtkcall("/usr/bin/systemctl",
                                               chkconfig_status, "kdump")
        if status > 0:
            return (cmd, status, std, err)

        if service_op != "":
            (cmd, status, std, err) = self.gtkcall("/usr/bin/kdumpctl",
                                                   service_op)
        if status > 0:
            return (cmd, status, std, err)

        if self.bootloader == 'yaboot':
            (cmd, status, std, err) = self.gtkcall('/sbin/ybin')
            if status > 0:
                return (cmd, status, std, err)

        if self.bootloader == 'zipl':
            (cmd, status, std, err) = self.gtkcall('/sbin/zipl')
            if status > 0:
                return (cmd, status, std, err)
        return (cmd, status, std, err)

    @slip.dbus.polkit.require_auth (AUTH)
    @dbus.service.method (MECHANISM,
                          in_signature = '', out_signature = '(siss)')
    def getservicestatus (self):
        """ Get current status of the kdump service """
        return self.gtkcall("/usr/bin/kdumpctl", "status")

    def gtkcall (self, *args):
        """
        Call command args[0] with args arguments
        Return the tuple with (called command, retcode, stdout, stderr)
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
        return ("".join(str(a) + " " for a in args),
            the_call.returncode, stdout or "", stderr or "")

if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    BUS = dbus.SystemBus ()

    NAME = dbus.service.BusName (MECHANISM, BUS)
    OBJECT = SystemConfigKdumpObject (BUS, KDUMP_OBJECT)

    MAINLOOP = gobject.MainLoop ()
    slip.dbus.service.set_mainloop (MAINLOOP)
    MAINLOOP.run ()

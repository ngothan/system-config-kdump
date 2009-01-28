#!/usr/bin/python
# system-config-kdump.py - configures kexec/kdump
# Copyright (c) 2006 Red Hat, Inc.
# Authors: Dave Lehman <dlehman@redhat.com>
#          Jarod Wilson <jwilson@redhat.com>
#          Roman Rakus <rrakus@redhat.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import gtk
import gobject
import gtk.glade

import sys
import os
import stat

##
## dbus and polkit
##
import dbus

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

system_bus = dbus.SystemBus ()

from slip.dbus import polkit

##
## I18N
##
from rhpl.translate import _, N_
import rhpl.translate as translate
domain = "system-config-kdump"
translate.textdomain (domain)
gtk.glade.bindtextdomain(domain)

if os.access("system-config-kdump.glade", os.F_OK):
    xml = gtk.glade.XML ("./system-config-kdump.glade", domain=domain)
else:
    xml = gtk.glade.XML ("/usr/share/system-config-kdump/system-config-kdump.glade", domain=domain)

KDUMP_CONFIG_FILE = "/etc/kdump.conf"


TYPE_LOCAL = "file"
TYPE_NET = "net"
TYPE_NFS = "nfs"
TYPE_SSH = "ssh"
TYPE_RAW = "raw"
TYPE_DEFAULT = TYPE_LOCAL

NUM_FILTERS = 5

ACTION_REBOOT = "reboot"
ACTION_SHELL = "shell"
ACTION_HALT = "halt"
ACTION_DEFAULT = _("mount rootfs and run /sbin/init")

FSTAB_FILE = "/etc/fstab"
PROC_PARTITIONS = "/proc/partitions"

TAG_CURRENT = _("(current)")
TAG_DEFAULT = _("(default)")

# got from kernel/Documentation/devices.txt
SUPPORTED_MAJOR = [ '2', '3', '8', '9', '13', '14', '19', '21', '22', '28',
                    '31', '33', '34', '36', '40', '44', '45', '47', '48', '49',
                    '50', '51', '52', '53', '54', '55', '56', '57', '65', '66',
                    '67', '68', '69', '70', '71', '88', '89', '90', '91', '94',
                    '99', '128', '129', '130', '131', '132', '133', '134',
                    '135', '147', '180' ]

PATH_DEFAULT = "/var/crash"
CORE_COLLECTOR_DEFAULT = "makedumpfile -c"

defaultActions = [ACTION_DEFAULT, ACTION_REBOOT, ACTION_SHELL, ACTION_HALT]

supportedFilesystemTypes = ("ext2", "ext3")

unsupportedArches = ("ppc", "s390", "s390x", "i386", "i586")
kernelKdumpArches = ("ppc64")
debug = 0 
testing = 0

KDUMP_BLURB = _("Kdump is a new kernel crash dumping mechanism. In the event "
                "of a system crash, a core file can be captured using kdump, "
                "which runs in the context of a freshly booted kernel, making "
                "it far more reliable than methods capturing within the "
                "context of the crashed kernel. Being able to capture a core "
                "file can be invaluable in helping determine the root cause "
                "of a system crash. Note that kdump does require reserving a "
                "portion of system memory that will be unavailable for other "
                "uses.")

LOCATION_BLURB = _("Kdump will attempt to place the vmcore at the specified "
                   "location. In the event that it fails to place the vmcore "
                   "at location, the default action (specified below) will "
                   "be executed.")

"""
    TODO:
page 2 target setup
page 3 initrd selection
localizations
using rhpl
XEN support - need change in grubby
"""

class DBusProxy (object):
    def __init__ (self):
        self.bus = dbus.SystemBus ()
        self.dbus_object = self.bus.get_object ("org.fedoraproject.systemconfig.kdump.mechanism", "/org/fedoraproject/systemconfig/kdump/object")

# Get default kernel from grubby
    @polkit.enable_proxy
    def getdefaultkernel (self):
        return self.dbus_object.getdefaultkernel (dbus_interface = "org.fedoraproject.systemconfig.kdump.mechanism")

# Get command line arguments for specific kernel from grubby
    @polkit.enable_proxy
    def getcmdline (self, kernel):
        return self.dbus_object.getcmdline (kernel, dbus_interface = "org.fedoraproject.systemconfig.kdump.mechanism")

# Get command line argument for specific xen kernel from grubby
    @polkit.enable_proxy
    def getxencmdline (self, kernel):
        return self.dbus_object.getxencmdline (kernel, dbus_interface = "org.fedoraproject.systemconfig.kdump.mechanism")

# Get all kernel names from grubby
    @polkit.enable_proxy
    def getallkernels (self):
        return self.dbus_object.getallkernels (dbus_interface = "org.fedoraproject.systemconfig.kdump.mechanism")

# Write kdump configuration data to /etc/kdump.conf
    @polkit.enable_proxy
    def writedumpconfig (self, configString):
        return self.dbus_object.writedumpconfig (configString, dbus_interface = "org.fedoraproject.systemconfig.kdump.mechanism")

# Write bootloader configuration
    @polkit.enable_proxy
    def writebootconfig (self, configString):
        return self.dbus_object.writebootconfig (configString, dbus_interface = "org.fedoraproject.systemconfig.kdump.mechanism")


class mainWindow:
    def __init__(self):
        self.dbusObject = DBusProxy()
        nameTag = _("Kernel Dump Configuration")
        commentTag = _("Configure kdump/kexec")

        self.xml = xml
        self.targetType = TYPE_DEFAULT
        self.serverName = ""
        self.userName = ""

        #                  fsType, partition
        self.partitions = [(None, "file:///")]
        self.rawDevices = []

        self.arch = None

        self._quiet = False # if set, don't pop up any message boxes or dialogs
    
        self.kdumpConfigComments = []
        self.miscConfig = []

        self.filters = [False for x in range(NUM_FILTERS)]
        self.filterCheckbutton = [gtk.CheckButton for x in range(NUM_FILTERS)]

        self.defaultAction = ACTION_DEFAULT
        self.path = PATH_DEFAULT
        self.coreCollector = CORE_COLLECTOR_DEFAULT

        self.kdumpEnabled = False
        self.totalMem = 0
        self.kdumpMem = 0
        self.usableMem = 0
        self.origCrashKernel = ""
        self.kernelPrefix = "/"

        self.defaultKernel = self.defaultKernelName()[:-1]
        self.runningKernel = os.popen("/bin/uname -r").read().strip()
        self.selectedKernel = self.defaultKernel

        self.bootloader = None
        self.arch = os.popen("/bin/uname -m").read().strip()

    def setupScreen(self):
        # load widgets from glade file
        self.toplevel = self.xml.get_widget("mainWindow")

        self.kdumpNotebook = self.xml.get_widget("kdumpNotebook");

        self.okButton = self.xml.get_widget("okButton")
        self.cancelButton = self.xml.get_widget("cancelButton")


        self.kdumpEnableCheckButton = self.xml.get_widget("kdumpEnableCheckButton")

        # page 0
        self.memoryTable            = self.xml.get_widget("memoryTable")
        self.totalMemLabel          = self.xml.get_widget("totalMem")
	self.kdumpMemCurrentLabel   = self.xml.get_widget("kdumpMemCurrent")
        self.kdumpMemSpinButton     = self.xml.get_widget("kdumpMemSpinButton")
        self.usableMemLabel         = self.xml.get_widget("usableMem")

        # page 1
        self.localfsRadiobutton      = self.xml.get_widget("localfsRadiobutton")
        self.partitionCombobox       = self.xml.get_widget("partitionCombobox")
        self.locationEntry           = self.xml.get_widget("locationEntry")
        self.localFilechooserbutton  = self.xml.get_widget("localFilechooserbutton")
        self.rawDeviceRadiobutton    = self.xml.get_widget("rawDeviceRadiobutton")
        self.deviceCombobox          = self.xml.get_widget("deviceCombobox")
        self.networkRadiobutton      = self.xml.get_widget("networkRadiobutton")
        self.networkTypeVbox         = self.xml.get_widget("networkTypeVbox")
        self.nfsRadiobutton          = self.xml.get_widget("nfsRadiobutton")
        self.sshRadiobutton          = self.xml.get_widget("sshRadiobutton")
        self.networkConfigTable      = self.xml.get_widget("networkConfigTable")
        self.usernameEntry           = self.xml.get_widget("usernameEntry")
        self.pathEntry               = self.xml.get_widget("pathEntry")
        self.servernameEntry         = self.xml.get_widget("servernameEntry")

        # page 2
        for x in range(NUM_FILTERS):
            self.filterCheckbutton[x]      = self.xml.get_widget("filterCheckbutton%d" % x)
        self.filterLevelLabel              = self.xml.get_widget("filterLevelLabel")
        self.elfFileFormatRadioButton      = self.xml.get_widget("elfFileFormatRadioButton")
        self.diskdupmFileFormatRadioButton = self.xml.get_widget("diskdumpFileFormatRadioButton")


        # page 3
        self.defaultInitrdRadiobutton = self.xml.get_widget("defaultInitrdRadiobutton")
        self.customInitrdRadiobutton  = self.xml.get_widget("customInitrdRadiobutton")
        self.initrdFilechooserbutton  = self.xml.get_widget("initrdFilechooserbutton")
        self.defaultKernelRadiobutton = self.xml.get_widget("defaultKernelRadiobutton")
        self.customKernelRadiobutton  = self.xml.get_widget("customKernelRadiobutton")
        self.customKernelCombobox     = self.xml.get_widget("customKernelCombobox")
        self.originalCommandLineEntry = self.xml.get_widget("originalCommandLineEntry")
        self.commandLineEntry         = self.xml.get_widget("commandLineEntry")
        self.clearCmdlineButton       = self.xml.get_widget("clearCmdlineButton")
        self.defaultActionCombo       = self.xml.get_widget("defaultActionCombo")
        self.coreCollectorEntry       = self.xml.get_widget("coreCollectorEntry")


        # widgets setup and signals connect
        self.okButton.connect("clicked", self.okClicked)
        self.cancelButton.connect("clicked", self.cancelClicked)
        self.toplevel.connect("destroy", self.destroy)
        self.kdumpEnableCheckButton.connect("toggled", self.kdumpEnableToggled)

        # page 0
        self.kdumpMemSpinButton.connect("value_changed", self.updateUsableMem)

        # page 1
        self.localfsRadiobutton.connect("toggled", self.targetTypeChanged)
        self.rawDeviceRadiobutton.connect("toggled", self.targetTypeChanged)
        self.networkRadiobutton.connect("toggled", self.targetTypeChanged)
        self.nfsRadiobutton.connect("toggled", self.nfsChanged)
        self.setupPartitions(self.partitionCombobox)
        self.setupRawDevices(self.deviceCombobox)
        self.locationEntry.connect("focus-out-event", self.locationChanged)
        self.localFilechooserbutton.connect("selection-changed", self.locationChanged)
        self.pathEntry.connect("focus-out-event", self.pathChanged)
        self.servernameEntry.connect("focus-out-event", self.servernameChanged)
        self.usernameEntry.connect("focus-out-event", self.usernameChanged)

        # page 2
        for x in range(NUM_FILTERS):
            self.filterCheckbutton[x].connect("toggled", self.filterChanged)

        # page 3
        self.customInitrdRadiobutton.connect("toggled", self.customInitrdChanged)
        self.customKernelRadiobutton.connect("toggled", self.customKernelChanged)
        self.initrdFilechooserbutton.set_current_folder("/boot")
        line = self.getCmdLine(self.defaultKernel)
        self.originalCommandLineEntry.set_text(line)
        self.commandLineEntry.set_text(line)
        self.setupCustomKernelCombobox(self.customKernelCombobox)
        self.customKernelCombobox.connect("changed", self.updateCmdLine)
        self.commandLineEntry.connect("focus-out-event", self.cmdlineChanged)
        self.clearCmdlineButton.connect("clicked", self.resetCmdline)
        self.coreCollectorEntry.connect("focus-out-event", self.collectorEntryChanged)
        self.defaultActionCombo.connect("changed", self.setDefaultAction)

        self.tooltips = gtk.Tooltips()
        self.tooltips.set_tip(self.kdumpEnableCheckButton, _(KDUMP_BLURB))


        # check architecture
        if self.arch in unsupportedArches:
            self.showErrorMessage(_("Sorry, this architecture does not "
                                    "currently support kdump"))
            sys.exit(1)

        # get total memory of system
        memInfo = open("/proc/meminfo").readlines()
        totalMem = None
        for line in memInfo:
            if line.startswith("MemTotal:"):
                totalMem = int(line.split()[1]) / 1024

        if not totalMem:
            self.showErrorMessage(_("Failed to detect total system memory"))
            sys.exit(1)


        # Check for a xen kernel, we do things a bit different w/xen
        self.xenKernel = False
        if os.access("/proc/xen", os.R_OK):
            self.xenKernel = True

        if self.xenKernel and self.arch == 'ia64':
            self.showErrorMessage(_("Sorry, ia64 xen kernels do not support kdump "
                                    "at this time."))
            sys.exit(1)

        # Check to see if kdump memory is already reserved
        # Read from /proc/iomem so we're portable across xen and non-xen
        kdumpMem = 0
	kdumpMemGrubby = 0
        kdumpOffset = 0
	kdumpOffsetGrubby = 0
        # PowerPC64 doesn't list crashkernel reservation in /proc/iomem
        if self.arch != 'ppc64':
            ioMem = open("/proc/iomem").readlines()
            for line in ioMem:
                if line.find("Crash kernel") != -1:
                    hexCKstart = line.strip().split("-")[0]
                    hexCKend = line.strip().split("-")[1].split(":")[0].strip()
                    kdumpOffset = self.hex2mb(hexCKstart)
                    kdumpMem = self.hex2mb(hexCKend) - kdumpOffset
                    break
        else:
            cmdLine = open("/proc/cmdline").read()
            if cmdLine.find("crashkernel=") > -1:
                crashString = filter(lambda t: t.startswith("crashkernel="), 
                                     cmdLine.split())[0].split("=")[1]
                tokens = crashString.split("@")
                kdumpMem = int(tokens[0][:-1])
                if len(tokens) == 2:
                    kdumpOffset = int(tokens[1][:-1])

        # i686 xen requires kernel-PAE for kdump if any memory
        # is mapped above 4GB
        self.xenKdumpKernel = "kernel"
        if self.arch == "i686" and self.xenKernel:
            for line in ioMem:
                if line.find("System RAM") != -1:
                    rangeEnd = line.strip().split("-")[1].split(":")[0].strip()
                    if rangeEnd >= 0x100000000L:
                        self.xenKdumpKernel = "kernel-PAE"
                        break

	# read current kdump settings from grubby
	if debug:
            print "grubby --default-kernel: " + self.defaultKernel
        line = self.getCmdLine(self.defaultKernel)
        if line.find("crashkernel") != -1:
            crashString = filter(lambda t: t.startswith("crashkernel="),
                                          line.split())[0].split("=")[1]
            tokens = crashString.split("@")
            kdumpMemGrubby = int(tokens[0][:-1])
            if len(tokens) == 2:
                kdumpOffsetGrubby = int(tokens[2][:-1])
            if debug:
                print "grubby --info: crashkernel=%iM@%iM" \
                       % (kdumpMemGrubby, kdumpOffsetGrubby)

        # Defaults
        lowerBound = 128
        minUsable = 512
        step = 64


        if self.arch == 'ia64':
            # ia64 needs at least 256M, page-aligned
            lowerBound = 256
            step = 256
        elif self.arch == 'ppc64':
            lowerBound = 256
            minUsable = 2048



        # Fix up memory calculations, if need be
	if kdumpMemGrubby != 0:
            self.kdumpEnableCheckButton.set_active(True)
            self.kdumpEnableCheckButton.toggled()
            totalMem += kdumpMem
            if kdumpOffset == 0:
                self.origCrashKernel = "%dM" % kdumpMem
            else:
                self.origCrashKernel = "%dM@%dM" % (kdumpMem, kdumpOffset)
        else:
	    kdumpMemGrubby = lowerBound
            self.kdumpEnableCheckButton.set_active(False)
            self.kdumpEnableCheckButton.toggled()

        self.totalMemLabel.set_text("%s (MB)" % (totalMem,))

        # Do some sanity-checking and try to present only sane options.
        #
        upperBound = (totalMem - minUsable) - (totalMem % step) 

        if upperBound < lowerBound:
            self.showErrorMessage(_("This system does not have enough "
                                    "memory for kdump to be viable"))
            sys.exit(1)

        # Set spinner to lowerBound unless already set on kernel command line
        if kdumpMem != 0:
            # round it down to a multiple of %step
            kdumpMem = kdumpMem - (kdumpMem % step)
            self.kdumpMem = kdumpMem

        self.totalMem = totalMem
        self.usableMem = self.totalMem - self.kdumpMem

	self.kdumpMemCurrentLabel.set_text("%s (MB)" % (kdumpMem))

        kdumpMemAdj = gtk.Adjustment(kdumpMem, lowerBound, upperBound, step, step, 64)
        self.kdumpMemSpinButton.set_adjustment(kdumpMemAdj)
        self.kdumpMemSpinButton.set_update_policy(gtk.UPDATE_IF_VALID)
        self.kdumpMemSpinButton.set_numeric(True)
        self.kdumpMemSpinButton.set_value(kdumpMemGrubby)
        self.updateUsableMem(self.kdumpMemSpinButton)

        self.usableMemLabel.set_text("%s (MB)" % (self.usableMem,))

        if debug:
            print "totalMem = %dM\nkdumpMem = %dM\nkdumpMemGrubby = %dM\nusableMem = %dM" % (totalMem, kdumpMem, kdumpMemGrubby, self.usableMem)

        for action in defaultActions:
            self.defaultActionCombo.append_text(action)
        self.defaultActionCombo.set_active(0)
        self.setDefaultAction()

        self.setLocation(TYPE_DEFAULT, PATH_DEFAULT)
        self.setPath(PATH_DEFAULT)
        self.setCoreCollector(CORE_COLLECTOR_DEFAULT)
        self.loadDumpConfig()

    def run(self):
        self.toplevel.show_all()
        gtk.main()

    def destroy(self, *args):
        gtk.main_quit()

    def okClicked(self, *args):
        if self.targetType not in (TYPE_RAW, TYPE_LOCAL) and not self.path:
            rc = self.yesNoDialog(_("Path cannot be empty for '%s' locations. "
                                    "Reset path to default ('%s')?.")
                                    % (self.targetType, PATH_DEFAULT))
            if rc == True:
                self.setPath(PATH_DEFAULT)
            else:
                return

        if (self.targetType == TYPE_RAW) and\
           (self.deviceCombobox.get_active() < 0):
            self.showErrorMessage(_("You must select one of the raw devices"))
            return

        if (self.targetType == TYPE_LOCAL) and\
           (self.partitionCombobox.get_active() < 0):
            self.showErrorMessage(_("You must select one of the partitions"))
            return



        kernelKdumpNote = ""
        if self.arch in kernelKdumpArches:
            kernelKdumpNote = _("\n\nNote that the %s architecture does not "
                                "feature a relocatable kernel at this time, "
                                "and thus requires a separate kernel-kdump "
                                "package to be installed for kdump to "
                                "function. This can be installed via 'yum "
                                "install kernel-kdump' at your convenience."
                                "\n\n") % self.arch

        if self.xenKernel and self.kdumpEnabled:
            self.showMessage(_("WARNING: xen kdump support requires a "
                               "non-xen %s RPM to perform actual crash "
                               "dump capture. Please be sure you have "
                               "the non-xen %s RPM of the same version "
                               "as your xen kernel installed.") %
                               (self.xenKdumpKernel, self.xenKdumpKernel))

        try:
            origKdumpMem = int(self.origCrashKernel.split("@")[0][:-1])
        except ValueError:
            origKdumpMem = 0

        if self.kdumpEnabled and self.kdumpMem != origKdumpMem:
            self.showMessage(_("Changing Kdump settings requires rebooting "
                               "the system to reallocate memory accordingly. "
                               "%sYou will have to reboot the system for the "
                               "new settings to take effect.")
                               % kernelKdumpNote)

        if not testing:
            if debug:
                print "writing kdump config"

            if not self.writeDumpConfig():
                return

            if debug:
                print "writing bootloader config"

            if not self.writeBootloaderConfig():
                return
        else:
            print "would have called writeDumpConfig"
            print "would have called writeBootloaderConfig"

        self.destroy()

    def cancelClicked(self, *args):
        self.destroy()


    def setLocation(self, locationType, path):
        if debug:
            print "setLocation " + locationType  + " " + path

        # SSH or NFS
        if locationType == TYPE_NET:
            self.networkRadiobutton.set_active(True)
            if path.find("@") != -1:
                # SSH
                self.sshRadiobutton.set_active(True)
                (self.userName, self.serverName) = path.split("@")
                self.servernameEntry.set_text(self.serverName)
                self.usernameEntry.set_text(self.userName)
            else:
                # NFS
                self.nfsRadiobutton.set_active(True)
                self.serverName = path
                self.servernameEntry.set_text(path)
            self.nfsRadiobutton.toggled()

        # RAW
        elif locationType == TYPE_RAW:
            if self.setActiveRawDevice(path):
                self.rawDeviceRadiobutton.set_active(True)

        elif locationType == TYPE_LOCAL:
            self.setPath(path)

        # One of supported partition type
        else:
            self.setActivePartition(locationType, path)
        self.localfsRadiobutton.toggled()

    def loadDumpConfig(self):
        try:
            lines = open(KDUMP_CONFIG_FILE).readlines()
        except IOError:
            return

        #self.quiet(True)  # suppress error popups temporarily

        for line in [l.strip() for l in lines]:
            if not line:
                continue

            i = line.find("#")
            if i != -1:
                origLine = line
                line = line[:i].strip()
                if not line:
                    # save comment lines to put in the updated config
                    self.kdumpConfigComments.append(origLine)
                    continue

            try:
                type, location = line.split(' ', 1)
            except ValueError:
                print >> sys.stderr, "Failed to parse line; chucking it..."
                print >> sys.stderr, "  \'%s\'" % (line,)
                continue

            # XXX is case going to be an issue?
            if type == "default":
                self.setDefaultAction(location)
            elif type == "ifc":
                continue
            elif type == "path":
                self.setPath(location)
            elif type == "core_collector":
                self.setCoreCollector(location)
            elif type in (TYPE_RAW, TYPE_NET) or type in supportedFilesystemTypes:
                self.setLocation(type, location)
            else:
                self.miscConfig.append(" ".join((type, location)))

    def writeDumpConfig(self):
        if testing or not self.kdumpEnabled:
            return 1

        # start point
        configString = ""

        # comment lines
        configString += "".join(self.kdumpConfigComments) + "\n"

        # misc. config
        for line in self.miscConfig:
            configString += "%s\n" % line

        # target type
        #   rawdevice
        if self.targetType == TYPE_RAW:
            configString += "raw %s\n" % self.rawDevices[self.deviceCombobox.get_active()]

        #   nfs
        elif self.targetType == TYPE_NFS:
            configString += "net %s\n" % self.serverName
            configString += "path %s\n" % self.pathEntry.get_text()

        #   scp
        elif self.targetType == TYPE_SSH:
            configString += "net %s@%s\n" % (self.userName ,self.serverName)
            configString += "path %s\n" % self.pathEntry.get_text()

        #   local
        elif self.targetType == TYPE_LOCAL:
            (fsType, partition) = self.partitions[self.partitionCombobox.get_active()]
            if fsType and partition:
                configString += "%s %s\n" % (fsType, partition)

        # path
        configString += "path %s\n" % self.path

        # core collector
        configString += "core_collector %s\n" % self.coreCollector

        # default
        if self.defaultAction is not ACTION_DEFAULT:
            configString += "default %s\n" % self.defaultAction

        written = self.dbusObject.writedumpconfig(configString)

        if debug:
            print "written kdump config:"
            print written
        if (configString != written):
            self.showErrorMessage(_("Error writing kdump configuration: %s" % written))
            return 0
        return 1

    def writeBootloaderConfig(self):
        if testing:
            return

        configString = ""
        if debug: print "Write bootloader conf:"
        
        # kernel name to change
        configString += " --update-kernel=" + self.selectedKernel
        if debug: print "  Updating kernel '%s'" % (self.selectedKernel)

        # arguments
        if self.kdumpEnabled:
        # at first remove original kernel cmd line
            configString += " --remove-args=\"" + self.originalCommandLineEntry.get_text() + "\""
            if debug:
                print "  Removing original args '%s'" % (self.originalCommandLineEntry.get_text())

            check = self.dbusObject.writebootconfig(configString)
            if debug:
                print "  check: " + check

        # and now set new kernel cmd line
            configString = " --update-kernel=" + self.selectedKernel
            if debug:
                print "  Updating kernel '%s'" % (self.selectedKernel)

            configString += " --args=\"" + self.commandLineEntry.get_text() + "\""
            if debug:
                print "  Setting args to '%s'" % (self.commandLineEntry.get_text())

            check = self.dbusObject.writebootconfig(configString)
            if debug:
                print "  check: " + check

        else:
        # kdump is desabled, so only remove crashkernel
            configString += " --remove-args=\"crashkernel=%s\"" % (self.origCrashKernel)
            if debug:
                print "  Removing crashkernel=%s" % (self.origCrashKernel)

            check = self.dbusObject.writebootconfig(configString)
            if debug:
                print "  check: " + check

        return 1

    def updateUsableMem(self, *args):
        self.kdumpMem = int(args[0].get_value())
        self.usableMem = self.totalMem - self.kdumpMem
        self.usableMemLabel.set_text("%s (MB)" % (self.usableMem,))
        if debug:
            print "setting usableMem to", self.usableMem
        self.setCrashkernel(self.commandLineEntry, self.kdumpMem)

    def setDefaultAction(self, *args):
        if args and args[0] in defaultActions:
            self.defaultAction = args[0]
            self.defaultActionCombo.set_active(defaultActions.index(args[0]))
        else:
            idx = self.defaultActionCombo.get_active()
            self.defaultAction = defaultActions[idx]

        if debug:
            print "setting defaultAction to", self.defaultAction

        return True

    # convert hex memory values into MB of RAM so we can
    # read /proc/iomem and show something a human understands
    def hex2mb(self, hex):
        divisor = 1048575
        mb = int(hex,16) / divisor
        return mb

    def setPath(self, path):
        if debug:
            print "setting path to '%s'" % path
        self.path = path

        if (self.pathEntry.get_text() != path):
            self.pathEntry.set_text(path)

        if (self.locationEntry.get_text() != path):
            self.locationEntry.set_text(path)

        if (self.localFilechooserbutton.get_filename() != path):
            self.localFilechooserbutton.set_current_folder(path)
        return True

    def setCoreCollector(self, collector):
        if collector and not collector.startswith("makedumpfile"):
            self.showErrorMessage(_("Core collector must begin with "
                                    "'makedumpfile'"))
            return False

        if debug:
            print "setting core_collector to '%s'" % collector
        self.coreCollector = collector
        if self.coreCollectorEntry.get_text() != collector:
            self.coreCollectorEntry.set_text(collector)
            self.collectorEntryChanged(self.coreCollectorEntry)
        return True

    def kdumpEnableToggled(self, *args):
        self.kdumpEnabled = self.kdumpEnableCheckButton.get_active()
        if debug:
            print "setting kdumpEnabled to", self.kdumpEnabled

        self.memoryTable.set_sensitive(self.kdumpEnabled)
        self.kdumpNotebook.set_sensitive(self.kdumpEnabled)
        if self.kdumpEnabled:
            self.updateUsableMem(self.kdumpMemSpinButton)

    def quiet(self, flag=None):
        if flag in (True, False):
            self._quiet = flag

        return self._quiet

    def showErrorMessage(self, text):
        if self.quiet():
            print >> sys.stderr, text
            return

        dlg = gtk.MessageDialog(None, 0, gtk.MESSAGE_ERROR, 
                                gtk.BUTTONS_OK, text)
        dlg.set_position(gtk.WIN_POS_CENTER)
        dlg.set_modal(True)
        dlg.run()
        dlg.destroy()
        return False

    def showMessage(self, text, type=None):
        if self.quiet():
            print >> sys.stderr, text
            return

        if type is None:
            type = gtk.MESSAGE_INFO

        dlg = gtk.MessageDialog(None, 0, type, gtk.BUTTONS_OK, text)
        dlg.set_position(gtk.WIN_POS_CENTER)
        dlg.set_modal(True)
        dlg.run()
        dlg.destroy()
           
    def yesNoDialog(self, text):
        if self.quiet():
            print >> sys.stderr, text, "(assuming yes)"
            return True

        dlg = gtk.MessageDialog(None, 0, gtk.MESSAGE_QUESTION, 
                                gtk.BUTTONS_YES_NO, text)
        dlg.set_position(gtk.WIN_POS_CENTER)
        dlg.set_modal(True)
        ret = dlg.run()
        dlg.destroy()
        if ret == gtk.RESPONSE_YES:
            rc = True
        else:
            rc = False

        return rc

    def targetTypeChanged(self, *args):
        local = self.localfsRadiobutton.get_active()
        raw = self.rawDeviceRadiobutton.get_active()
        net = self.networkRadiobutton.get_active()

        self.locationEntry.set_sensitive(local)
        self.localFilechooserbutton.set_sensitive(local)
        self.partitionCombobox.set_sensitive(local)

        self.deviceCombobox.set_sensitive(raw)

        self.networkTypeVbox.set_sensitive(net)
        self.networkConfigTable.set_sensitive(net)
        
        if (local):
            self.targetType = TYPE_LOCAL
        elif (raw):
            self.targetType = TYPE_RAW

    def nfsChanged(self, nfsRadioButton, *args):
        if (nfsRadioButton.get_active()):
            self.usernameEntry.set_sensitive(False)
            self.targetType = TYPE_NFS
        else:
            self.usernameEntry.set_sensitive(True)
            self.targetType = TYPE_SSH
            

    def customKernelChanged(self, button, *args):
        self.customKernelCombobox.set_sensitive(self.customKernelRadiobutton.get_active())
        if not button.get_active():
            self.selectedKernel = self.defaultKernel
            line = self.getCmdLine(self.selectedKernel)
            self.originalCommandLineEntry.set_text(line)
            self.commandLineEntry.set_text(line)
        else:
            self.updateCmdLine(self.customKernelCombobox)
        self.updateUsableMem(self.kdumpMemSpinButton)

    def customInitrdChanged(self, *args):
        self.initrdFilechooserbutton.set_sensitive(self.customInitrdRadiobutton.get_active())

    # fill partition combo box with available partitions
    # partitions and their types are read from fstab
    def setupPartitions(self, combobox):
        try:
            lines = open(FSTAB_FILE).readlines()
            for line in lines:
                for fstype in supportedFilesystemTypes:
                    if line.find(fstype) != -1:
                        self.partitions.append((fstype, line.split(" ")[0]))
                        if debug:
                            print "found partition in fstab: ", self.partitions[len(self.partitions) -1 ] 
        except IOError:
            pass
        for (fsType, partition) in self.partitions:
            combobox.append_text("%s (%s)" % (partition, fsType))
        combobox.set_active(0)
        return

    # fill raw devices combo box with all partitions listed in /proc/partitions
    # uses only valid major numbers
    def setupRawDevices(self, combobox):
        try:
            lines = open(PROC_PARTITIONS).readlines()
            for line in lines:
                major = line.strip().split(" ")[0]
                if major in SUPPORTED_MAJOR:
                    dev = "/dev/%s" % line.strip().rsplit(" ",1)[1]
                    self.rawDevices.append(dev)
                    if debug:
                        print "added '%s' to raw devices" % dev
        except IOError:
            pass
        for dev in self.rawDevices:
            combobox.append_text(dev)
        combobox.set_active(0)
        return

    def locationChanged(self, widget, *args):
        if widget == self.locationEntry:
            self.setPath(widget.get_text())
        else:
            self.setPath(widget.get_filename())

    def getCmdLine(self, kernel):
       if (kernel.find("/boot/xen.")) is not -1:
           cmdline = self.dbusObject.getxencmdline(kernel)
       else:
           cmdline = self.dbusObject.getcmdline(kernel)
       self.origCrashKernel = self.getCrashkernel(cmdline)
       return cmdline
       

    def defaultKernelName(self):
        defKern = self.dbusObject.getdefaultkernel()
        self.kernelPrefix = defKern.rsplit("/",1)[0]
        if debug:
            print "Default kernel = " + defKern
            print "Kernel prefix = " + self.kernelPrefix
	return defKern

    def setupCustomKernelCombobox(self, combobox):
        lines = self.dbusObject.getallkernels().split("\n")
        for line in lines[:-1]:
            (name, value) = line.strip().split("=",1)
            if name == "kernel":
                text = value.strip('"')
                if self.defaultKernel.find(text) is not -1:
                    text = text + " " + TAG_DEFAULT
                if text.find(self.runningKernel) is not -1:
                    text = text + " " + TAG_CURRENT
                combobox.append_text(self.kernelPrefix + text)
                if debug:
                   print "Appended kernel:\"" + self.kernelPrefix + text+"\""
        combobox.set_active(0)
        return

    def updateCmdLine(self, combobox, *args):
        self.selectedKernel = combobox.get_active_text()
        self.selectedKernel = self.selectedKernel.rsplit(TAG_CURRENT,1)[0] # there can be current or default
        self.selectedKernel = self.selectedKernel.rsplit(TAG_DEFAULT,1)[0] # or default tag
        line = self.getCmdLine(self.selectedKernel)
        self.originalCommandLineEntry.set_text(line)
        self.commandLineEntry.set_text(line)
        self.updateUsableMem(self.kdumpMemSpinButton)

    def getCrashkernel(self, text):
        index = text.find("crashkernel=")
        if index != -1:
            return text[index:].split(" ")[0].split("=")[1]
        return ""

    def setCrashkernel(self, gtkEntry, size):
        oldValue = self.getCrashkernel(gtkEntry.get_text())
        oldText = gtkEntry.get_text()
        if oldValue == "":
            gtkEntry.set_text(oldText + " crashkernel=%dM" % size)
        else:
            gtkEntry.set_text(oldText.replace(oldValue,"%dM" % size))

    def cmdlineChanged(self, gtkEntry, *args):
        value = self.getCrashkernel(gtkEntry.get_text())[:-1]
        if value == "":
            self.kdumpEnableCheckButton.set_active(False)
            self.kdumpEnableCheckButton.toggled()
        else:
            self.kdumpMemSpinButton.set_value(float(value))
            self.updateUsableMem(self.kdumpMemSpinButton)
        if debug:
            print "Updated cmdline. Crashkernel set to " + value

    def resetCmdline(self, *args):
        self.commandLineEntry.set_text(self.originalCommandLineEntry.get_text())
        self.cmdlineChanged(self.commandLineEntry)

    def setActiveRawDevice(self, deviceName):
        if self.rawDevices.count(deviceName) > 0:
            self.deviceCombobox.set_active(self.rawDevices.index(deviceName))
            return True
        else:
            self.showErrorMessage(_("Raw device %s wasn't found on this machine" % deviceName))
            self.deviceCombobox.set_active(-1)
            return False

    def setActivePartition(self, partType, partName):
        if self.partitions.count((partType, partName)) > 0:
            self.partitionCombobox.set_active(self.partitions.index((partType, partName)))
            return True
        else:
            self.showErrorMessage(_("Local file system partition with name %s and type %s wasn't found" % (partName, partType)))
            self.partitionCombobox.set_active(-1)
            return False

    def collectorEntryChanged(self, entry, *args):
        if not self.setCoreCollector(entry.get_text()):
            entry.set_text(self.coreCollector)

        # filter level set?
        idx = self.coreCollector.find("-d")
        if idx != -1:
            try:
                level = int(self.coreCollector[idx:].split(" ")[1])
            except ValueError:
                level = 0
            self.filterChanged(level)
	else:
		self.filterChanged(0)
        return False

    def setCollectorFilter(self, level):
        idx = self.coreCollector.find("-d")
        if idx != -1:
            value = self.coreCollector[idx:].split(" ")[1]
            self.setCoreCollector(self.coreCollector.replace(\
                            "-d %s" % value, "-d %d" % level))
        else:
            self.setCoreCollector(self.coreCollector + " -d %d" % level)

    def pathChanged(self, entry, *args):
        self.path = entry.get_text()
        return False

    def usernameChanged(self, entry, *args):
        self.userName = entry.get_text()
        return False

    def servernameChanged(self, entry, *args):
        self.serverName = entry.get_text()
        return False

    def setFilterCheckbuttons(self, level):
        for index in range(NUM_FILTERS-1, -1, -1):
            if level >= (2**index):
                level -= (2**index)
                self.filters[index] = True
                self.filterCheckbutton[index].set_active(True)
            else:
                self.filters[index] = False
                self.filterCheckbutton[index].set_active(False)
        self.filterCheckbutton[0].toggled()
        return

    def filterChanged(self, *args):
        level = 0
        if args[0] in self.filterCheckbutton:
            for x in range(NUM_FILTERS):
                self.filters[x] = self.filterCheckbutton[x].get_active()
                level += self.filters[x] * (2**x)
            self.setCollectorFilter(level)
            self.filterLevelLabel.set_text("%d" % level)
        else:
            level = args[0]
            self.setFilterCheckbuttons(level)


if __name__ == "__main__":
    import getopt

    opt, arg = getopt.getopt(sys.argv[1:], 'dth', ['debug', 'test', 'testing', 'help'])
    for (opt, val) in opt:
        if opt in ("-d", "--debug"):
            print "*** Debug messages enabled. ***"
            debug = 1
        elif opt in ("-t", "--test", "--testing"):
            print "*** Testing only. No configurations will be modified. ***"
            testing = 1
        elif opt in ("-h", "--help"):
            print >> sys.stderr, "Usage: system-config-kdump.py [--test] [--debug]"

    win = mainWindow()
    win.setupScreen()
    win.run()

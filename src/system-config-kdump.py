# system-config-kdump.py - configures kexec/kdump
# Copyright (c) 2006 Red Hat, Inc.
# Authors: Dave Lehman <dlehman@redhat.com>
#          Jarod Wilson <jwilson@redhat.com>
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

#             bootloader : (config file, kdump offset, kernel path)
bootloaders = { "grub"   : ("/boot/grub/grub.conf", 16, "/boot"),
                "yaboot" : ("/boot/etc/yaboot.conf", 32, "/boot"),
                "elilo"  : ("/boot/efi/EFI/redhat/elilo.conf", 256, "/boot/efi/EFI/redhat") }

TYPE_LOCAL = "file"
TYPE_NET = "net"
TYPE_NFS = "nfs"
TYPE_SSH = "ssh"
TYPE_RAW = "raw"
TYPE_DEFAULT = TYPE_LOCAL

ACTION_REBOOT = "reboot"
ACTION_SHELL = "shell"
ACTION_DEFAULT = _("mount rootfs and run /sbin/init")

PATH_DEFAULT = "/var/crash"
CORE_COLLECTOR_DEFAULT = "makedumpfile -c"

locationTypes = [TYPE_LOCAL, TYPE_NFS, TYPE_SSH, TYPE_RAW]
netLocationTypes = (TYPE_NFS, TYPE_SSH)
defaultActions = [ACTION_REBOOT, ACTION_SHELL, ACTION_DEFAULT]

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

"""
class mainWindow:
    def __init__(self):
        nameTag = _("Kernel Dump Configuration")
        commentTag = _("Configure kdump/kexec")

        self.xml = xml
        self.location = (TYPE_DEFAULT, PATH_DEFAULT)

        self.arch = None

        self._quiet = False # if set, don't pop up any message boxes or dialogs
    
        self.kdumpConfigComments = []

        self.defaultAction = ACTION_DEFAULT
        self.path = PATH_DEFAULT
        self.coreCollector = CORE_COLLECTOR_DEFAULT

        self.kdumpEnabled = False
        self.totalMem = 0
        self.kdumpMem = 0
        self.usableMem = 0
        self.origCrashKernel = ""

        self.bootloader = None

    def setupScreen(self):
        self.toplevel = self.xml.get_widget("mainWindow")
        self.toplevel.set_position(gtk.WIN_POS_CENTER)

        self.memoryTable = self.xml.get_widget("memoryTable")
        self.kdumpEnableCheckButton = self.xml.get_widget("kdumpEnableCheckButton")
        self.totalMemLabel = self.xml.get_widget("totalMem")
        self.kdumpMemSpinButton = self.xml.get_widget("kdumpMemSpinButton")
        self.usableMemLabel = self.xml.get_widget("usableMem")

        self.tooltips = gtk.Tooltips()
        self.tooltips.set_tip(self.kdumpEnableCheckButton, _(KDUMP_BLURB))

        self.arch = os.popen("/bin/uname -m").read().strip()

        if self.arch in unsupportedArches:
            self.showErrorMessage(_("Sorry, this architecture does not "
                                    "currently support kdump"))
            sys.exit(1)

        memInfo = open("/proc/meminfo").readlines()
        totalMem = None
        for line in memInfo:
            if line.startswith("MemTotal:"):
                totalMem = int(line.split()[1]) / 1024

        if not totalMem:
            self.showErrorMessage(_("Failed to detect total system memory"))
            sys.exit(1)

        self.runningKernel = os.popen("/bin/uname -r").read().strip()

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
        kdumpOffset = 0
        self.origCrashKernel = ""
        self.kdumpEnabled = False
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
                (kdumpMem, kdumpOffset) = \
                           [int(m[:-1]) for m in crashString.split("@")]

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

        # Fix up memory calculations, if need be
        if kdumpMem != 0:
            self.kdumpEnabled = True
            self.kdumpEnableCheckButton.set_active(True)
            totalMem += kdumpMem
            self.origCrashKernel = "%dM@%dM" % (kdumpMem, kdumpOffset)
        else:
            self.kdumpEnableCheckButton.set_active(False)

        self.totalMemLabel.set_text(_("%s" % (totalMem,)))

        # Do some sanity-checking and try to present only sane options.
        #
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

        upperBound = (totalMem - minUsable) - (totalMem % step) 

        if upperBound < lowerBound:
            self.showErrorMessage(_("This system does not have enough "
                                    "memory for kdump to be viable"))
            sys.exit(1)

        # Set spinner to lowerBound unless already set on kernel command line
        if kdumpMem == 0:
            kdumpMem = lowerBound
        else:
            # round it down to a multiple of %step
            kdumpMem = kdumpMem - (kdumpMem % step)

        self.totalMem = totalMem
        self.kdumpMem = kdumpMem
        self.usableMem = self.totalMem - self.kdumpMem

        kdumpMemAdj = gtk.Adjustment(kdumpMem, lowerBound, upperBound, step, step, 64)
        self.kdumpMemSpinButton.set_adjustment(kdumpMemAdj)
        self.kdumpMemSpinButton.set_update_policy(gtk.UPDATE_IF_VALID)
        self.kdumpMemSpinButton.set_numeric(True)
        self.kdumpMemSpinButton.connect("value_changed", self.updateUsableMem)
        self.kdumpMemSpinButton.set_value(kdumpMem)

        self.usableMemLabel.set_text(_("%s" % (self.usableMem,)))

        if debug:
            print "totalMem = %dM\nkdumpMem = %dM\nusableMem = %dM" % (totalMem, kdumpMem, self.usableMem)

        self.defaultActionCombo = self.xml.get_widget("defaultActionCombo")

        for action in defaultActions:
            self.defaultActionCombo.append_text(action)

        self.defaultActionCombo.set_active(defaultActions.index(self.defaultAction))
        self.defaultActionCombo.connect("changed", self.setDefaultAction)

        self.pathEntry = self.xml.get_widget("pathEntry")
        self.coreCollectorEntry = self.xml.get_widget("coreCollectorEntry")
        self.locationEditButton = self.xml.get_widget("locationEditButton")
        self.locationEntry = self.xml.get_widget("locationEntry")

        self.setLocation(self.location)
        self.setPath()
        self.setCoreCollector()
        self.loadDumpConfig()

        self.advancedConfigTable = self.xml.get_widget("advancedConfigTable")
        self.locationEditButton.connect("clicked", self.editLocationHandler)
        self.pathEntry.connect("changed", self.updateLocationString)
        self.kdumpEnableCheckButton.connect("toggled", self.kdumpEnableToggled)
        self.kdumpEnabled = not self.kdumpEnabled # gonna get toggled next line
        self.kdumpEnableToggled()
        self.okButton = self.xml.get_widget("okButton")
        self.okButton.connect("clicked", self.okClicked)
        self.cancelButton = self.xml.get_widget("cancelButton")
        self.cancelButton.connect("clicked", self.cancelClicked)
        self.toplevel.connect("destroy", self.destroy)

        if not self.setBootloader():
            # find out now if they have a bootloader we know what to do with
            sys.exit(1)

    def run(self):
        self.toplevel.show_all()
        gtk.main()

    def destroy(self, *args):
        gtk.main_quit()

    def okClicked(self, *args):
        if not self.setCoreCollector():
            return

        if not self.setPath():
            return

        if self.location[0] not in (TYPE_RAW, TYPE_LOCAL) and not self.path:
            rc = self.yesNoDialog(_("Path cannot be empty for '%s' locations. "
                                    "Reset path to default ('%s')?."
                                    % (self.location[0], PATH_DEFAULT)))
            if rc == True:
                self.setPath(PATH_DEFAULT)
            else:
                return

        kernelKdumpNote = ""
        if self.arch in kernelKdumpArches:
            kernelKdumpNote = _("\n\nNote that the %s architecture does not "
                                "feature a relocatable kernel at this time, "
                                "and thus requires a separate kernel-kdump "
                                "package to be installed for kdump to "
                                "function. This can be installed via 'yum "
                                "install kernel-kdump' at your convenience."
                                "\n\n" % self.arch)

        if self.xenKernel and self.kdumpEnabled:
            self.showMessage(_("WARNING: xen kdump support requires a "
                               "non-xen %s RPM to perform actual crash "
                               "dump capture. Please be sure you have "
                               "the non-xen %s RPM of the same version "
                               "as your xen kernel installed." %
                               (self.xenKdumpKernel, self.xenKdumpKernel)))

        if self.kdumpEnabled:
            self.showMessage(_("Changing Kdump settings requires rebooting "
                               "the system to reallocate memory accordingly. "
                               "%sYou will have to reboot the system for the "
                               "new settings to take effect." 
                               % kernelKdumpNote))

        if not testing:
            if debug:
                print "writing kdump config"

            self.writeDumpConfig()

            if debug:
                print "writing bootloader config"

            self.writeBootloaderConfig()
        else:
            print "would have called writeDumpConfig"
            print "would have called writeBootloaderConfig"

        self.destroy()

    def cancelClicked(self, *args):
        self.destroy()

    def locationEditDialog(self, type=None, location=None):
        if type and location:
            title = _("Edit Location")
        else:
            title = _("New Location")

        d = gtk.Dialog(title=title, parent=self.toplevel, 
                        flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                        buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                                   gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        
        def typeChanged(*args):
            combo, locationEntry = args
            iter = combo.get_active_iter()
            type = combo.get_model().get_value(iter, 0).strip()
            if type == TYPE_DEFAULT:
                locationEntry.set_text(PATH_DEFAULT)
                locationEntry.set_sensitive(False)
            else:
                locationEntry.set_sensitive(True)
                if locationEntry.get_text().strip() == PATH_DEFAULT:
                    locationEntry.set_text("")

        vbox1 = gtk.VBox()
        label1 = gtk.Label(str=_("Select a location type:"))
        vbox1.add(label1)
        combo = gtk.combo_box_new_text()
        for typeStr in locationTypes:
            combo.append_text(typeStr)
        fstypes = []
        for fsck in [f for f in os.listdir("/sbin") if f.startswith("fsck.")]:
            if fsck[5:] in supportedFilesystemTypes:
                fstypes.append(fsck[5:])
        fstypes.sort()
        for fstype in fstypes:
            combo.append_text(fstype)

        vbox1.add(combo)
        vbox1.add(gtk.HSeparator())
        label2 = gtk.Label(str=_("Enter location:"))
        vbox1.add(label2)
        entry2 = gtk.Entry()
        vbox1.add(entry2)
        combo.connect("changed", typeChanged, entry2)
        vbox1.show_all()
        d.vbox.pack_start(vbox1)

        if type is None:
            combo.set_active(0)
        elif type in locationTypes:
            combo.set_active(locationTypes.index(type))
            entry2.set_text(location)
        elif type in fstypes:
            combo.set_active(fstypes.index(type) + len(locationTypes))
            entry2.set_text(location)

        while d.run() == gtk.RESPONSE_ACCEPT:
            iter = combo.get_active_iter()
            new_type = combo.get_model().get_value(iter, 0).strip()
            new_location = entry2.get_text().strip()
            if self.setLocation((new_type, new_location)):
                break

        d.destroy()

    def editLocationHandler(self, *args):
        (type, location) = self.location
        
        if type == TYPE_NET and location.count("@"):
            if debug:
                print "FIXUP: %s://%s => %s://%s" % (type, location,
                                                     TYPE_SSH, location)
            type = TYPE_SSH
        elif type == TYPE_NET:
            if debug:
                print "FIXUP: %s://%s => %s://%s" % (type, location,
                                                     TYPE_NFS, location)
            type = TYPE_NFS
            
        self.locationEditDialog(type, location)

    def setLocation(self, locationTuple=None):
        if debug:
            print "setLocation(", locationTuple, ")"

        if locationTuple is None and self.location is not None:
            type, location = self.location
        else:
            type, location = locationTuple         

        # fixup the type if necessary
        if type == TYPE_NET and location.count("@"):
            if debug:
                print "FIXUP: %s://%s => %s://%s" % (type, location,
                                                     TYPE_SSH, location)
            type = TYPE_SSH
        elif type == TYPE_NET:
            if debug:
                print "FIXUP: %s://%s => %s://%s" % (type, location,
                                                     TYPE_NFS, location)
            type = TYPE_NFS

        rc = True

        # try to validate the new location
        if type == TYPE_SSH:
            if not location.count("@") or location.count(":"):
                self.showErrorMessage(_("SSH locations must be of the form "
                                        "'user@host'. A path can be specified "
                                        "in the main window."))
                rc = False
        elif type == TYPE_NFS:
            if not location.count(":") or location.count("@"):
                self.showErrorMessage(_("NFS locations must be of the form "
                                        "'host:/path'"))
                rc = False
        elif type == TYPE_RAW:
            try:
                st = os.stat(location)
            except OSError:
                self.showErrorMessage(_("For raw locations you must specify "
                                        "a valid device node."))
                rc = False
            else:
                if not stat.S_ISBLK(st.st_mode):
                    self.showErrorMessage(_("For raw locations you must "
                                            "specify a valid device node."))
                    rc = False
        elif type == TYPE_LOCAL:
            pass
        else:
            if not os.access("/sbin/fsck.%s" % type, os.X_OK):
                self.showErrorMessage(_("Support for filesystem type '%s' "
                                        "is not present on this system" % type))
                rc = False

            # XXX need to find a way to validate labels & uuids
            if location.startswith("LABEL="):
                # look up and validate the device
                pass
            elif location.startswith("UUID="):
                # look up and validate the device
                pass
            else:
                try:
                    st = os.stat(location)
                except OSError:
                    self.showErrorMessage(_("Failed to stat device node "
                                            "'%s'" % location))
                    rc = False
                else:
                    if not stat.S_ISBLK(st.st_mode):
                        self.showErrorMessage(_("'%s' locations must specify "
                                                "a valid device node." % type))
                        rc = False

        if rc == True:
            self.location = (type, location)

            if type in (TYPE_RAW, TYPE_LOCAL):
                # unset path and freeze the entry
                self.setPath("")
                self.pathEntry.set_sensitive(False)
            else:
                path = self.pathEntry.get_text().strip()
                if not path or path == "/":
                    path = PATH_DEFAULT
                self.setPath(path)
                self.pathEntry.set_sensitive(True)

            if type in (TYPE_SSH, TYPE_RAW, TYPE_LOCAL):
                # unset core_collector and freeze the entry
                self.setCoreCollector("")
                self.coreCollectorEntry.set_sensitive(False)
            else:
                self.coreCollectorEntry.set_sensitive(True)

            if type == TYPE_LOCAL:
                self.defaultActionCombo.set_active(defaultActions.index(ACTION_DEFAULT))
                self.defaultActionCombo.set_sensitive(False)
            else:
                self.defaultActionCombo.set_sensitive(True)

            self.updateLocationString()

            if debug:
                print "location modified; now", self.location

        return rc

    def updateLocationString(self, *args):
        type, location = self.location
        if type in (TYPE_RAW, TYPE_LOCAL):
            self.setPath("")
            path = self.path
        else:
            self.setPath(self.pathEntry.get_text())
            path = self.path

        if type in (TYPE_NFS, TYPE_LOCAL, TYPE_RAW):
            delim = ""
            if path and not path.startswith("/"):
                # we're not really changing the path, just the locationText
                path = "/" + path
        else:
            delim = ":"

        locationText = "%s://%s%s%s" % (type, location, delim, path)
        self.locationEntry.set_text(locationText)
            
    def loadDumpConfig(self):
        try:
            lines = open(KDUMP_CONFIG_FILE).readlines()
        except IOError:
            return

        self.quiet(True)  # suppress error popups temporarily

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
            else:
                self.setLocation((type, location))

        # now we fix up the loaded config as needed
        if self.location[0] in (TYPE_LOCAL, TYPE_RAW):
            self.setPath("")
            self.pathEntry.set_sensitive(False)

        if self.location[0] in (TYPE_RAW, TYPE_SSH, TYPE_LOCAL):
            self.setCoreCollector("")
            self.coreCollectorEntry.set_sensitive(False)

        self.updateLocationString()
        # end fixups

        self.quiet(False)

    def writeDumpConfig(self):
        if testing or not self.kdumpEnabled:
            return

        if os.access(KDUMP_CONFIG_FILE, os.W_OK):
            # make a minimal effort at backing up an existing config
            try:
                os.rename(KDUMP_CONFIG_FILE, KDUMP_CONFIG_FILE + ".backup")
            except:
                pass

        fd = open(KDUMP_CONFIG_FILE, "w")
        # dump all of the comment lines from the original file into the new one
        fd.write("\n".join(self.kdumpConfigComments) + "\n")
        if self.location[0] in netLocationTypes:
            fd.write("net %s\n" % self.location[1])
        elif self.location[0] != TYPE_DEFAULT:
            fd.write("%s %s\n" % self.location)

        if self.path and self.path != PATH_DEFAULT:
            fd.write("path %s\n" % self.path)

        if self.coreCollector != CORE_COLLECTOR_DEFAULT:
            fd.write("core_collector %s\n" % self.coreCollector)

        if self.defaultAction != ACTION_DEFAULT:
            fd.write("default %s\n" % (self.defaultAction,))

        fd.close()

    def setBootloader(self):
        for (name, (conf, offset, kpath)) in bootloaders.items():
            # I hope order doesn't matter
            if os.access(conf, os.W_OK) or (testing and os.access(conf, os.F_OK)):
                self.bootloader = name

        if self.bootloader is None:
            self.showErrorMessage(_("No bootloader config file found, "
                                    "aborting configuration!"))
            return

        return self.bootloader

    def writeBootloaderConfig(self):
        if testing:
            return

        (blConfig, offset, kpath) = bootloaders[self.bootloader]

        # crashkerenl line goes in different places for xen vs. non-xen
        if self.xenKernel:
            args = 'mbargs'
            # x86_64 xen has issues @16M, use 32M instead
            if self.arch == 'x86_64':
                offset = 32
        else:
            args = 'args'

        # Are we adding or removing the crashkernel param?
        if self.kdumpEnabled:
            grubbyCmd = '/sbin/grubby --%s --update-kernel=%s/vmlinuz-%s --%s="crashkernel=%iM@%iM"' \
                        % (self.bootloader, kpath, self.runningKernel, 
                           args, self.kdumpMem, offset)
            chkconfigStatus = "on"
        else:
            grubbyCmd = '/sbin/grubby --%s --update-kernel=%s/vmlinuz-%s --remove-%s="crashkernel=%s"' \
                        % (self.bootloader, kpath, self.runningKernel, 
                           args, self.origCrashKernel)
            chkconfigStatus = "off"

        if debug:
            print "Using %s bootloader with %iM offset" % (self.bootloader, offset)
            print "Grubby command:\n    %s" % grubbyCmd

        # FIXME: use rhpl.executil (and handle errors)!
        os.system(grubbyCmd)
        os.system("/sbin/chkconfig kdump %s" % chkconfigStatus)
        if self.bootloader == 'yaboot':
            os.system('/sbin/ybin')

    def updateUsableMem(self, *args):
        self.kdumpMem = int(args[0].get_value())
        self.usableMem = self.totalMem - self.kdumpMem
        self.usableMemLabel.set_text("%s" % (self.usableMem,))
        if debug:
            print "setting usableMem to", self.usableMem

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

    def setPath(self, path=None):
        if path is None and self.path is not None:
            path = self.path
        elif path is None:
            path = PATH_DEFAULT

        # XXX are there are times (local_fs) when leading "/" is needed?
        #if path and not path.startswith("/"):
        #    path = "/" + path
        #    self.showErrorMessage(_("Path must start with '/'"))
        #    return False

        if debug:
            print "setting path to '%s'" % path
        self.path = path
        self.pathEntry.set_text(path)
        return True

    def setCoreCollector(self, collector=None):
        if collector is None and self.coreCollector is not None:
            collector = self.coreCollector
        elif not collector:
            collector = CORE_COLLECTOR_DEFAULT

        if collector and not collector.startswith("makedumpfile"):
            self.showErrorMessage(_("Core collector must begin with "
                                    "'makedumpfile'"))
            return False

        if debug:
            print "setting core_collector to '%s'" % collector
        self.coreCollector = collector
        self.coreCollectorEntry.set_text(collector)
        return True

    def kdumpEnableToggled(self, *args):
        if self.kdumpEnabled:
            self.kdumpEnabled = False
        else:
            self.kdumpEnabled = True

        if debug:
            print "setting kdumpEnabled to", self.kdumpEnabled

        self.memoryTable.set_sensitive(self.kdumpEnabled)
        self.advancedConfigTable.set_sensitive(self.kdumpEnabled)

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

    if not testing:
        uid = os.getuid()
        if uid != 0:
            w = mainWindow()
            w.showErrorMessage(_("You must be root to run this application."))
            sys.exit()

    win = mainWindow()
    win.setupScreen()
    win.run()


#!/usr/bin/python

# system-config-kdump - configures kexec/kdump
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

bootloaders = { "grub"   : ("/boot/grub/grub.conf", 16),
                "yaboot" : ("/boot/etc/yaboot.conf", 16),
                "elilo"  : ("/boot/efi/efi/redhat/elilo.conf", 256) }

locationTypes = ["nfs", "ssh", "raw"]
netLocationTypes = ("nfs", "ssh")
defaultActions = ["reboot", "shell", "none"]

DEFAULT_PATH = "/var/crash"

unsupportedArches = ("ppc", "s390", "s390x", "i386", "i586")
kernelKdumpArches = ("ppc64")
debug = 0 
testing = 0

KDUMP_BLURB = """
Kdump is a new kernel crash dumping mechanism. In the event of a system crash, a core file can be captured using kdump, which runs in the context of a freshly booted kernel, making it far more reliable than methods capturing within the context of the crashed kernel. Being able to capture a core file can be invaluable in helping determine the root cause of a system crash. Note that kdump does require reserving a portion of system memory that will be unavailable for other uses.
"""

LOCATION_BLURB = """
Kdump will attempt to place the vmcore at each of the following locations, in order, until it either succeeds or runs out of locations to try. In the event that it fails to place the vmcore at any location, the default action (specified above) will be executed.

If no locations are specified, the vmcore will be placed in 
/var/crash/YYYY-MM-DD-HH:mm/
"""

KDUMP_CONFIG_HEADER = """# Configures where to put the kdump /proc/vmcore files
#
# This file contains a series of commands to perform (in order) when a
# kernel crash has happened and the kdump kernel has been loaded
# 
# The commands are chained together to allow redundancy in case the 
# primary choice is not available at crash time
#
# Basics commands supported are:
# raw <partition> - will dd /proc/vmcore into <partition>
# net <nfs mount>     - will mount fs and copy /proc/vmcore to 
#			<mnt>/var/crash/%DATE/ , supports DNS
# net <user@location> - will scp /proc/vmcore to 
#			<user@location>:/var/crash/%DATE/, supports DNS
#			NOTE: Currently only the root user is supported
# <fs type> <partition> - will mount -t <fs type> <partition> /mnt and 
#                         copy /proc/vmcore to /mnt/var/crash/%DATE/.
#			  NOTE: <partition> can be a device node, label or uuid.
# path <path>	      - Append this path to the filesystem device which you 
#                       are dumping to 
#                       NOTE: only used with actual filesystems (ssh, nfs, 
#                             local fs).
#			NOTE: if unset, will default to /var/crash
# core_collector makedumpfile <options> - This directive allows you to use 
#                                         the dump filtering program 
#                                         makedumpfile to retrieve your core, 
#                                         which on some arches can drastically
#		                          reduce core file size.  see 
#                                         /sbin/makedumpfile --help for a list 
#                                         of options
#		        NOTE: the -i and -g options are not needed here, as 
#                             the initrd will automatically be populated with
#                             a config file appropriate for the running kernel 
# default <reboot | shell> - if all of the above fail, do the default action. 
#		      reboot: if the default action is reboot simply reboot 
#                             the system and lose the core that you are trying
#                             to retrieve
#		      shell:  if the default action is shell, then drop to an 
#                             msh session inside the initramfs from which you 
#                             can try to record the core manually.  exiting 
#                             this shell reboots the system
#		      NOTE: If no default action is specified, the initramfs 
#                           will mount the root file system and run init.

#raw /dev/sda5
#ext3 /dev/sda3
#ext3 LABEL=/boot
#ext3 UUID=03138356-5e61-4ab3-b58e-27507ac41937
#net my.server.com:/export/tmp
#net user@my.server.com
#path /var/crash
#core_collector makedumpfile -c
#default shell
"""

"""
    TODO:
        - validate all input before writing configs (ASAP, really)

"""
class mainWindow:
    def __init__(self):
        nameTag = _("Kernel Dump Configuration")
        commentTag = _("Configure kdump/kexec")

        self.xml = xml
        self.locations = []

        self.arch = None

        self.defaultAction = "reboot"
        self.path = DEFAULT_PATH
        self.coreCollector = ""

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
            self.showErrorMessage(_("Sorry, this architecture does not currently support kdump"))
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
        if self.runningKernel.find("xen") != -1:
            self.showErrorMessage(_("Sorry, Xen kernels do not support kdump at this time!"))
            sys.exit(1)

        # Fix up memory calculations in case kdump is already on
        cmdLine = open("/proc/cmdline").read()
        kdumpMem = 0
        kdumpOffset = 0
        if cmdLine.find("crashkernel=") > 1:
            self.kdumpEnabled = True
            self.kdumpEnableCheckButton.set_active(True)
            crashString = filter(lambda t: t.startswith("crashkernel="), cmdLine.split())[0].split("=")[1]
            (kdumpMem, kdumpOffset) = [int(m[:-1]) for m in crashString.split("@")]
            totalMem += kdumpMem
            self.origCrashKernel = "%dM@%dM" % (kdumpMem, kdumpOffset)
        else:
            self.kdumpEnableCheckButton.set_active(False)

        self.totalMemLabel.set_text(_("%s" % (totalMem,)))

        # Do some sanity-checking and try to present only sane options.
        #
        # Defaults
        lowerBound = 128
        upperBound = 512
        step = 64
        enoughMem = True
        # ia64 usually needs at *least* 256M, page-aligned... :(
        if self.arch == "ia64":
            lowerBound = 256
            step = 256
            if (totalMem - upperBound) < 512:
                enoughMem = False
        # If less than 1GB and not ia64, lower bounds
        elif (totalMem - upperBound) < 512:
            lowerBound = 64
            upperBound = 256
            # If less than 512MB, lower bounds further
            if (totalMem - upperBound) < 256:
                upperBound = 128
                # Okay, they simply don't have enough memory for kdump to be viable
                if (totalMem - upperBound) < 192:
                    self.showErrorMessage(_("This system does not have enough"
                                             "memory for kdump to be viable"))
                    sys.exit(1)
        
        # Set spinner to lowerBound to start unless already set on kernel command line
        if kdumpMem == 0:
            kdumpMem = lowerBound

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

        self.advancedConfigTable = self.xml.get_widget("advancedConfigTable")
        self.defaultActionCombo = self.xml.get_widget("defaultActionCombo")

        for action in defaultActions:
            self.defaultActionCombo.append_text(action)

        self.defaultActionCombo.set_active(defaultActions.index(self.defaultAction))
        self.defaultActionCombo.connect("changed", self.setDefaultAction)

        self.pathEntry = self.xml.get_widget("pathEntry")
        self.coreCollectorEntry = self.xml.get_widget("coreCollectorEntry")

        self.locationVBox = self.xml.get_widget("locationVBox")
        self.locationToolbar = self.xml.get_widget("locationToolbar")
        self.locationAddButton = self.xml.get_widget("locationAddButton")
        self.locationRemoveButton = self.xml.get_widget("locationRemoveButton")
        self.locationEditButton = self.xml.get_widget("locationEditButton")
        self.locationUpButton = self.xml.get_widget("locationUpButton")
        self.locationDownButton = self.xml.get_widget("locationDownButton")
        self.locationScrolledWindow = self.xml.get_widget("locationScrolledWindow")
        self.locationTreeView = self.xml.get_widget("locationTreeView")

        self.locationStore = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
       
        self.tooltips.set_tip(self.locationTreeView, _(LOCATION_BLURB))
        col = gtk.TreeViewColumn(_("Type"), gtk.CellRendererText(), text=0)
        self.locationTreeView.append_column(col)
        col = gtk.TreeViewColumn(_("Location"), gtk.CellRendererText(), text=1)
        self.locationTreeView.append_column(col)

        self.locationAddButton.connect("clicked", self.addLocationHandler)
        self.locationEditButton.connect("clicked", self.editLocationHandler)
        self.locationRemoveButton.connect("clicked", self.removeLocationHandler)
        self.locationUpButton.connect("clicked", self.promoteLocationHandler)
        self.locationDownButton.connect("clicked", self.demoteLocationHandler)

        self.loadDumpConfig()

        self.locationTreeView.set_model(self.locationStore)

        self.kdumpEnableCheckButton.connect("toggled", self.kdumpEnableToggled)
        self.kdumpEnabled = not self.kdumpEnabled # gonna get toggled next line
        self.kdumpEnableToggled()
        self.okButton = self.xml.get_widget("okButton")
        self.okButton.connect("clicked", self.okClicked)
        self.cancelButton = self.xml.get_widget("cancelButton")
        self.cancelButton.connect("clicked", self.cancelClicked)
        self.toplevel.connect("destroy", self.destroy)

    def run(self):
        self.toplevel.show_all()
        gtk.main()

    def destroy(self, *args):
        gtk.main_quit()

    def okClicked(self, *args):
        if not self.setBootloader():
            return

        if not self.setCoreCollector():
            return

        if not self.setPath():
            return

        kernelKdumpNote = ""
        if self.arch in kernelKdumpArches:
            kernelKdumpNote = "\n\nNote that the %s architecture does not feature a relocatable kernel at this time, and thus requires a separate kernel-kdump package to be installed for kdump to function. This can be installed via 'yum install kernel-kdump' at your convenience.\n\n" % self.arch

        if self.kdumpEnabled:
            self.showMessage(_("Changing Kdump settings requires rebooting the "
                           "system to reallocate memory accordingly. %sYou will"
                           " have to reboot the system for the new settings to "
                           "take effect." % kernelKdumpNote))

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
        
        def radioToggled(*args):
            button, widget = args
            widget.set_sensitive(button.get_active())

        vbox1 = gtk.VBox()
        label1 = gtk.Label(str=_("Select or enter a location type:"))
        vbox1.add(label1)
        table = gtk.Table(rows=2, columns=2, homogeneous=True)
        rb1 = gtk.RadioButton()
        rb2 = gtk.RadioButton(rb1)
        combo = gtk.combo_box_new_text()
        for typeStr in locationTypes:
            combo.append_text(typeStr)
        entry1 = gtk.Entry()
        rb1.connect("toggled", radioToggled, combo)
        rb2.connect("toggled", radioToggled, entry1)
        table.attach(rb1, 0, 1, 0, 1)
        table.attach(combo, 1, 2, 0, 1)
        table.attach(rb2, 0, 1, 1, 2)
        table.attach(entry1, 1, 2, 1, 2)
        vbox1.add(table)
        vbox1.add(gtk.HSeparator())
        label2 = gtk.Label(str=_("Enter location:"))
        vbox1.add(label2)
        entry2 = gtk.Entry()
        vbox1.add(entry2)
        vbox1.show_all()
        d.vbox.pack_start(vbox1)

        if type is None:
            combo.set_active(0)
            rb1.set_active(True)
            entry1.set_sensitive(False)
        elif type in locationTypes:
            combo.set_active(locationTypes.index(type))
            rb1.set_active(True)
            entry2.set_text(location)
            entry1.set_sensitive(False)
        else:
            entry1.set_text(type)
            rb2.set_active(True)
            entry2.set_text(location)
            combo.set_sensitive(False)

        while d.run() == gtk.RESPONSE_ACCEPT:
            if rb1.get_active():
                iter = combo.get_active_iter()
                new_type = combo.get_model().get_value(iter, 0).strip()
            else:
                new_type = entry1.get_text().strip()
                if not new_type:
                    self.showErrorMessage(_("You must specify a type for this location"))
                    continue

            new_location = entry2.get_text().strip()

            # try to validate the new location
            if new_type == "ssh":
                if new_location.find(":") == -1 or new_location.find("@") == -1:
                    self.showErrorMessage(_("SSH locations must be of the form 'user@host:/path'"))
                    continue
            elif new_type == "nfs":
                if new_location.find(":") == -1:
                    self.showErrorMessage(_("NFS locations must be of the form 'host:/path'"))
                    continue
            elif new_type == "raw":
                try:
                    st = os.stat(new_location)
                except OSError:
                    self.showErrorMessage(_("Failed to stat device node '%s'" % new_location))
                    continue
                else:
                    if not stat.S_ISBLK(st.st_mode):
                        self.showErrorMessage(_("For raw locations you must specify a valid device node."))
                        continue
            else:
                if not os.access("/sbin/fsck.%s" % new_type, os.X_OK):
                    self.showErrorMessage(_("Support for filesystem type '%s' is not present on this system" % new_type)) 
                    continue

                # XXX need to find a way to validate labels & uuids
                if new_location.startswith("LABEL="):
                    # look up and validate the device
                    pass
                elif new_location.startswith("UUID="):
                    # look up and validate the device
                    pass
                else:
                    try:
                        st = os.stat(new_location)
                    except OSError:
                        self.showErrorMessage(_("Failed to stat device node '%s'" % new_location))
                        continue
                    else:
                        if not stat.S_ISBLK(st.st_mode):
                            self.showErrorMessage(_("'%s' locations must specify a valid device node." % new_type))
                            continue

            # everything appears to be in order
            retval = (new_type, new_location)
            break
        else:
            retval = (type, location)

        d.destroy()
        return retval

    def addLocationHandler(self, *args):
        (type, location) = self.locationEditDialog()
        if type and location:
            self.addLocation(type, location)

    def getActiveLocation(self):
        iter = self.locationTreeView.get_selection().get_selected()[1]
        if iter is None:
            return

        return self.locationStore.get(iter, 0, 1)

    def editLocationHandler(self, *args):
        iter = self.locationTreeView.get_selection().get_selected()[1]
        if iter is None:
            return

        (type, location) = self.locationStore.get(iter, 0, 1)
        
        new_loc = self.locationEditDialog(type, location)
        if new_loc == (type, location):
            return

        if new_loc[0] and new_loc[1]:
            self.locationStore.set(iter, 0, new_loc[0], 1, new_loc[1])

    def removeLocationHandler(self, *args):
        iter = self.locationTreeView.get_selection().get_selected()[1]
        if iter is None:
            return

        location = self.locationStore.get(iter, 0, 1)
        if not location in self.locations:
            return
        self.locationStore.remove(iter)
        self.removeLocation(location)

    def promoteLocationHandler(self, *args):
        iter = self.locationTreeView.get_selection().get_selected()[1]
        if iter is None:
            return

        activeLocation = self.locationStore.get(iter, 0, 1)
        if not activeLocation in self.locations:
            return

        if activeLocation == self.locations[0]:
            return

        if debug:
            print "promoting location", activeLocation
            print "locations is", self.locations

        i = self.locations.index(activeLocation)
        l2 = self.locations[i-1:i+1]
        l2.reverse()
        self.locations[i-1:i+1] = l2
        row = self.locationStore.get_string_from_iter(iter)
        prevRow = str(int(row) - 1)
        prevIter = self.locationStore.get_iter_from_string(prevRow)
        self.locationStore.swap(prevIter, iter)
        
        if debug:
            print "locations modified; now", self.locations

    def demoteLocationHandler(self, *args):
        iter = self.locationTreeView.get_selection().get_selected()[1]
        if iter is None:
            return

        activeLocation = self.locationStore.get(iter, 0, 1)
        if not activeLocation in self.locations:
            return

        if activeLocation == self.locations[-1]:
            return

        if debug:
            print "demoting location", activeLocation
            print "locations is", self.locations

        i = self.locations.index(activeLocation)
        l2 = self.locations[i:i+2]
        l2.reverse()
        self.locations[i:i+2] = l2
        next = self.locationStore.iter_next(iter)
        self.locationStore.swap(iter, next)
        if debug:
            print "locations modified; now", self.locations

    def removeLocation(self, item):
        (type, location) = item

        if debug:
            print "removeLocation (%s, %s)" % (type, location)
            print "locations is", self.locations

        self.locations.remove(item)
        if debug:
            print "locations modified; now", self.locations

    def addLocation(self, type, location):
        if debug:
            print "addLocation (%s, %s)" % (type, location)
            print "locations is", self.locations

        # fixup the type
        if type == "net" and location.find("@") > -1:
            type = "ssh"
        elif type == "net":
            type = "nfs"

        if (type, location) in self.locations:
            if debug:
                print "location (\'%s\', \'%s\') already in locations" % (type, 
                                                                      location)
            return

        self.locations.append((type, location))
        self.locationStore.append([type, location])
        if debug:
            print "locations modified; now", self.locations
            
    def loadDumpConfig(self):
        try:
            lines = open(KDUMP_CONFIG_FILE).readlines()
        except IOError:
            return

        for line in [l.strip() for l in lines]:
            if not line:
                continue

            i = line.find("#")
            if i != -1:
                line = line[:i].strip()
                if not line:
                    continue

            try:
                type, location = line.split()
            except ValueError:
                print "Failed to parse line; chucking it..."
                print "  \'%s\'" % (line,)
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
                self.addLocation(type, location)

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
        fd.write(KDUMP_CONFIG_HEADER)
        for location in self.locations:
            if location[0] in netLocationTypes:
                fd.write("net %s %s\n" % location)
            else:
                fd.write("%s %s\n" % location)

        fd.write("path %s\n" % self.path)

        if self.coreCollector:
            fd.write("core_collector %s\n" % self.coreCollector)

        if self.defaultAction != "none":
            fd.write("default %s\n" % (self.defaultAction,))

        fd.close()

    def setBootloader(self):
        for (name, (conf, offset)) in bootloaders.items():
            # I hope order doesn't matter
            if os.access(conf, os.W_OK) or (testing and os.path.exists(conf)):
                self.bootloader = name

        if self.bootloader is None:
            self.showErrorMessage(_("Error! No bootloader config file found, aborting configuration!"))
            self.destroy()

        return self.bootloader

    def writeBootloaderConfig(self):
        if testing:
            return

        offset = bootloaders[self.bootloader][1]

        # Are we adding or removing the crashkernel param?
        if self.kdumpEnabled:
            grubbyCmd = '/sbin/grubby --%s --update-kernel=/boot/vmlinuz-%s --args="crashkernel=%iM@%iM"' \
                        % (self.bootloader, self.runningKernel, 
                           self.kdumpMem, offset)
            chkconfigStatus = "on"
        else:
            grubbyCmd = '/sbin/grubby --%s --update-kernel=/boot/vmlinuz-%s --remove-args="crashkernel=%s"' \
                        % (self.bootloader, self.runningKernel, 
                           self.origCrashKernel)
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

    def setPath(self, path=None):
        if path is None:
            # grab the path from the UI
            path = self.pathEntry.get_text().strip()
            if not path:
                path = DEFAULT_PATH

        if not path.startswith("/"):
            self.showErrorMessage(_("Path must start with '/'"))
            return False

        self.path = path
        self.pathEntry.set_text(path)
        return True

    def setCoreCollector(self, collector=None):
        if collector is None:
            # grab the value from the UI
            collector = self.coreCollectorEntry.get_text().strip()

        if collector and not collector.startswith("makedumpfile"):
            self.showErrorMessage(_("Core collector must begin with 'makedumpfile'"))
            return False

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
        self.locationVBox.set_sensitive(self.kdumpEnabled)

    def showErrorMessage(self, text):
        dlg = gtk.MessageDialog(None, 0, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, text)
        dlg.set_position(gtk.WIN_POS_CENTER)
        dlg.set_modal(True)
        dlg.run()
        dlg.destroy()

    def showMessage(self, text, type=None):
        if type is None:
            type = gtk.MESSAGE_INFO

        dlg = gtk.MessageDialog(None, 0, type, gtk.BUTTONS_OK, text)
        dlg.set_position(gtk.WIN_POS_CENTER)
        dlg.set_modal(True)
        dlg.run()
        dlg.destroy()

    def okCancelDialog(self, text):
        dlg = gtk.Dialog(title=title, parent=None, 
                         flags=gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                         buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                                    gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
 
        dlg.vbox.add(gtk.Label(str=text))
        dlg.set_position(gtk.WIN_POS_CENTER)
        dlg.set_modal(True)
        ret = dlg.run()
        dlg.destroy()
        if ret == gtk.RESPONSE_ACCEPT:
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


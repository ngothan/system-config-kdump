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
# import gobject
import gtk.glade
from gtk.gdk import keyval_name
from rhpl.executil import gtkExecWithCaptureStatus

import sys
import os
# import stat

##
## dbus and polkit
##
import dbus

try:
    # try to import the module installed in the system
    import slip.dbus.service
except ImportError:
    # try to find the module in the unpacked source tree
    import os.path
    import import_marker

    # try to find the slip.dbus module

    MODFILE = import_marker.__file__
    PATH = os.path.dirname (MODFILE)
    FOUND = False
    OLDSYSPATH = sys.path
    while not FOUND and PATH and PATH != "/":
        PATH = os.path.abspath (os.path.join (PATH, os.path.pardir))
        sys.path = OLDSYSPATH + [PATH]
        try:
            import slip.dbus.service
            FOUND = True
        except ImportError:
            pass
    if not FOUND:
        import slip.dbus.service
    sys.path = OLDSYSPATH

#system_bus = dbus.SystemBus ()

from slip.dbus import polkit

##
## I18N
##
from rhpl.translate import _, N_
import rhpl.translate as translate
DOMAIN = "system-config-kdump"
translate.textdomain (DOMAIN)
gtk.glade.bindtextdomain(DOMAIN)

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

TAG_CURRENT = _("(c)")
TAG_DEFAULT = _("(d)")

# got from kernel/Documentation/devices.txt
SUPPORTED_MAJOR = [ '2', '3', '8', '9', '13', '14', '19', '21', '22', '28',
                    '31', '33', '34', '36', '40', '44', '45', '47', '48', '49',
                    '50', '51', '52', '53', '54', '55', '56', '57', '65', '66',
                    '67', '68', '69', '70', '71', '88', '89', '90', '91', '94',
                    '99', '128', '129', '130', '131', '132', '133', '134',
                    '135', '147', '180' ]

PATH_DEFAULT = "/var/crash"
CORE_COLLECTOR_DEFAULT = "makedumpfile -c"

ENTER_CODES = ["KP_Enter", "Return"]

VERSION = "1.0.0"

AUTHORS = [
    "Dave Lehman <dlehman@redhat.com>",
    "Jarod Wilson <jwilson@redhat.com>",
    "Roman Rakus <rrakus@redhat.com>",
    ]

LICENSE = _(
    "This program is free software; you can redistribute it and/or modify "
    "it under the terms of the GNU General Public License as published by "
    "the Free Software Foundation; either version 2 of the License, or "
    "(at your option) any later version.\n"
    "\n"
    "This program is distributed in the hope that it will be useful, "
    "but WITHOUT ANY WARRANTY; without even the implied warranty of "
    "MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the "
    "GNU General Public License for more details.\n"
    "\n"
    "You should have received a copy of the GNU General Public License "
    "along with this program; if not, write to the Free Software "
    "Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.")

COPYRIGHT = '(C) 2006 - 2009 Red Hat, Inc.'




DEFAULTACTIONS = [ACTION_DEFAULT, ACTION_REBOOT, ACTION_SHELL, ACTION_HALT]

SUPPORTEDFSTYPES = ("ext2", "ext3")

UNSUPPORTED_ARCHES = ("ppc", "s390", "s390x", "i386", "i586")
KERNEL_KDUMP_ARCHES = ("ppc64")
DEBUG = 0 
TESTING = 0

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
tab 2 target setup
tab 3 initrd selection
localizations
using rhpl
XEN support - need change in grubby
help
"""

# all needed for Python-slip, PoilcyKit and dbus
class DBusProxy (object):
    """
    Class used for communication with/via dbus
    """

    def __init__ (self):
        self.bus = dbus.SystemBus ()
        self.dbus_object = self.bus.get_object ("org.fedoraproject.systemconfig.kdump.mechanism", "/org/fedoraproject/systemconfig/kdump/object")

    @polkit.enable_proxy
    def getdefaultkernel (self):
        """
        Return name of default kernel set in bootloader configuration string
        """
        return self.dbus_object.getdefaultkernel (dbus_interface = "org.fedoraproject.systemconfig.kdump.mechanism")

    @polkit.enable_proxy
    def getcmdline (self, kernel):
        """
        Return command line arguments for specific kernel
        """
        return self.dbus_object.getcmdline (kernel, dbus_interface = "org.fedoraproject.systemconfig.kdump.mechanism")

    @polkit.enable_proxy
    def getxencmdline (self, kernel):
        """
        Return command line arguments for specific xen kernel
        """
        return self.dbus_object.getxencmdline (kernel, dbus_interface = "org.fedoraproject.systemconfig.kdump.mechanism")

    @polkit.enable_proxy
    def getallkernels (self):
        """
        Return name of all kernels in bootloader configuration files separated by newline (\n)
        """
        return self.dbus_object.getallkernels (dbus_interface = "org.fedoraproject.systemconfig.kdump.mechanism")

    @polkit.enable_proxy
    def writedumpconfig (self, config_string):
        """
        Write config_string string to kdump.conf file and returns same string if no errors
        """
        return self.dbus_object.writedumpconfig (config_string, dbus_interface = "org.fedoraproject.systemconfig.kdump.mechanism")

    @polkit.enable_proxy
    def writebootconfig (self, config_string):
        """
        Update bootloader configuration. config_string is grubby arguments. Return error messages, if any.
        """
        return self.dbus_object.writebootconfig (config_string, dbus_interface = "org.fedoraproject.systemconfig.kdump.mechanism")




# This class contains every settings
class Settings:
    """
    Class used for storing settings
    """
    def __init__(self):
        self.kdump_enabled = False          # whether kdump is enabled
        self.kdump_mem = 0                  # amount of kdump memory
        self.kdump_offset = 0               # kdump mem offset
        self.target_type = TYPE_DEFAULT     # crash dump target type
        self.path = PATH_DEFAULT            # local fs path, where to save kdump
        self.local_partition = ""           # local fs partition, where...
        self.raw_device = ""                # raw device, where...
        self.server_name = ""               # network server, where...
        self.user_name = ""                 # user on server
        self.filter_level = 0               #
        self.initrd = ""                    # which initrd we will use
        self.kernel = ""                    # which kernel
        self.orig_commandline = ""          #
        self.commandline = ""               # kernel arguments
        self.default_action = ACTION_DEFAULT#
        self.core_collector = CORE_COLLECTOR_DEFAULT# core collector settings

    # set location type, path, raw device, partition and so on
    def set_location(self, location_type, path):
        """
        Set location type and path. These two variables are read from kdump.conf
        and are appropriately parsed. Then we save user and server name,
        raw device, path and so on. Look at kdump.conf to more info.
        """
        self.target_type = location_type
        # SSH or NFS
        if location_type == TYPE_NET:
            if path.find("@") != -1:
                # SSH
                (self.user_name, self.server_name) = path.split("@")
                self.target_type = TYPE_SSH
            else:
                # NFS
                self.server_name = path
                self.target_type = TYPE_NFS

        # RAW
        elif location_type == TYPE_RAW:
            self.raw_device = path

        elif location_type == TYPE_LOCAL:
            self.path = path

        # One of supported partition type
        else:
            self.local_partition = "%s %s" % (location_type, path)
            self.target_type = TYPE_LOCAL

    def copy_settings(self, dest_settings):
        """
        copy settings from self to dest_settings
        """
        dest_settings.kdump_enabled = self.kdump_enabled
        dest_settings.kdump_mem = self.kdump_mem
        dest_settings.kdump_offset = self.kdump_offset
        dest_settings.target_type = self.target_type
        dest_settings.path = self.path
        dest_settings.local_partition = self.local_partition
        dest_settings.raw_device = self.raw_device
        dest_settings.server_name = self.server_name
        dest_settings.user_name = self.user_name
        dest_settings.filter_level = self.filter_level
        dest_settings.initrd = self.initrd
        dest_settings.kernel = self.kernel
        dest_settings.commandline = self.commandline
        dest_settings.orig_commandline = self.orig_commandline
        dest_settings.default_action = self.default_action
        dest_settings.core_collector = self.core_collector

    def check_settings(self, ref_settings):
        """
        Returns if self and reference settings are same.
        """
        if ref_settings.kdump_enabled != self.kdump_enabled:
            if DEBUG:
                print "differ on kdump_enabled"
            return 0

        if ref_settings.kdump_mem != self.kdump_mem:
            if DEBUG:
                print "differ on kdump_mem"
                print "ref: (str) <%s>" % (ref_settings.kdump_mem)
                print "self: (str) <%s>" % (self.kdump_mem)
            return 0

        if ref_settings.kdump_offset != self.kdump_offset:
            if DEBUG:
                print "differ on kdump_offset"
            return 0


        if ref_settings.target_type != self.target_type:
            if DEBUG:
                print "differ on target_type"
                print "ref: (str) <%s>" % (ref_settings.target_type)
                print "self: (str) <%s>" % (self.target_type)
            return 0

        if ref_settings.path != self.path:
            if DEBUG:
                print "differ on path"
            return 0

        if ref_settings.local_partition != self.local_partition:
            if DEBUG:
                print "differ on local_partition"
                print "ref: (str) <%s>" % (ref_settings.local_partition)
                print "self: (str) <%s>" % (self.local_partition)

            return 0

        if ref_settings.raw_device != self.raw_device:
            if DEBUG:
                print "differ on raw_device"
            return 0

        if ref_settings.server_name != self.server_name:
            if DEBUG:
                print "differ on server_name"
            return 0

        if ref_settings.user_name != self.user_name:
            if DEBUG:
                print "differ on user_name"
            return 0

        if ref_settings.filter_level != self.filter_level:
            if DEBUG:
                print "differ on filter_level"
            return 0

        if ref_settings.initrd != self.initrd:
            if DEBUG:
                print "differ on initrd"
            return 0

        if ref_settings.kernel != self.kernel:
            if DEBUG:
                print "differ on kernel"
                print "ref: (str) <%s>" % (ref_settings.kernel)
                print "self: (str) <%s>" % (self.kernel)
            return 0

        if ref_settings.commandline != self.commandline:
            if DEBUG:
                print "differ on commandline"
                print "ref: (str) <%s>" % (ref_settings.commandline)
                print "self: (str) <%s>" % (self.commandline)
            return 0

        if ref_settings.orig_commandline != self.orig_commandline:
            if DEBUG:
                print "differ on orig_commandline"
                print "ref: (str) <%s>" % (ref_settings.orig_commandline)
                print "self: (str) <%s>" % (self.orig_commandline)

            return 0

        if ref_settings.default_action != self.default_action:
            if DEBUG:
                print "differ on default_action"
            return 0

        if ref_settings.core_collector != self.core_collector:
            if DEBUG:
                print "differ on core_collector"
            return 0

        return 1


class MainWindow:
    """
    Main window. What user see.
    """
    def __init__(self):
        if os.access("system-config-kdump.glade", os.F_OK):
            self.xml = gtk.glade.XML ("./system-config-kdump.glade", domain=DOMAIN)
        else:
            self.xml = gtk.glade.XML ("/usr/share/system-config-kdump/system-config-kdump.glade", domain=DOMAIN)


        self.dbus_object = DBusProxy()
        self.orig_settings = Settings()
        self.my_settings = Settings()

        #                  fsType, partition
        self.partitions = [(None, "file:///")]
        self.raw_devices = []

        self.arch = None

        self._quiet = False # if set, don't pop up any message boxes or dialogs
    
        self.kdump_config_comments = []
        self.misc_config = []

        self.filters = [False] * (NUM_FILTERS)
        self.filter_check_button = [gtk.CheckButton for x in range(NUM_FILTERS)]

        self.total_mem = 0
        self.usable_mem = 0
        self.kernel_prefix = "/"

        self.default_kernel = self.default_kernel_name()[:-1]
        self.running_kernel = os.popen("/bin/uname -r").read().strip()

        self.bootloader = None
        self.arch = os.popen("/bin/uname -m").read().strip()

        # load widgets from glade file
        self.toplevel = self.xml.get_widget("mainWindow")
        self.about_dialog = self.xml.get_widget("aboutdialog")

        self.kdump_notebook = self.xml.get_widget("kdumpNotebook")

        # menu
        self.menu_apply             = self.xml.get_widget("menuitemapply")
        self.menu_reload            = self.xml.get_widget("menuitemreload")
        self.menu_quit              = self.xml.get_widget("menuitemquit")
        self.menu_enable            = self.xml.get_widget("menuitemEnable")
        self.menu_disable           = self.xml.get_widget("menuitemDisable")
        self.menu_about             = self.xml.get_widget("imagemenuitemAbout")
        self.menu_help              = self.xml.get_widget("imagemenuitemHelp")

        # toolbar
        self.enable_button          = self.xml.get_widget("toolbuttonEnable")
        self.disable_button         = self.xml.get_widget("toolbuttonDisable")
        self.apply_button           = self.xml.get_widget("toolbuttonApply")
        self.reload_button          = self.xml.get_widget("toolbuttonReload")
        self.help_button            = self.xml.get_widget("toolbuttonHelp")

        # tab 0
        self.total_mem_label         = self.xml.get_widget("totalMem")
        self.kdump_mem_current_label = self.xml.get_widget("kdumpMemCurrent")
        self.kdump_mem_spin_button   = self.xml.get_widget("kdumpMemSpinButton")
        self.usable_mem_label        = self.xml.get_widget("usableMem")

        # tab 1
        self.localfs_radiobutton      = self.xml.get_widget("localfsRadiobutton")
        self.partition_combobox       = self.xml.get_widget("partitionCombobox")
        self.location_entry           = self.xml.get_widget("locationEntry")
        self.table_localfs            = self.xml.get_widget("tableLocalfs")
        self.local_filechooser_button = self.xml.get_widget("localFilechooserbutton")
        self.raw_device_radiobutton   = self.xml.get_widget("rawDeviceRadiobutton")
        self.device_combobox          = self.xml.get_widget("deviceCombobox")
        self.network_radiobutton      = self.xml.get_widget("networkRadiobutton")
        self.network_type_vbox        = self.xml.get_widget("networkTypeVbox")
        self.nfs_radiobutton          = self.xml.get_widget("nfsRadiobutton")
        self.ssh_radiobutton          = self.xml.get_widget("sshRadiobutton")
        self.network_config_table     = self.xml.get_widget("networkConfigTable")
        self.username_entry           = self.xml.get_widget("usernameEntry")
        self.path_entry               = self.xml.get_widget("pathEntry")
        self.servername_entry         = self.xml.get_widget("servernameEntry")

        # tab 2
        for x in range(NUM_FILTERS):
            self.filter_check_button[x]      = self.xml.get_widget("filterCheckbutton%d" % x)
        self.filter_level_label              = self.xml.get_widget("filterLevelLabel")
#        self.elf_file_format_radio_button      = self.xml.get_widget("elfFileFormatRadioButton")
#        self.diskdupm_file_format_radio_button = self.xml.get_widget("diskdumpFileFormatRadioButton")


        # tab 3
#        self.default_initrd_radio_button = self.xml.get_widget("defaultInitrdRadiobutton")
        self.custom_initrd_radio_button  = self.xml.get_widget("customInitrdRadiobutton")
        self.initrd_file_chooser_button  = self.xml.get_widget("initrdFilechooserbutton")
        self.default_kernel_radio_button = self.xml.get_widget("defaultKernelRadiobutton")
        self.custom_kernel_radio_button  = self.xml.get_widget("customKernelRadiobutton")
        self.custom_kernel_combobox      = self.xml.get_widget("customKernelCombobox")
        self.original_command_line_entry = self.xml.get_widget("originalCommandLineEntry")
        self.command_line_entry          = self.xml.get_widget("commandLineEntry")
        self.clear_cmdline_button        = self.xml.get_widget("clearCmdlineButton")
        self.default_action_combobox     = self.xml.get_widget("defaultActionCombo")
        self.core_collector_entry        = self.xml.get_widget("coreCollectorEntry")



    def setup_screen(self):
        """
        Load widgets, load settings...
        """

        # widgets setup and signals connect
        self.toplevel.connect("destroy", self.destroy)

        # menu
        self.menu_enable.connect("activate", self.kdump_enable_toggled)
        self.menu_disable.connect("activate", self.kdump_enable_toggled)
        self.menu_quit.connect("activate", self.destroy)
        self.menu_about.connect("activate", self.show_about_dialog)
        self.menu_reload.connect("activate", self.reset_settings)
        self.menu_apply.connect("activate", self.apply_clicked)
        self.menu_help.connect("activate", self.show_help)
        self.about_dialog.set_transient_for(self.toplevel)
        self.about_dialog.set_version(VERSION)
        self.about_dialog.set_authors(AUTHORS)
        self.about_dialog.set_license(LICENSE)
        self.about_dialog.set_copyright(COPYRIGHT)


        # toolbar
        self.enable_button.connect("clicked", self.kdump_enable_toggled)
        self.disable_button.connect("clicked", self.kdump_enable_toggled)
        self.reload_button.connect("clicked", self.reset_settings)
        self.apply_button.connect("clicked", self.apply_clicked)
        self.help_button.connect("clicked", self.show_help)

        # tab 0
        self.kdump_mem_spin_button.connect("value_changed", self.update_usable_mem)

        # tab 1
        self.localfs_radiobutton.connect("toggled", self.target_type_changed)
        self.raw_device_radiobutton.connect("toggled", self.target_type_changed)
        self.network_radiobutton.connect("toggled", self.target_type_changed)
        self.nfs_radiobutton.connect("toggled", self.nfs_changed)
        self.setup_partitions(self.partition_combobox)
        self.partition_combobox.connect("changed", self.changed_partition)
        self.setup_raw_devices(self.device_combobox)
        self.device_combobox.connect("changed", self.changed_raw_device)
        self.location_entry.connect("focus-out-event", self.location_changed)
        self.location_entry.connect("key-press-event", self.catch_enter, self.location_changed)
        self.local_filechooser_button.connect("selection-changed", self.location_changed)
        self.path_entry.connect("focus-out-event", self.path_changed)
        self.path_entry.connect("key-press-event", self.catch_enter, self.path_changed)
        self.servername_entry.connect("focus-out-event", self.servername_changed)
        self.servername_entry.connect("changed", self.servername_changed)
        self.username_entry.connect("focus-out-event", self.username_changed)
        self.username_entry.connect("changed", self.username_changed)

        # tab 2
        for x in range(NUM_FILTERS):
            self.filter_check_button[x].connect("toggled", self.filter_changed)

        # tab 3
        self.custom_initrd_radio_button.connect("toggled", self.custom_initrd_changed)
        self.custom_kernel_radio_button.connect("toggled", self.custom_kernel_changed)
        self.initrd_file_chooser_button.set_current_folder("/boot")
        line = self.get_cmdline(self.default_kernel)
        self.original_command_line_entry.set_text(line)
        self.command_line_entry.set_text(line)
        self.setup_custom_kernel_combobox(self.custom_kernel_combobox)
        self.custom_kernel_combobox.connect("changed", self.update_cmdline)
        self.command_line_entry.connect("focus-out-event", self.cmdline_changed)
        self.command_line_entry.connect("key-press-event", self.catch_enter, self.cmdline_changed)
        self.clear_cmdline_button.connect("clicked", self.reset_cmdline)
        self.core_collector_entry.connect("focus-out-event", self.collector_entry_changed)
        self.core_collector_entry.connect("key-press-event", self.catch_enter, self.collector_entry_changed)
        self.default_action_combobox.connect("changed", self.set_default_action)

        self.tooltips = gtk.Tooltips()

        # check architecture
        if self.arch in UNSUPPORTED_ARCHES:
            self.show_error_message(_("Sorry, this architecture does not "
                                    "currently support kdump"),
                                    _("system-config-kdump: kdump not supported"))
            sys.exit(1)

        # get total memory of system
        total_mem = None
        for line in open("/proc/meminfo").readlines():
            if line.startswith("MemTotal:"):
                total_mem = int(line.split()[1]) / 1024

        if not total_mem:
            self.show_error_message(_("Failed to detect total system memory"), _("system-config-kdump: Memory error"))
            sys.exit(1)


        # Check for a xen kernel, we do things a bit different w/xen
        self.xen_kernel = False
        if os.access("/proc/xen", os.R_OK):
            self.xen_kernel = True

        if self.xen_kernel and self.arch == 'ia64':
            self.show_error_message(_("Sorry, ia64 xen kernels do not support kdump "
                                    "at this time."), _("system-config-kdump: kdump not supported"))
            sys.exit(1)

        # Check to see if kdump memory is already reserved
        # Read from /proc/iomem so we're portable across xen and non-xen
        kdump_mem = 0
        kdump_mem_grubby = 0
        kdump_offset = 0
        kdump_offset_grubby = 0
        # PowerPC64 doesn't list crashkernel reservation in /proc/iomem
        if self.arch != 'ppc64':
            io_mem = open("/proc/iomem").readlines()
            for line in io_mem:
                if line.find("Crash kernel") != -1:
                    hex_ck_start = line.strip().split("-")[0]
                    hex_ck_end = line.strip().split("-")[1].split(":")[0].strip()
                    kdump_offset = self.hex2mb(hex_ck_start)
                    kdump_mem = self.hex2mb(hex_ck_end) - kdump_offset
                    break
        else:
            cmdline = open("/proc/cmdline").read()
            if cmdline.find("crashkernel=") > -1:
                crash_string = filter(lambda t: t.startswith("crashkernel="), 
                                     cmdline.split())[0].split("=")[1]
                tokens = crash_string.split("@")
                kdump_mem = int(tokens[0][:-1])
                if len(tokens) == 2:
                    kdump_offset = int(tokens[1][:-1])

        # i686 xen requires kernel-PAE for kdump if any memory
        # is mapped above 4GB
        self.xen_kdump_kernel = "kernel"
        if self.arch == "i686" and self.xen_kernel:
            for line in io_mem:
                if line.find("System RAM") != -1:
                    range_end = line.strip().split("-")[1].split(":")[0].strip()
                    if range_end >= 0x100000000L:
                        self.xen_kdump_kernel = "kernel-PAE"
                        break

	# read current kdump settings from grubby
        (kdump_mem_grubby, kdump_offset_grubby) = self.grubby_crashkernel()

        # Defaults
        lower_bound = 128
        min_usable = 512
        step = 64


        if self.arch == 'ia64':
            # ia64 needs at least 256M, page-aligned
            lower_bound = 256
            step = 256
        elif self.arch == 'ppc64':
            lower_bound = 256
            min_usable = 2048



        # Fix up memory calculations, if need be
        if kdump_mem_grubby != 0:
            self.orig_settings.kdump_enabled = True
            self.kdump_enable_toggled(self.enable_button)
            total_mem += kdump_mem
            self.orig_settings.kdump_offset = kdump_offset
            self.orig_settings.kdump_mem = kdump_mem_grubby

        else:
            kdump_mem_grubby = lower_bound
            self.orig_settings.kdump_enabled = False
            self.kdump_enable_toggled(self.disable_button)

        self.total_mem_label.set_text("%s (MB)" % (total_mem,))

        # Do some sanity-checking and try to present only sane options.
        upper_bound = (total_mem - min_usable) - (total_mem % step) 

        if upper_bound < lower_bound:
            self.show_error_message(_("This system does not have enough "
                                    "memory for kdump to be viable"), _("system-config-kdump: Not enough memory"))
            sys.exit(1)

        # Set spinner to lower_bound unless already set on kernel command line
        if kdump_mem != 0:
            # round it down to a multiple of %step
            kdump_mem = kdump_mem - (kdump_mem % step)
            self.orig_settings.kdump_mem = kdump_mem

        self.total_mem = total_mem
        self.usable_mem = self.total_mem - kdump_mem

        self.kdump_mem_current_label.set_text("%s (MB)" % (kdump_mem))

        kdump_mem_adj = gtk.Adjustment(kdump_mem, lower_bound, upper_bound, step, step, 64)
        self.kdump_mem_spin_button.set_adjustment(kdump_mem_adj)
        self.kdump_mem_spin_button.set_update_policy(gtk.UPDATE_IF_VALID)
        self.kdump_mem_spin_button.set_numeric(True)
        self.kdump_mem_spin_button.set_value(kdump_mem_grubby)
        self.update_usable_mem(self.kdump_mem_spin_button)

        self.usable_mem_label.set_text("%s (MB)" % (self.usable_mem,))

        if DEBUG:
            print "total_mem = %dM\nkdump_mem = %dM\nkdump_mem_grubby = %dM\nusable_mem = %dM" % (total_mem, kdump_mem, kdump_mem_grubby, self.usable_mem)

        for action in DEFAULTACTIONS:
            self.default_action_combobox.append_text(action)
        self.default_action_combobox.set_active(0)
        self.orig_settings.default_action = DEFAULTACTIONS[0]

        self.set_location(TYPE_DEFAULT, PATH_DEFAULT)
        self.set_path(PATH_DEFAULT)
        self.set_core_collector(CORE_COLLECTOR_DEFAULT)
        self.load_dump_config()

        self.orig_settings.copy_settings(self.my_settings)
        self.check_settings()



    def run(self):
        """
        Show main window and call gtk.main()
        """
        self.toplevel.show_all()
        gtk.main()

    def destroy(self, *args):
        """
        Just quit
        """
        gtk.main_quit()

    def apply_clicked(self, *args):
        """
        When user clicked apply. Do checks. Save settings.
        """
        if self.my_settings.target_type not in (TYPE_RAW, TYPE_LOCAL) and not self.my_settings.path:
            retc = self.yes_no_dialog(_("Path cannot be empty for '%s' locations. "
                                    "Reset path to default ('%s')?."
                                    % (self.my_settings.target_type, PATH_DEFAULT)),
                                   _("system-config-kdump: Empty path"))
            if retc == True:
                self.set_path(PATH_DEFAULT)
            else:
                return

        if self.my_settings.target_type in (TYPE_NFS, TYPE_SSH) and not self.my_settings.server_name:
            self.show_error_message(_("You must specify server. "), _("system-config-kdump: Server name not set"))
            return

        if self.my_settings.target_type in (TYPE_SSH) and not self.my_settings.user_name:
            self.show_error_message(_("You must specify user name. "), _("system-config-kdump: User name not set"))
            return

        if (self.my_settings.target_type == TYPE_RAW) and\
        (self.device_combobox.get_active() < 0):
            self.show_error_message(_("You must select one of the raw devices"), _("system-config-kdump: Raw device error"))
            return

        if (self.my_settings.target_type == TYPE_LOCAL) and\
        (self.partition_combobox.get_active() < 0):
            self.show_error_message(_("You must select one of the partitions"), _("system-config-kdump: Local partition error"))
            return



        kernel_kdump_note = ""
        if self.arch in KERNEL_KDUMP_ARCHES:
            kernel_kdump_note = _("\n\nNote that the %s architecture does not "
                                "feature a relocatable kernel at this time, "
                                "and thus requires a separate kernel-kdump "
                                "package to be installed for kdump to "
                                "function. This can be installed via 'yum "
                                "install kernel-kdump' at your convenience."
                                "\n\n") % self.arch

        if self.xen_kernel and self.my_settings.kdump_enabled:
            self.show_message(_("WARNING: xen kdump support requires a "
                               "non-xen %s RPM to perform actual crash "
                               "dump capture. Please be sure you have "
                               "the non-xen %s RPM of the same version "
                               "as your xen kernel installed.") %
                               (self.xen_kdump_kernel, self.xen_kdump_kernel), _("system-config-kdump: Need non-xen kernel"))

        if self.my_settings.kdump_enabled and self.my_settings.kdump_mem != self.orig_settings.kdump_mem:
            self.show_message(_("Changing Kdump settings requires rebooting "
                               "the system to reallocate memory accordingly. "
                               "%sYou will have to reboot the system for the "
                               "new settings to take effect.")
                               % kernel_kdump_note, _("system-config-kdump: Need reboot"))

        if not TESTING:
            if DEBUG:
                print "writing kdump config"

            if not self.write_dump_config():
                return

            if DEBUG:
                print "writing bootloader config"

            if not self.write_bootloader_config():
                return
            else:
                self.show_message(_("Configurations sucessfully saved"), _("system-config-kdump: Configuration saved"))
                
        else:
            print "would have called write_dump_config"
            print "would have called write_bootloader_config"

        self.my_settings.copy_settings(self.orig_settings)
        self.reset_settings()

    def set_location(self, location_type, path):
        """
        Set location type and path. These two variables are read from kdump.conf
        and are appropriately parsed. Then we save user and server name,
        raw device, path and so on. Look at kdump.conf to more info.
        """
        if DEBUG:
            print "set_location " + location_type  + " " + path

        # SSH or NFS
        if location_type == TYPE_NET:
            self.network_radiobutton.set_active(True)
            if path.find("@") != -1:
                # SSH
                self.ssh_radiobutton.set_active(True)
                (user_name, server_name) = path.split("@")
                self.my_settings.user_name = user_name
                self.my_settings.server_name = server_name
                self.servername_entry.set_text(server_name)
                self.username_entry.set_text(user_name)
            else:
                # NFS
                self.nfs_radiobutton.set_active(True)
                self.my_settings.server_name = path
                self.servername_entry.set_text(path)
            self.nfs_radiobutton.toggled()

        # RAW
        elif location_type == TYPE_RAW:
            if self.set_active_raw_device(path):
                self.raw_device_radiobutton.set_active(True)

        elif location_type == TYPE_LOCAL:
            self.my_settings.path = path

        # One of supported partition type
        else:
            self.set_active_partition(location_type, path)
        self.localfs_radiobutton.toggled()

    def load_dump_config(self):
        """
        Load kdump configuration from /etc/kdump.conf
        """
        self.kdump_config_comments = []
        try:
            lines = open(KDUMP_CONFIG_FILE).readlines()
        except IOError, reason:
            self.show_error_message(_("Error reading kdump configuration: %s" % reason), _("system-config-kdump: kdump configuration file error"))
            return

        for line in [l.strip() for l in lines]:
            if not line:
                continue

            i = line.find("#")
            if i != -1:
                orig_line = line
                line = line[:i].strip()
                if not line:
                    # save comment lines to put in the updated config
                    self.kdump_config_comments.append(orig_line)
                    continue

            try:
                loc_type, location = line.split(' ', 1)
            except ValueError:
                print >> sys.stderr, "Failed to parse line; chucking it..."
                print >> sys.stderr, "  \'%s\'" % (line,)
                continue

            # XXX is case going to be an issue?
            if loc_type == "default":
                self.orig_settings.default_action = location
                self.set_default_action(location)
            elif loc_type == "ifc":
                continue
            elif loc_type == "path":
                self.orig_settings.path = location
                self.set_path(location)
            elif loc_type == "core_collector":
                self.orig_settings.core_collector = location
                idx = location.find("-d")
                if idx != -1:
                    self.orig_settings.filter_level = location[idx:].split(" ")[1]
                self.set_core_collector(location)
            elif loc_type in (TYPE_RAW, TYPE_NET) or loc_type in SUPPORTEDFSTYPES:
                self.orig_settings.set_location(loc_type, location)
                self.set_location(loc_type, location)
            else:
                self.misc_config.append(" ".join((loc_type, location)))
        self.orig_settings.kernel = self.default_kernel
        self.orig_settings.commandline = self.get_cmdline(self.default_kernel)
        self.orig_settings.orig_commandline = self.orig_settings.commandline

    def write_dump_config(self):
        """
        Write settings to /etc/kdump.conf
        """
        if TESTING or not self.my_settings.kdump_enabled:
            return 1

        # start point
        config_string = ""

        # comment lines
        for line in self.kdump_config_comments:
            config_string += "%s\n" % line

        # misc. config
        for line in self.misc_config:
            config_string += "%s\n" % line

        # target type
        #   rawdevice
        if self.my_settings.target_type == TYPE_RAW:
            config_string += "raw %s\n" % self.my_settings.raw_device
            config_string += "path %s\n" % self.my_settings.path

        #   nfs
        elif self.my_settings.target_type == TYPE_NFS:
            config_string += "net %s\n" % self.my_settings.server_name
            config_string += "path %s\n" % self.my_settings.path

        #   scp
        elif self.my_settings.target_type == TYPE_SSH:
            config_string += "net %s@%s\n" % (self.my_settings.user_name, self.my_settings.server_name)
            config_string += "path %s\n" % self.my_settings.path

        #   local
        elif self.my_settings.target_type == TYPE_LOCAL and self.my_settings.local_partition != "":
            (fs_type, partition) = self.my_settings.local_partition.split()
            if fs_type and partition and fs_type != "None":
                config_string += "%s %s\n" % (fs_type, partition)
            config_string += "path %s\n" % self.my_settings.path


        # core collector
        config_string += "core_collector %s\n" % self.my_settings.core_collector

        # default
        if self.my_settings.default_action is not ACTION_DEFAULT:
            config_string += "default %s\n" % self.my_settings.default_action

        written = self.dbus_object.writedumpconfig(config_string)

        if DEBUG:
            print "written kdump config:"
            print written
        if (config_string != written):
            self.show_error_message(_("Error writing kdump configuration: %s" % written), _("system-config-kdump: write kdump configuration file error"))
            return 0
        return 1

    def write_bootloader_config(self):
        """
        Write settings to bootloader config file.
        Return True on succes.
        """
        if TESTING:
            return True

        config_string = ""
        if DEBUG:
            print "Write bootloader conf:"
        
        # kernel name to change
        config_string += " --update-kernel=" + self.my_settings.kernel
        if DEBUG:
            print "  Updating kernel '%s'" % (self.my_settings.kernel)

        # arguments
        if self.my_settings.kdump_enabled:
        # at first remove original kernel cmd line
            config_string += " --remove-args=\"" + self.my_settings.orig_commandline
            if DEBUG:
                print "  Removing original args '%s'" % (self.my_settings.orig_commandline)

            check = self.dbus_object.writebootconfig(config_string)
            if DEBUG:
                print "  check: " + check

        # and now set new kernel cmd line
            config_string = " --update-kernel=" + self.my_settings.kernel
            if DEBUG:
                print "  Updating kernel '%s'" % (self.my_settings.kernel)

            config_string += " --args=\"" + self.my_settings.commandline + "\""
            if DEBUG:
                print "  Setting args to '%s'" % (self.my_settings.commandline)

            check = self.dbus_object.writebootconfig(config_string)
            if DEBUG:
                print "  check: " + check

        else:
        # kdump is desabled, so only remove crashkernel
            config_string += " --remove-args=\"crashkernel=%s\"" % (self.my_settings.kdump_mem)
            if DEBUG:
                print "  Removing crashkernel=%s" % (self.my_settings.kdump_mem)

            check = self.dbus_object.writebootconfig(config_string)
            if DEBUG:
                print "  check: " + check

        return True

    def update_usable_mem(self, spin_button, *args):
        """
        Update Usable mem label whenever you change ammount of kdump mem
        """
        if self.my_settings.kdump_enabled:
            self.my_settings.kdump_mem = int(spin_button.get_value())
            self.usable_mem = self.total_mem - self.my_settings.kdump_mem
            self.usable_mem_label.set_text("%s (MB)" % (self.usable_mem,))
            if DEBUG:
                print "setting usable_mem to", self.usable_mem
            self.set_crashkernel(self.command_line_entry, self.my_settings.kdump_mem)
        else:
            self.my_settings.kdump_mem = 0
        self.check_settings()

    def set_default_action(self, action, *args):
        """
        Select default action in combobox and set it in settings
        """
        if action in DEFAULTACTIONS:
            self.default_action_combobox.set_active(DEFAULTACTIONS.index(action))
            self.my_settings.default_action = action
        else:
            idx = self.default_action_combobox.get_active()
            self.my_settings.default_action = DEFAULTACTIONS[idx]

        if DEBUG:
            print "setting default_action to", self.my_settings.default_action

        self.check_settings()
        return True

    def hex2mb(self, hex_code):
        """
        convert hex memory values into MB of RAM so we can
        read /proc/iomem and show something a human understands
        """
        divisor = 1048575
        return (int(hex_code, 16) / divisor)

    def set_path(self, path):
        """
        Save path where to save crash file. Save it to settings and set
        filechooser button
        """
        if DEBUG:
            print "setting path to '%s'" % path

        if (self.path_entry.get_text() != path):
            self.path_entry.set_text(path)

        if (self.location_entry.get_text() != path):
            self.location_entry.set_text(path)

        if (self.local_filechooser_button.get_filename() != path):
            self.local_filechooser_button.set_current_folder(path)
        self.my_settings.path = path
        self.check_settings()
        return True

    def set_core_collector(self, collector):
        """
        Set core collector with all arguments. Core collector must be makedumpfile.
        """
        if collector and not collector.startswith("makedumpfile"):
            self.show_error_message(_("Core collector must begin with "
                                    "'makedumpfile'"), _("system-config-kdump: Bad core collector"))
            self.set_core_collector(self.orig_settings.core_collector)
            return False

        if DEBUG:
            print "setting core_collector to '%s'" % collector
        if self.core_collector_entry.get_text() != collector:
            self.core_collector_entry.set_text(collector)
            self.collector_entry_changed(self.core_collector_entry)
        self.my_settings.core_collector = collector
        self.check_settings()
        return True

    def kdump_enable_toggled(self, button):
        """
        It's called whenever you click enable or disable.
        Set up sensitive of widgets.
        """
        if (button is self.enable_button) or (button is self.menu_enable):
            self.my_settings.kdump_enabled = 1
        else:
            self.my_settings.kdump_enabled = 0
        if DEBUG:
            print "setting kdump_enabled to", self.my_settings.kdump_enabled

        self.kdump_notebook.set_sensitive(self.my_settings.kdump_enabled)
        if self.my_settings.kdump_enabled:
            self.update_usable_mem(self.kdump_mem_spin_button)
            self.enable_button.set_sensitive(False)
            self.menu_enable.set_sensitive(False)
            self.disable_button.set_sensitive(True)
            self.menu_disable.set_sensitive(True)
            self.target_type_changed(None)
        else:
            self.enable_button.set_sensitive(True)
            self.menu_enable.set_sensitive(True)
            self.disable_button.set_sensitive(False)
            self.menu_disable.set_sensitive(False)
        self.check_settings()

    def show_error_message(self, text, title):
        """
        Show up gtk window with error message.
        Text is message text.
        Title is window title.
        """
        dlg = gtk.MessageDialog(None, 0, gtk.MESSAGE_ERROR, 
                                gtk.BUTTONS_OK, text)
        dlg.set_transient_for(self.toplevel)
        dlg.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        dlg.set_modal(True)
        dlg.set_title(title)
        dlg.run()
        dlg.destroy()
        return False

    def show_message(self, text, title, msgtype=None):
        """
        Show up gtk information message.
        Text is message text.
        Title is window title.
        With msgtype you can override type of gtk MessageDialog
        """
        if msgtype is None:
            msgtype = gtk.MESSAGE_INFO

        dlg = gtk.MessageDialog(None, 0, msgtype, gtk.BUTTONS_OK, text)
        dlg.set_transient_for(self.toplevel)
        dlg.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        dlg.set_modal(True)
        dlg.set_title(title)
        dlg.run()
        dlg.destroy()
           
    def yes_no_dialog(self, text, title):
        """
        Show up gtk message with yes and no buttons.
        Text is message text.
        Title is window title.
        Returns True for Yes clicked, False for No.
        """
        dlg = gtk.MessageDialog(None, 0, gtk.MESSAGE_QUESTION, 
                                gtk.BUTTONS_YES_NO, text)
        dlg.set_transient_for(self.toplevel)
        dlg.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        dlg.set_modal(True)
        dlg.set_title(title)
        ret = dlg.run()
        dlg.destroy()
        if ret == gtk.RESPONSE_YES:
            retc = True
        else:
            retc = False

        return retc

    def target_type_changed(self, button):
        """
        It's callled whenever you choose one of target type.
        Will set target type in settings.
        """
        local = self.localfs_radiobutton.get_active()
        raw = self.raw_device_radiobutton.get_active()
        net = self.network_radiobutton.get_active()

        self.table_localfs.set_sensitive(local)

        self.device_combobox.set_sensitive(raw)

        self.network_type_vbox.set_sensitive(net)
        self.network_config_table.set_sensitive(net)

        if (local):
            self.my_settings.target_type = TYPE_LOCAL
            self.changed_partition(self.partition_combobox)
        elif (raw):
            self.my_settings.target_type = TYPE_RAW
        else: 
            self.nfs_changed(self.nfs_radiobutton)
        self.check_settings()

    def nfs_changed(self, nfs_radio_button):
        """
        It's called whenever you select NFS or SSH.
        """
        if (nfs_radio_button.get_active()):
            self.username_entry.set_sensitive(False)
            self.my_settings.target_type = TYPE_NFS
        else:
            self.username_entry.set_sensitive(True)
            self.my_settings.target_type = TYPE_SSH
        self.check_settings()
            

    def custom_kernel_changed(self, button):
        """
        It's called when you choose from default kernel and custom kernel
        """
        self.custom_kernel_combobox.set_sensitive(self.custom_kernel_radio_button.get_active())
        if not button.get_active():
            self.my_settings.kernel = self.default_kernel
            line = self.get_cmdline(self.default_kernel)
            self.my_settings.commandline = line
            self.my_settings.orig_commandline = line
            self.command_line_entry.set_text(line)
            self.original_command_line_entry.set_text(line)
        else:
            self.update_cmdline(self.custom_kernel_combobox)
        self.update_usable_mem(self.kdump_mem_spin_button)
        self.check_settings()

    def custom_initrd_changed(self, button):
        """
        Called when you choose default or custom initrd
        """
        self.initrd_file_chooser_button.set_sensitive(self.custom_initrd_radio_button.get_active())

    def setup_partitions(self, combobox):
        """
        fill partition combo box with available partitions
        partitions and their types are read from fstab
        """
        try:
            lines = open(FSTAB_FILE).readlines()
            for line in lines:
                for fstype in SUPPORTEDFSTYPES:
                    if line.find(fstype) != -1:
                        self.partitions.append((fstype, line.split(" ")[0]))
                        if DEBUG:
                            print "found partition in fstab: ", self.partitions[len(self.partitions) -1 ] 
        except IOError:
            pass
        for (fs_type, partition) in self.partitions:
            combobox.append_text("%s (%s)" % (partition, fs_type))
        combobox.set_active(0)
        return

    def setup_raw_devices(self, combobox):
        """
        fill raw devices combo box with all partitions listed in /proc/partitions
        uses only valid major numbers
        """
        try:
            lines = open(PROC_PARTITIONS).readlines()
            for line in lines:
                major = line.strip().split(" ")[0]
                if major in SUPPORTED_MAJOR:
                    dev = "/dev/%s" % line.strip().rsplit(" ", 1)[1]
                    self.raw_devices.append(dev)
                    if DEBUG:
                        print "added '%s' to raw devices" % dev
        except IOError:
            pass
        for dev in self.raw_devices:
            combobox.append_text(dev)
        combobox.set_active(0)
        return

    def location_changed(self, widget, *args):
        """
        Called when you change path entry for local file system.
        """
        if widget == self.location_entry:
            self.set_path(widget.get_text())
        else:
            self.set_path(widget.get_filename())

    def get_cmdline(self, kernel):
        """
        Read command line argument for kernel and return them.
        """
        if (kernel.find("/boot/xen.")) is not -1:
            cmdline = self.dbus_object.getxencmdline(kernel)
        else:
            cmdline = self.dbus_object.getcmdline(kernel)
        self.my_settings.kdump_mem = self.get_crashkernel(cmdline)
        return cmdline

    def default_kernel_name(self):
        """
        Read default kernel name from bootloader config and return it.
        Also set up kernel prefix.
        """
        default_kernel = self.dbus_object.getdefaultkernel()
        self.kernel_prefix = default_kernel.rsplit("/", 1)[0]
        if DEBUG:
            print "Default kernel = " + default_kernel
            print "Kernel prefix = " + self.kernel_prefix
        return default_kernel

    def setup_custom_kernel_combobox(self, combobox):
        """
        Fill custom kernel combobox with all kernels found in bootloader config.
        """
        lines = self.dbus_object.getallkernels().split("\n")
        for line in lines[:-1]:
            (name, value) = line.strip().split("=", 1)
            if name == "kernel":
                text = value.strip('"')
                if self.default_kernel.find(text) is not -1:
                    text = text + " " + TAG_DEFAULT
                if text.find(self.running_kernel) is not -1:
                    text = text + " " + TAG_CURRENT
                combobox.append_text(self.kernel_prefix + text)
                if DEBUG:
                    print "Appended kernel:\"" + self.kernel_prefix + text + "\""
        combobox.set_active(0)
        return

    def update_cmdline(self, combobox):
        """
        (Re)Load command line arguments for selected kernel in combobox
        """
        self.my_settings.kernel = combobox.get_active_text()
        self.my_settings.kernel = self.my_settings.kernel.rsplit(TAG_CURRENT, 1)[0] # there can be current or default
        self.my_settings.kernel = self.my_settings.kernel.rsplit(TAG_DEFAULT, 1)[0] # or default tag
        line = self.get_cmdline(self.my_settings.kernel)
        self.original_command_line_entry.set_text(line)
        self.command_line_entry.set_text(line)
        self.my_settings.orig_commandline = line
        self.my_settings.commandline = line
        self.update_usable_mem(self.kdump_mem_spin_button)
        self.check_settings()

    def get_crashkernel(self, text):
        """
        Parse from text `crashkernel='. Return amount (as string) or empty string.
        """
        index = text.find("crashkernel=")
        if index != -1:
            return text[index:].split(" ")[0].split("=")[1]
        return ""

    def set_crashkernel(self, gtk_entry, size):
        """
        Set command line from gtk_entry crashkernel amount to size. 
        """
        old_value = self.get_crashkernel(gtk_entry.get_text())
        old_text = gtk_entry.get_text()
        if old_value == "":
            gtk_entry.set_text(old_text + " crashkernel=%dM" % size)
        else:
            gtk_entry.set_text(old_text.replace(old_value,"%dM" % size))
        self.my_settings.commandline = gtk_entry.get_text()
        self.my_settings.kdump_mem = size

    def cmdline_changed(self, gtk_entry, *args):
        """
        Called when you change command line.
        """
        value = self.get_crashkernel(gtk_entry.get_text())[:-1]
        if value == "":
            self.kdump_enable_toggled(self.disable_button)
        else:
            self.kdump_mem_spin_button.set_value(float(value))
            self.update_usable_mem(self.kdump_mem_spin_button)
        if DEBUG:
            print "Updated cmdline. Crashkernel set to " + value
        self.my_settings.commandline = gtk_entry.get_text()
        self.check_settings()

    def reset_cmdline(self, button):
        """
        Called when you click Refresh button.
        Will set command line entry to default command line entry. 
        """
        self.command_line_entry.set_text(self.original_command_line_entry.get_text())
        self.cmdline_changed(self.command_line_entry)

    def set_active_raw_device(self, device_name):
        """
        Make active raw device to device_name.
        """
        if self.raw_devices.count(device_name) > 0:
            self.device_combobox.set_active(self.raw_devices.index(device_name))
            self.my_settings.raw_device = device_name
            self.check_settings()
            return True
        else:
            self.show_error_message(_("Raw device %s wasn't found on this machine" % device_name), _("system-config-kdump: Raw device error"))
            self.device_combobox.set_active(-1)
            self.my_settings.raw_device = None
            self.check_settings()
            return False

    def set_active_partition(self, part_type, part_name):
        """
        Make active partition part_name which is of part_type type.
        """
        if self.partitions.count((part_type, part_name)) > 0:
            self.partition_combobox.set_active(self.partitions.index((part_type, part_name)))
            self.my_settings.local_partition = "%s %s" % (part_type, part_name)
            if DEBUG:
                print "set_active_partition called: self.my_settings.local_partition = <%s>" % self.my_settings.local_partition
            self.check_settings()
            return True
        else:
            self.show_error_message(_("Local file system partition with name %s and type %s wasn't found") % (part_name, part_type),
                                      _("system-config-kdump: Local partition error"))
            self.partition_combobox.set_active(-1)
            self.my_settings.local_partition = None
            self.check_settings()
            return False

    def collector_entry_changed(self, entry, *args):
        """
        Called when you change collector entry text.
        Will do checks and write to settings, also change filter level.
        """
        if not self.set_core_collector(entry.get_text()):
            entry.set_text(self.my_settings.core_collector)

        # filter level set?
        idx = self.my_settings.core_collector.find("-d")
        if idx != -1:
            try:
                level = int(self.my_settings.core_collector[idx:].split(" ")[1])
            except ValueError:
                level = 0
            self.filter_changed(level)
        else:
            self.filter_changed(0)
        self.check_settings()
        return False

    def set_collector_filter(self, level):
        """
        Change and write to settings filter level, set it to level.
        """
        idx = self.my_settings.core_collector.find("-d")
        if idx != -1:
            value = self.my_settings.core_collector[idx:].split(" ")[1]
            self.set_core_collector(self.my_settings.core_collector.replace(\
                            "-d %s" % value, "-d %d" % level))
        else:
            self.set_core_collector(self.my_settings.core_collector + " -d %d" % level)
        self.check_settings()

    def path_changed(self, entry, *args):
        """
        Called when you change path entry in network target type
        """
        self.my_settings.path = entry.get_text()
        self.check_settings()
        return False

    def username_changed(self, entry, *args):
        """
        Called when you change user name
        """
        self.my_settings.user_name = entry.get_text()
        self.check_settings()
        return False

    def servername_changed(self, entry, *args):
        """
        Called when you change server name
        """
        self.my_settings.server_name = entry.get_text()
        self.check_settings()
        return False

    def set_filter_checkbuttons(self, level):
        """
        Will set filter check buttons active or passive
        by level
        """
        for index in range(NUM_FILTERS-1, -1, -1):
            if level >= (2**index):
                level -= (2**index)
                self.filters[index] = True
                self.filter_check_button[index].set_active(True)
            else:
                self.filters[index] = False
                self.filter_check_button[index].set_active(False)
        self.filter_check_button[0].toggled()
        return

    def filter_changed(self, *args):
        """
        Called when you change filter level by check buttons and/or by collector line.
        """
        level = 0
        if args[0] in self.filter_check_button:
            for x in range(NUM_FILTERS):
                self.filters[x] = self.filter_check_button[x].get_active()
                level += self.filters[x] * (2**x)
            self.set_collector_filter(level)
            self.filter_level_label.set_text("%d" % level)
        else:
            level = args[0]
            self.set_filter_checkbuttons(level)

        self.check_settings()

    def check_settings(self):
        """
        Check original (loaded) and setup settings.
        Set up sensitivities to buttons
        """
        same = self.orig_settings.check_settings(self.my_settings)
        if DEBUG:
            print "Checked settings and is same? %d" % same
        self.menu_apply.set_sensitive(not same)
        self.apply_button.set_sensitive(not same)

    def reset_settings(self, *args):
        """
        Move original settings to my settings. This will revert any changes.
        """
        self.load_dump_config()
        (self.orig_settings.kdump_mem, self.orig_settings.kdump_offset) = self.grubby_crashkernel()
        self.orig_settings.copy_settings(self.my_settings)
        if DEBUG:
            print "Reseting settings. orig kdump_mem = <%s>, my kdump_mem = <%s>" % (self.orig_settings.kdump_mem, self.my_settings.kdump_mem)
        if self.orig_settings.kdump_mem > 0:
            self.kdump_mem_spin_button.set_value(self.orig_settings.kdump_mem)

        if DEBUG:
            print "self.default_kernel: <%s>, self.orig_settings.kernel: <%s>" % (self.default_kernel, self.orig_settings.kernel)
            print "self.my_settings.kernel: <%s>, self.orig_settings.kernel: <%s>" % (self.my_settings.kernel, self.orig_settings.kernel)
        self.default_kernel_radio_button.set_active(self.default_kernel == self.orig_settings.kernel)
        self.custom_kernel_changed(self.custom_kernel_radio_button)
        self.check_settings()
        if self.my_settings.kdump_enabled:
            self.kdump_enable_toggled(self.enable_button)
        else:
            self.kdump_enable_toggled(self.disable_button)

    def changed_partition(self, part_combobox, *args):
        """
        Called when you change local fs in combobox and will save active one into settings
        """
        (partition, fs_type) = part_combobox.get_active_text().split()
        fs_type = fs_type[1:-1]
        if fs_type != "None":
            self.my_settings.local_partition = "%s %s" % (fs_type, partition)
        else:
            self.my_settings.local_partition = ""
        self.check_settings()

    def changed_raw_device(self, raw_dev_box, *args):
        """
        Called when you change raw device in combobox and will save active one into settings
        """
        self.my_settings.raw_device = raw_dev_box.get_active_text()
        self.check_settings()

    def show_about_dialog(self, *args):
        """
        Just show up about dialog
        """
        self.about_dialog.show_all()
        self.about_dialog.run()
        self.about_dialog.hide()

    def grubby_crashkernel(self):
        """
        Read actual crashkernel from bootloader settings for default kernel
        """
        kdump_mem_grubby = 0
        kdump_offset_grubby = 0
        if DEBUG:
            print "grubby --default-kernel: " + self.default_kernel
        line = self.get_cmdline(self.default_kernel)
        if line.find("crashkernel") != -1:
            crash_string = filter(lambda t: t.startswith("crashkernel="),
                                          line.split())[0].split("=")[1]
            tokens = crash_string.split("@")
            kdump_mem_grubby = int(tokens[0][:-1])
            if len(tokens) == 2:
                kdump_offset_grubby = int(tokens[1][:-1])
            if DEBUG:
                print "grubby --info: crashkernel=%iM@%iM" \
                       % (kdump_mem_grubby, kdump_offset_grubby)
        return (kdump_mem_grubby, kdump_offset_grubby)

    def catch_enter(self, widget, event_key, ap_func):
        """
        Filter every key pressed under widget.
        Catch enter, which means to call ap_func.
        """
        if keyval_name(event_key.keyval) in ENTER_CODES:
            ap_func(widget)
            return True
        else:
            return False

    def show_help(self, *args):
        """
        Showup help in yelp
        """
        help_page = "ghelp:system-config-kdump"
        path = "/usr/bin/yelp"

        if not os.access (path, os.X_OK):
            d = gtk.MessageDialog (self.toplevel, 0,
                        gtk.MESSAGE_WARNING, gtk.BUTTONS_CLOSE,
                        _("The help viewer could not be found. To be able to view help, the 'yelp' package needs to be installed."))
            d.set_position (gtk.WIN_POS_CENTER)
            d.run ()
            d.destroy ()
            return

        pid = os.fork ()
        if pid == 0:
            os.execv (path, (path, help_page))


if __name__ == "__main__":
    import getopt

    opt, arg = getopt.getopt(sys.argv[1:], 'dth', ['debug', 'test', 'testing', 'help'])
    for (opt, val) in opt:
        if opt in ("-d", "--debug"):
            print "*** Debug messages enabled. ***"
            DEBUG = 1
        elif opt in ("-t", "--test", "--testing"):
            print "*** Testing only. No configurations will be modified. ***"
            TESTING = 1
        elif opt in ("-h", "--help"):
            print >> sys.stderr, "Usage: system-config-kdump.py [--test] [--debug]"

    win = MainWindow()
    win.setup_screen()
    win.run()


from slip.dbus import polkit
import dbus
import gobject

import gtk
import gettext
DOMAIN = "system-config-kdump"
gtk.glade.bindtextdomain(DOMAIN)
_ = lambda x: gettext.ldgettext(DOMAIN, x)
N_ = lambda x: x

# progress window
from sckdump.progress import ProgressWindow

import dbus.mainloop.glib

# all needed for Python-slip, PoilcyKit and dbus
class DBusProxy (gobject.GObject):
    """
    Class used for communication with/via dbus
    """

    def __init__ (self, progress_window):
        gobject.GObject.__init__(self)
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SystemBus ()
        self.dbus_object = self.bus.get_object (
            "org.fedoraproject.systemconfig.kdump.mechanism",
            "/org/fedoraproject/systemconfig/kdump/object")

        self.progress_window = progress_window

        # What was on stdout
        self.std = ""

        # What was on stderr
        self.err = ""

        # Which command failed
        self.cmd = ""

        # return code
        self.retcode = 0

        gobject.signal_new("proxy-error", self, gobject.SIGNAL_RUN_FIRST,
            gobject.TYPE_NONE,
            (gobject.TYPE_PYOBJECT,))

        self.loop = gobject.MainLoop()

    def handle_reply(self, (cmd, retcode, std, err)):
        self.retcode = retcode
        self.std = std
        self.err = err
        self.cmd = cmd
        self.loop.quit()
        self.progress_window.hide()

    def handle_reply_config(self, (retcode, err)):
        self.retcode = retcode
        self.err = err
        self.loop.quit()
        self.progress_window.hide()

    def handle_error(self, exception):
        self.loop.quit()
        self.progress_window.hide()
        self.emit("proxy-error", exception)
        self.retcode = -1
        self.std = ""
        self.err = ""
        self.cmd = ""

    @polkit.enable_proxy
    def getdefaultkernel (self):
        """
        Return name of default kernel set in bootloader configuration string
        """
        self.progress_window.set_label(_("Getting default kernel name"))
        self.progress_window.show()
        self.dbus_object.getdefaultkernel(
            dbus_interface = "org.fedoraproject.systemconfig.kdump.mechanism",
            reply_handler = self.handle_reply,
            error_handler = self.handle_error)
        self.loop.run()
        return self.cmd, self.retcode, self.std, self.err

    @polkit.enable_proxy
    def getcmdline (self, kernel):
        """
        Return command line arguments for specific kernel
        """
        self.progress_window.set_label(_("Getting argument for kernel"))
        self.progress_window.show()
        self.dbus_object.getcmdline(
            kernel,
            dbus_interface = "org.fedoraproject.systemconfig.kdump.mechanism",
            reply_handler = self.handle_reply,
            error_handler = self.handle_error)
        self.loop.run()
        return self.cmd, self.retcode, self.std, self.err

    @polkit.enable_proxy
    def getxencmdline (self, kernel):
        """
        Return command line arguments for specific xen kernel
        """
        self.progress_window.set_label(_("Getting argument for xen kernel"))
        self.progress_window.show()
        self.dbus_object.getxencmdline(
            kernel,
            dbus_interface = "org.fedoraproject.systemconfig.kdump.mechanism",
            reply_handler = self.handle_reply,
            error_handler = self.handle_error)
        self.loop.run()
        return self.cmd, self.retcode, self.std, self.err

    @polkit.enable_proxy
    def getallkernels (self):
        """
        Return name of all kernels in bootloader configuration files
        separated by newline (\n)
        """
        self.progress_window.set_label(_("Getting name of all kernels"))
        self.progress_window.show()
        self.dbus_object.getallkernels(
            dbus_interface = "org.fedoraproject.systemconfig.kdump.mechanism",
            reply_handler = self.handle_reply,
            error_handler = self.handle_error)
        self.loop.run()
        return self.cmd, self.retcode, self.std, self.err


    @polkit.enable_proxy
    def writedumpconfig (self, config_string):
        """
        Write config_string string to kdump.conf file and returns error code
        and reread string
        """
        self.progress_window.set_label(_("Writing kdump configuration"))
        self.progress_window.show()
        self.dbus_object.writedumpconfig(
            config_string,
            dbus_interface = "org.fedoraproject.systemconfig.kdump.mechanism",
            reply_handler = self.handle_reply_config,
            error_handler = self.handle_error)
        self.loop.run()
        return self.retcode, self.err


    @polkit.enable_proxy
    def writebootconfig (self, config_string):
        """
        Update bootloader configuration. config_string is grubby arguments.
        """
        self.progress_window.set_label(_("Writing bootloader configuration"))
        self.progress_window.show()
        self.dbus_object.writebootconfig(
            config_string,
            dbus_interface = "org.fedoraproject.systemconfig.kdump.mechanism",
            reply_handler = self.handle_reply,
            error_handler = self.handle_error)
        self.loop.run()
        return self.cmd, self.retcode, self.std, self.err


    @polkit.enable_proxy
    def handlekdumpservice(self, chkconfig_status, service_op):
        """
        Start or stop kdump service, turn on or off init script
        """
        self.progress_window.set_label(_("Handling kdump service"))
        self.progress_window.show()
        self.dbus_object.handledumpservice (
            (chkconfig_status, service_op),
            dbus_interface = "org.fedoraproject.systemconfig.kdump.mechanism",
            reply_handler = self.handle_reply,
            error_handler = self.handle_error)
        self.loop.run()
        return self.cmd, self.retcode, self.std, self.err


    @polkit.enable_proxy
    def getservicestatus(self):
        """
        Get the current status of the kdump service
        """
        self.progress_window.set_label(_("Getting status of kdump service"))
        self.progress_window.show()
        self.dbus_object.getservicestatus(
            dbus_interface = "org.fedoraproject.systemconfig.kdump.mechanism",
            reply_handler = self.handle_reply,
            error_handler = self.handle_error)
        self.loop.run()
        return self.cmd, self.retcode, self.std, self.err


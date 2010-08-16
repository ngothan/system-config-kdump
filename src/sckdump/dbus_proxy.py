from slip.dbus import polkit
import dbus

# all needed for Python-slip, PoilcyKit and dbus
class DBusProxy (object):
    """
    Class used for communication with/via dbus
    """

    def __init__ (self):
        self.bus = dbus.SystemBus ()
        self.dbus_object = self.bus.get_object (
            "org.fedoraproject.systemconfig.kdump.mechanism",
            "/org/fedoraproject/systemconfig/kdump/object")

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

    @polkit.enable_proxy
    def handlekdumpservice(self, chkconfig_status, service_op):
        """
        Start or stop kdump service, turn on or off init script
        """
        return self.dbus_object.handledumpservice (
            (chkconfig_status, service_op),
            dbus_interface = "org.fedoraproject.systemconfig.kdump.mechanism")

    @polkit.enable_proxy
    def getservicestatus(self):
        """
        Get the current status of the kdump service
        """
        return self.dbus_object.getservicestatus (
            dbus_interface = "org.fedoraproject.systemconfig.kdump.mechanism")



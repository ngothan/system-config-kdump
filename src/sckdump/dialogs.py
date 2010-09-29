import gtk
import os
import gtk.glade

import gettext
DOMAIN = "system-config-kdump"
gtk.glade.bindtextdomain(DOMAIN)

if os.access("dialog_call_error.glade", os.F_OK):
   _XML = gtk.glade.XML("dialog_call_error.glade", domain = DOMAIN)
else:
   _XML = gtk.glade.XML(
       "/usr/share/system-config-kdump/dialog_call_error.glade",
       domain=DOMAIN)

def show_call_error_message(text, title, cmd, stdout, stderr, parent = None):
    """
    Show up gtk window with error message indicating which command failed.
    text is message text - some talk about the whole problem
    title is window title
    cmd is command which failed
    stdout is standard output from the command
    stderr is standard error from the command
    parrent is parent window
    """
    if cmd == "" and stdout == "" and stderr == "":
        return show_error_message(text, title, parent)
    dlg = _XML.get_widget("dialog_call_error")
    dlg.set_transient_for(parent)
    dlg.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
    dlg.set_modal(True)
    dlg.set_title(title)
    _XML.get_widget("label_message").set_text(text)
    _XML.get_widget("tv_command").get_buffer().set_text(cmd)
    _XML.get_widget("tv_stdout").get_buffer().set_text(stdout)
    _XML.get_widget("tv_stderr").get_buffer().set_text(stderr)
    dlg.run()
    dlg.hide()
    return False

def show_error_message(text, title, parent = None):
    """
    Show up gtk window with error message.
    Text is message text.
    Title is window title.
    """
    dlg = gtk.MessageDialog(None, 0, gtk.MESSAGE_ERROR,
                            gtk.BUTTONS_OK, text)
    dlg.set_transient_for(parent)
    dlg.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
    dlg.set_modal(True)
    dlg.set_title(title)
    dlg.run()
    dlg.destroy()
    return False

def show_message(text, title, msgtype=None, parent = None):
    """
    Show up gtk information message.
    Text is message text.
    Title is window title.
    With msgtype you can override type of gtk MessageDialog
    """
    if msgtype is None:
        msgtype = gtk.MESSAGE_INFO

    dlg = gtk.MessageDialog(None, 0, msgtype, gtk.BUTTONS_OK, text)
    dlg.set_transient_for(parent)
    dlg.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
    dlg.set_modal(True)
    dlg.set_title(title)
    dlg.run()
    dlg.destroy()

def yes_no_dialog(text, title, parent = None):
    """
    Show up gtk message with yes and no buttons.
    Text is message text.
    Title is window title.
    Returns True for Yes clicked, False for No.
    """
    dlg = gtk.MessageDialog(None, 0, gtk.MESSAGE_QUESTION,
                            gtk.BUTTONS_YES_NO, text)
    dlg.set_transient_for(parent)
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

if __name__ == "__main__":
    yes_no_dialog("Yes no dialog test\n"*10, "TEST")
    show_message("Show message test\n"*10, "TEST")
    show_error_message("Show error message test\n"*10, "TEST")
    show_call_error_message("Show call error message test\n"*10,
        "TEST",
        "command test\n"*5,
        "stdout test\n"*5,
        "stderr test\n"*5)
    show_call_error_message("Show call error message test2\n"*10,
        "TEST", "", "", "")
    show_call_error_message("Show call error message test3\n"*10,
        "TEST", "", "a", "")


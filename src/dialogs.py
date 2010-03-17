import gtk

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


import gtk
import gobject

class ProgressWindow(gtk.Window):
    def __init__(self, title, label):
        gtk.Window.__init__(self, gtk.WINDOW_TOPLEVEL)
        self.set_deletable(False)
        self.set_resizable(False)
        self.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        self.set_modal(True)

        self.set_title(title)
        self.progress = gtk.ProgressBar()
        self.progress.show()

        self.label = gtk.Label(label)
        self.label.show()

        vbox = gtk.VBox()
        vbox.set_spacing(10)
        vbox.set_border_width(10)
        vbox.show()

        vbox.pack_start(self.label)
        vbox.pack_start(self.progress)

        self.add(vbox)

    def set_label(self, label):
        self.label.set_text(label)

    def start(self):
        self.timer = gobject.timeout_add(100, self.update_cb)

    def update_cb(self):
        self.progress.pulse()
        self.deiconify()
        return True

    def stop(self):
        if self.timer:
            gobject.source_remove(self.timer)
            self.timer = None

    def show(self):
        self.start()
        gtk.Window.show(self)

    def hide(self):
        self.stop()
        gtk.Window.hide(self)


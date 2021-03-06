import os
import glob

from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets

import ida_kernwin

# Ricky, a PNG sequence player for IDA Pro
__author__ = "patois"

HOTKEY = "Ctrl-Shift-P"

# -------------------------------------------------------------------------
def find_files(folder, wc):
    stuff = os.path.join(folder, wc)
    print("Finding %s" % stuff)
    return glob.glob(stuff)

# -------------------------------------------------------------------------
class png_player_t(QtCore.QObject):
    def __init__(self, title, file_list, interval=200):
        QtCore.QObject.__init__(self)
        self.dead = False        
        w = ida_kernwin.find_widget(title)
        if not w:
            raise RuntimeError("Could not find %s" % title)
        self.target = ida_kernwin.PluginForm.FormToPyQtWidget(w).viewport()
        
        self.title = title
        self.file_list = file_list
        self.interval = interval

        self.painting = False
        self.anim = None
        self._load_img_files(self.file_list)
        self.target.installEventFilter(self)
        self.t = self.timercallback_t(self.target, len(self.anim), interval)

    class timercallback_t(object):
        def __init__(self, target, n_frames, interval=200):
            self.interval = interval

            self.lane = [i for i in range(n_frames)] + [i for i in range(n_frames-1, -1, -1)]
            self.n = len(self.lane)
            self.i = 0
            self.target = target
            self.obj = ida_kernwin.register_timer(self.interval, self)
            if self.obj is None:
                raise RuntimeError("Failed to register timer")

        def get_frame(self):
            return self.lane[self.i]

        def die(self):
            ida_kernwin.unregister_timer(self.obj)

        def __call__(self):
            self.i = (self.i + 1) % self.n
            try:
                self.target.repaint()
            except:
                return -1
            return self.interval

    def _load_img_files(self, files):
        self.anim = []
        i = 1
        ida_kernwin.show_wait_box("HIDECANCEL\nLoading files")
        try:
            for file in files:
                ida_kernwin.replace_wait_box("Loading file %d/%d" % (i, len(files)))
                self.anim.append(QtGui.QPixmap(file))
                i += 1
        except:
            print("Failed loading file %d/%d" % (i, len(files)))
        finally:
            ida_kernwin.hide_wait_box()
        return

    def die(self):
        self.dead = True
        self.t.die()
        self.target.removeEventFilter(self)

    def is_dead(self):
        return self.dead

    def eventFilter(self, receiver, event):
        if not self.painting and \
           self.target == receiver and \
           event.type() == QtCore.QEvent.Paint:

            # Send a paint event that we won't intercept
            self.painting = True
            try:
                pev = QtGui.QPaintEvent(self.target.rect())
                QtWidgets.QApplication.instance().sendEvent(self.target, pev)
            finally:
                self.painting = False

            painter = QtGui.QPainter(receiver)
            painter.setRenderHints(QtGui.QPainter.Antialiasing)
            
            # adjust opacity
            #painter.setOpacity(0.5)

            # feel free to experiment with the various compositionModes
            # ---> https://doc.qt.io/qt-5/qpainter.html#composition-modes
            painter.setCompositionMode(QtGui.QPainter.CompositionMode_SoftLight)
            painter.drawPixmap(self.target.rect(), self.anim[self.t.get_frame()])
            painter.end()
            
            # ...and prevent the widget form painting itself again
            return True

        elif event.type() in [QtCore.QEvent.Close, QtCore.QEvent.Hide]:
            self.die()

        return QtCore.QObject.eventFilter(self, receiver, event)

def pp_main():
    global pp

    if pp and not pp.is_dead():
        pp.die()
        pp = None
        return
    w = ida_kernwin.get_current_widget()        
    title = "IDA View-A"
    if w:
        title = ida_kernwin.get_widget_title(w)
    title = ida_kernwin.ask_str(title, 0, "Please specify title of widget")
    if title:
        path = ida_kernwin.ask_str("", ida_kernwin.HIST_DIR, "Please specify path containing png files to play back")
        if path and os.path.exists(path):
            files = find_files(path, "*.png")
            print("found %d files" % len(files))
            if len(files):
                interval = ida_kernwin.ask_long(100, "Please specify timer interval")
                if interval:
                    pp = png_player_t(title, files, interval=interval)
                    print("PNGs playing in widget %s" % title)

try:
    pp
    ida_kernwin.info("Already installed. Press %s to start/stop playback." % HOTKEY)
except:
    pp = None
    print("Press %s to start/stop playing PNG files" % HOTKEY)
    ida_kernwin.add_hotkey(HOTKEY, pp_main)

import os

from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets

import ida_kernwin
import ida_diskio
from datetime import datetime

# Screen (widget) recorder for IDA Pro
__author__ = "patois"

class screen_record_t(QtCore.QObject):
    def __init__(self, title, path):
        QtCore.QObject.__init__(self)
        self.target = ida_kernwin.PluginForm.FormToPyQtWidget(ida_kernwin.find_widget(title)).viewport()
        self.target.installEventFilter(self)
        self.painting = False
        self.title = title
        self.path = path

    def eventFilter(self, receiver, event):
        if not self.painting and \
           self.target == receiver and \
           event.type() == QtCore.QEvent.Paint:

            # Send a paint event that we won't intercept
            self.painting = True
            try:
                pev = QtGui.QPaintEvent(self.target.rect())
                QtWidgets.QApplication.instance().sendEvent(self.target, pev)
                self.pm = QtGui.QPixmap(self.target.size())
                self.target.render(self.pm)
            finally:
                self.painting = False

            try:
                filename = "%s_%s" % (self.title, datetime.utcnow().strftime("%Y_%m_%d_%H_%M_%S_%f"))
                dst = "%s.png" % (os.path.join(self.path, filename))
                print("Saving %s" % dst)
                self.pm.save(dst, "PNG")
            except:
                print("[!] Error saving file")
        return QtCore.QObject.eventFilter(self, receiver, event)


if __name__ == "__main__":
    try:
        del sr
        print("Stopped recording")
    except:
        title = ida_kernwin.ask_str("IDA View-A", 0, "Please specify title of widget to capture")
        if title:
            path = ida_kernwin.ask_str("", ida_kernwin.HIST_DIR, "Please specify destination path")
            if path and os.path.exists(path):
                sr = screen_record_t(title, path)
                print("Started recording")
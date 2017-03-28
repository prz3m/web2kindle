import sys
import configparser
import os.path as osp

from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMainWindow, QFileDialog, QProgressDialog, QMessageBox
from dialog import Ui_Dialog
from settings import Ui_Settings
from PyQt5.QtCore import QThread
from PyQt5.QtCore import Qt
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5.QtCore import pyqtSignal

from web2kindle import Converter, KindlegenNotFoundError, NothingToConvertError


class ThreadConvert(QThread):
    signal_showMessageBox = pyqtSignal(str)

    def __init__(self, args):
        QThread.__init__(self)
        self.args = args

    def __del__(self):
        self.wait()

    def run(self):
        try:
            c = Converter(*self.args)
            c.convert()
        except NothingToConvertError:
            self.signal_showMessageBox.emit("Nothing to convert!")
        except KindlegenNotFoundError:
            self.signal_showMessageBox.emit("Download kindlegen!")


class Form(QMainWindow, Ui_Dialog):
    def __init__(self):
        super().__init__()

        # Set up the user interface from Designer.
        self.setupUi(self)
        self.setFixedSize(380, 150)
        self.setWindowIcon(QtGui.QIcon(osp.join(osp.dirname(osp.abspath(__file__)),"w2k.ico")))
        self.folder.hide()
        self.go_button.clicked.connect(self.do_stuff)
        self.file.clicked.connect(self.folder.show)
        self.url.clicked.connect(self.folder.hide)

        self.folder.clicked.connect(self.select_folder)

        self.pushButton.clicked.connect(self.open_settings)

        # Init QSystemTrayIcon
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QtGui.QIcon(osp.join(osp.dirname(osp.abspath(__file__)),"w2k.ico")))
        self.t = ThreadConvert(None)

        self.t.finished.connect(self.cleanup_after_stuff)
        self.t.signal_showMessageBox.connect(self.show_messagebox)

        self.tray_icon.show()
        self.tray_icon.activated.connect(self.on_systemTrayIcon_activated)

    def on_systemTrayIcon_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            if self.isHidden():
                self.show()
                self.setWindowState(
                    self.windowState() &
                    ~QtCore.Qt.WindowMinimized | QtCore.Qt.WindowActive)
            else:
                self.hide()

    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.WindowStateChange:
            if self.windowState() & QtCore.Qt.WindowMinimized:
                event.ignore()
                self.hide()
                return
        super().changeEvent(event)

    def select_folder(self):
        file_name = QFileDialog.getOpenFileName(self, 'Select file to convert')
        self.path.setText(file_name[0])

    def do_stuff(self):
        if self.url.isChecked():
            url = self.path.text()
            path = None
        elif self.file.isChecked():
            path = self.path.text()
            url = None
        send = self.send.isChecked()
        clean = self.clean.isChecked()

        self.t.args = url, path, send, clean

        self.t.start()
        self.go_button.setDisabled(True)
        self.progress = QProgressDialog("Sending...", "", 0, 0, self)
        self.progress.setWindowTitle("Sending...")
        self.progress.setCancelButton(None)
        self.progress.setWindowFlags(self.progress.windowFlags() &
                                     ~ Qt.WindowCloseButtonHint &
                                     ~ Qt.WindowContextHelpButtonHint)
        self.path.setText("")
        self.progress.show()

    def cleanup_after_stuff(self):
        self.progress.close()
        self.go_button.setEnabled(True)

    def open_settings(self):
        settings.show()

    def show_messagebox(self, text="Error!"):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)

        msg.setText(text)
        msg.setWindowTitle("Error")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.show()


class Settings(QMainWindow, Ui_Settings):
    def __init__(self):
        super().__init__()

        # Set up the user interface from Designer.
        self.setupUi(self)

        self.load_settings()
        self.pushButton.clicked.connect(self.save_settings)
        self.lineEdit.returnPressed.connect(self.save_settings)
        self.lineEdit_2.returnPressed.connect(self.save_settings)

    def load_settings(self):
        config = configparser.ConfigParser()
        config.read("web2kindle.conf")
        if "web2kindle" in config.keys() and "gmail_login" in config["web2kindle"]:
            login = config["web2kindle"]["gmail_login"]
            self.lineEdit.setText(login)
        if "web2kindle" in config.keys() and "kindle_address" in config["web2kindle"]:
            kindle = config["web2kindle"]["kindle_address"]
            self.lineEdit_2.setText(kindle)

    def save_settings(self):
        config = configparser.ConfigParser()
        config["web2kindle"] = {}
        config["web2kindle"]["gmail_login"] = self.lineEdit.text()
        config["web2kindle"]["kindle_address"] = self.lineEdit_2.text()
        with open("web2kindle.conf", "w") as f:
            config.write(f)
        settings.hide()


app = QApplication(sys.argv)
form = Form()
settings = Settings()

form.show()

sys.exit(app.exec_())

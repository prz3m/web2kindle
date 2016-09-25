import sys
from PyQt5.QtWidgets import QApplication, QDialog, QWidget, QMainWindow, QFileDialog
from mainwindow import Ui_MainWindow
from dialog import Ui_Dialog
from settings import Ui_Settings

from web2kindle import Converter
import configparser


class Form(QMainWindow, Ui_Dialog):
    def __init__(self):
        super().__init__()

        # Set up the user interface from Designer.
        self.setupUi(self)
        self.folder.hide()

        self.go_button.clicked.connect(self.do_stuff)
        self.file.clicked.connect(self.folder.show)
        self.url.clicked.connect(self.folder.hide)

        self.folder.clicked.connect(self.select_folder)

        self.pushButton.clicked.connect(self.open_settings)

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
        c = Converter(url, path, send, clean)
        c.convert()

    def open_settings(self):

        settings.show()


class Settings(QMainWindow, Ui_Settings):
    def __init__(self):
        super().__init__()

        # Set up the user interface from Designer.
        self.setupUi(self)

        self.load_settings()
        self.pushButton.clicked.connect(self.save_settings)

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

# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'dialog.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(381, 151)
        self.formGroupBox = QtWidgets.QGroupBox(Dialog)
        self.formGroupBox.setGeometry(QtCore.QRect(10, 20, 351, 111))
        self.formGroupBox.setToolTip("")
        self.formGroupBox.setAlignment(QtCore.Qt.AlignJustify|QtCore.Qt.AlignVCenter)
        self.formGroupBox.setObjectName("formGroupBox")
        self.formLayout = QtWidgets.QFormLayout(self.formGroupBox)
        self.formLayout.setObjectName("formLayout")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setSizeConstraint(QtWidgets.QLayout.SetMaximumSize)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.url = QtWidgets.QRadioButton(self.formGroupBox)
        self.url.setEnabled(True)
        self.url.setChecked(True)
        self.url.setObjectName("url")
        self.horizontalLayout_2.addWidget(self.url)
        self.file = QtWidgets.QRadioButton(self.formGroupBox)
        self.file.setObjectName("file")
        self.horizontalLayout_2.addWidget(self.file)
        self.formLayout.setLayout(0, QtWidgets.QFormLayout.FieldRole, self.horizontalLayout_2)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setSizeConstraint(QtWidgets.QLayout.SetMaximumSize)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.path = QtWidgets.QLineEdit(self.formGroupBox)
        self.path.setBaseSize(QtCore.QSize(276, 20))
        self.path.setObjectName("path")
        self.horizontalLayout.addWidget(self.path)
        self.folder = QtWidgets.QPushButton(self.formGroupBox)
        self.folder.setObjectName("folder")
        self.horizontalLayout.addWidget(self.folder)
        self.formLayout.setLayout(1, QtWidgets.QFormLayout.FieldRole, self.horizontalLayout)
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setSizeConstraint(QtWidgets.QLayout.SetMaximumSize)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.send = QtWidgets.QCheckBox(self.formGroupBox)
        self.send.setChecked(True)
        self.send.setObjectName("send")
        self.horizontalLayout_3.addWidget(self.send)
        self.clean = QtWidgets.QCheckBox(self.formGroupBox)
        self.clean.setObjectName("clean")
        self.horizontalLayout_3.addWidget(self.clean)
        self.formLayout.setLayout(2, QtWidgets.QFormLayout.FieldRole, self.horizontalLayout_3)
        self.horizontalLayout_5 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        self.pushButton = QtWidgets.QPushButton(self.formGroupBox)
        self.pushButton.setObjectName("pushButton")
        self.horizontalLayout_5.addWidget(self.pushButton)
        self.go_button = QtWidgets.QPushButton(self.formGroupBox)
        self.go_button.setBaseSize(QtCore.QSize(359, 23))
        self.go_button.setObjectName("go_button")
        self.horizontalLayout_5.addWidget(self.go_button)
        self.formLayout.setLayout(3, QtWidgets.QFormLayout.FieldRole, self.horizontalLayout_5)

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "web2kindle"))
        self.url.setText(_translate("Dialog", "url"))
        self.file.setText(_translate("Dialog", "file"))
        self.folder.setText(_translate("Dialog", "..."))
        self.send.setText(_translate("Dialog", "send"))
        self.clean.setText(_translate("Dialog", "clean"))
        self.pushButton.setText(_translate("Dialog", "Settings..."))
        self.go_button.setText(_translate("Dialog", "Go!"))

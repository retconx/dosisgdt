import configparser, os
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialogButtonBox,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLineEdit,
    QMessageBox,
    QLabel, 
    QListWidget,
    QPushButton
)

class VorlagenVerwalten(QDialog):
    def __init__(self, vorlagen, defaultxml):
        super().__init__()
        self.vorlagen = vorlagen
        self.defaultxml = defaultxml

        self.fontNormal = QFont()
        self.fontDurchgestrichen = QFont()
        self.fontDurchgestrichen.setStrikeOut(True)   
        self.fontBold = QFont()
        self.fontBold.setBold(True)

        self.setWindowTitle("Vorlagen verwalten")
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setText("Abbrechen")
        self.buttonBox.accepted.connect(self.accept) # type:ignore
        self.buttonBox.rejected.connect(self.reject) # type:ignore

        dialogLayoutV = QVBoxLayout()
        editButtonsLayoutH = QHBoxLayout()
        labelVorlagen = QLabel("Vorlagen:")
        labelVorlagen.setStyleSheet("font-weight:bold")
        self.listWidgetVorlagen = QListWidget()
        self.listWidgetVorlagen.sortItems()
        i = 0
        for vorlage in self.vorlagen:
            self.listWidgetVorlagen.addItem(vorlage)
            if vorlage + ".dgv" == defaultxml:
                self.listWidgetVorlagen.item(i).setFont(self.fontBold)
            self.listWidgetVorlagen.item(i).setFlags(self.listWidgetVorlagen.item(i).flags() | Qt.ItemFlag.ItemIsEditable)
            i += 1
        self.listWidgetVorlagen.itemSelectionChanged.connect(self.listWidgetSelectionChanged) # type: ignore
        self.listWidgetVorlagen.itemChanged.connect(self.listWidgetVorlagenItemChangeed) # type: ignore
        dialogLayoutV.addWidget(labelVorlagen)
        dialogLayoutV.addWidget(self.listWidgetVorlagen)
        self.pushButtonLoeschen = QPushButton("Entfernen")
        self.pushButtonLoeschen.clicked.connect(self.pushButtonLoeschenClicked) # type: ignore
        self.pushButtonUmbenenen = QPushButton("Umbenennen")
        self.pushButtonUmbenenen.clicked.connect(self.pushButtonUmbenennenClicked) # type: ignore
        self.pushButtonAlsStandard = QPushButton("Als Standard setzen")
        self.pushButtonAlsStandard.clicked.connect(self.pushButtonAlsStandardClicked) # type: ignore
        editButtonsLayoutH.addWidget(self.pushButtonLoeschen)
        editButtonsLayoutH.addWidget(self.pushButtonUmbenenen)
        editButtonsLayoutH.addWidget(self.pushButtonAlsStandard)
        dialogLayoutV.addLayout(editButtonsLayoutH)
        dialogLayoutV.addWidget(self.buttonBox)
        dialogLayoutV.setContentsMargins(10, 10, 10, 10)
        dialogLayoutV.setSpacing(20)
        self.setLayout(dialogLayoutV)
        if len(self.vorlagen) > 0:
            self.listWidgetVorlagen.setCurrentItem(self.listWidgetVorlagen.item(0))
        else: 
            self.pushButtonAlsStandard.setEnabled(False)
            self.pushButtonLoeschen.setEnabled(False)
            self.pushButtonUmbenenen.setEnabled(False)
            self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

    def listWidgetSelectionChanged(self):
        item = self.listWidgetVorlagen.currentItem()
        # Durchgestrichen?
        if item.font() == self.fontDurchgestrichen:
            self.pushButtonLoeschen.setText("Wiederherstellen")
            self.pushButtonUmbenenen.setEnabled(False)
            self.pushButtonAlsStandard.setEnabled(False)
        else:
            self.pushButtonLoeschen.setText("Entfernen")
            self.pushButtonUmbenenen.setEnabled(True)
            self.pushButtonAlsStandard.setEnabled(True)
            if self.listWidgetVorlagen.currentItem().text() == self.defaultxml[0:-4]:
                self.pushButtonAlsStandard.setText("Nicht als Standard setzen")
            else:
                self.pushButtonAlsStandard.setText("Als Standard setzen")
    def listWidgetVorlagenItemChangeed(self, item):
        itemIndex = self.listWidgetVorlagen.indexFromItem(item).row()
        doppelt = False
        for i in range(len(self.vorlagen)):
            if item.text() == self.vorlagen[i] and i != itemIndex:
                doppelt = True
                break
        if doppelt:
            mb = QMessageBox(QMessageBox.Icon.Warning, "Hinweis von DosisGDT", "Die Vorlage " + item.text() + " existiert bereits.", QMessageBox.StandardButton.Ok)
            mb.exec()
            item.setText(self.vorlagen[self.listWidgetVorlagen.indexFromItem(item).row()])
        else:
            self.vorlagen[itemIndex] = item.text()

    def pushButtonLoeschenClicked(self):
        if self.listWidgetVorlagen.currentItem().font().strikeOut() == False:
            self.listWidgetVorlagen.currentItem().setFont(self.fontDurchgestrichen)
            self.pushButtonLoeschen.setText("Wiederherstellen")
            self.pushButtonUmbenenen.setEnabled(False)
            self.pushButtonAlsStandard.setEnabled(False)
            self.pushButtonAlsStandard.setText("Als Standard setzen")
            if self.listWidgetVorlagen.currentItem().text() == self.defaultxml[0:-4]:
                self.defaultxml = ""
        else:
            self.listWidgetVorlagen.currentItem().setFont(self.fontNormal)
            self.pushButtonLoeschen.setText("Entfernen")
            self.pushButtonUmbenenen.setEnabled(True)
            self.pushButtonAlsStandard.setEnabled(True)

    def pushButtonUmbenennenClicked(self):
        self.listWidgetVorlagen.editItem(self.listWidgetVorlagen.currentItem())

    def pushButtonAlsStandardClicked(self):
        if self.pushButtonAlsStandard.text() == "Als Standard setzen":
            self.pushButtonAlsStandard.setText("Nicht als Standard setzen")
            self.defaultxml = self.listWidgetVorlagen.currentItem().text() + ".dgv"
            for i in range(self.listWidgetVorlagen.count()):
                self.listWidgetVorlagen.item(i).setFont(self.fontNormal)
            self.listWidgetVorlagen.currentItem().setFont(self.fontBold)
        else:
            self.pushButtonAlsStandard.setText("Als Standard setzen")
            self.defaultxml = ""
            self.listWidgetVorlagen.currentItem().setFont(self.fontNormal)
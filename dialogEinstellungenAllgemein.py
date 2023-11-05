import configparser, os, gdttoolsL, re
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import (
    QDialogButtonBox,
    QDialog,
    QVBoxLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QCheckBox,
    QFileDialog,
    QMessageBox
)

class EinstellungenAllgemein(QDialog):
    def __init__(self, configPath):
        super().__init__()

        #config.ini lesen
        configIni = configparser.ConfigParser()
        configIni.read(os.path.join(configPath, "config.ini"))
        self.version = configIni["Allgemein"]["version"]
        self.releasedatum = configIni["Allgemein"]["releasedatum"]
        self.einrichtungsname = configIni["Allgemein"]["einrichtungsname"]
        self.pdfErstellen = configIni["Allgemein"]["pdferstellen"] == "1"
        self.pdfbezeichnung = configIni["Allgemein"]["pdfbezeichnung"] 
        self.einrichtungAufPdf = configIni["Allgemein"]["einrichtungaufpdf"] == "1"

        self.setWindowTitle("Allgemeine Einstellungen")
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setText("Abbrechen")
        self.buttonBox.accepted.connect(self.accept) # type: ignore
        self.buttonBox.rejected.connect(self.reject) # type: ignore

        # Prüfen, ob Lizenzschlüssel verschlüsselt in config.ini
        lizenzschluessel = configIni["Erweiterungen"]["lizenzschluessel"]
        if len(lizenzschluessel) != 29:
            lizenzschluessel = gdttoolsL.GdtToolsLizenzschluessel.dekrypt(lizenzschluessel)

        dialogLayoutV = QVBoxLayout()
        # Groupox Name der Einrichtung
        groupboxEinrichtung = QGroupBox("Name der Einrichtung")
        groupboxEinrichtung.setStyleSheet("font-weight:bold")
        self.lineEditEinrichtungsname = QLineEdit(self.einrichtungsname)
        self.lineEditEinrichtungsname.setPlaceholderText("Hausarztpraxis XY")
        self.lineEditEinrichtungsname.setStyleSheet("font-weight:normal")
        groupboxLayoutEinrichtung = QVBoxLayout()
        groupboxLayoutEinrichtung.addWidget(self.lineEditEinrichtungsname)
        groupboxEinrichtung.setLayout(groupboxLayoutEinrichtung)

        # Groupbox PDF-Erstellung
        groupboxPdfErstellung = QGroupBox("PDF-Erstellung")
        groupboxPdfErstellung.setStyleSheet("font-weight:bold")
        labelKeineRegistrierung = QLabel("Für diese Funktion ist eine gültige LANR/Lizenzschlüsselkombination erforderlich.")
        labelKeineRegistrierung.setStyleSheet("font-weight:normal;color:rgb(0,0,200)")
        labelKeineRegistrierung.setVisible(False)
        labelPdfErstellen = QLabel("PDF erstellen und per GDT übertragen")
        labelPdfErstellen.setStyleSheet("font-weight:normal")
        self.checkboxPdfErstellen = QCheckBox()
        self.checkboxPdfErstellen.setChecked(self.pdfErstellen)
        self.checkboxPdfErstellen.stateChanged.connect(self.checkboxPdfErstellenChanged) # type: ignore
        labelEinrichtungAufPdf = QLabel("Einrichtungsname übernehmen")
        labelEinrichtungAufPdf.setStyleSheet("font-weight:normal")
        self.checkboxEinrichtungAufPdf = QCheckBox()
        self.checkboxEinrichtungAufPdf.setChecked(self.einrichtungAufPdf)
        self.checkboxEinrichtungAufPdf.stateChanged.connect(self.checkboxEinrichtungAufPdfChanged) # type: ignore
        labelPdfBezeichnung = QLabel("PDF-Bezeichnung in Karteikarte:")
        labelPdfBezeichnung.setStyleSheet("font-weight:normal")
        self.lineEditPdfBezeichnung = QLineEdit(self.pdfbezeichnung)
        self.lineEditPdfBezeichnung.setStyleSheet("font-weight:normal")
        self.lineEditPdfBezeichnung.setPlaceholderText("Dosierungsplan")
        # PDF-Erstellung daktivieren, falls nicht lizensiert
        if not gdttoolsL.GdtToolsLizenzschluessel.lizenzErteilt(lizenzschluessel, configIni["Erweiterungen"]["lanr"], gdttoolsL.SoftwareId.DOSISGDT):
            labelKeineRegistrierung.setVisible(True)
            self.checkboxPdfErstellen.setEnabled(False)
            self.checkboxPdfErstellen.setChecked(False)
            self.lineEditPdfBezeichnung.setText("")
            self.checkboxEinrichtungAufPdf.setEnabled(False)
            self.checkboxEinrichtungAufPdf.setChecked(False)

        groupboxLayoutPdfErstellung = QGridLayout()
        groupboxLayoutPdfErstellung.addWidget(labelKeineRegistrierung, 0, 0, 1, 2)
        groupboxLayoutPdfErstellung.addWidget(labelPdfErstellen, 1, 0)
        groupboxLayoutPdfErstellung.addWidget(self.checkboxPdfErstellen, 1, 1)
        groupboxLayoutPdfErstellung.addWidget(labelEinrichtungAufPdf, 3, 0)
        groupboxLayoutPdfErstellung.addWidget(self.checkboxEinrichtungAufPdf, 3, 1)
        groupboxPdfErstellung.setLayout(groupboxLayoutPdfErstellung)
        groupboxLayoutPdfErstellung.addWidget(labelPdfBezeichnung, 4, 0)
        groupboxLayoutPdfErstellung.addWidget(self.lineEditPdfBezeichnung, 5, 0)

        dialogLayoutV.addWidget(groupboxEinrichtung)
        dialogLayoutV.addWidget(groupboxPdfErstellung)
        dialogLayoutV.addWidget(self.buttonBox)
        dialogLayoutV.setContentsMargins(10, 10, 10, 10)
        dialogLayoutV.setSpacing(20)
        self.setLayout(dialogLayoutV)

    def checkboxPdfErstellenChanged(self, newState):
        if not newState:
            self.lineEditPdfBezeichnung.setText("")
            self.checkboxEinrichtungAufPdf.setChecked(False)

    def checkboxEinrichtungAufPdfChanged(self, newState):
        if newState:
            self.checkboxPdfErstellen.setChecked(True)

    def accept(self):
        regexPattern = "[/.,]"
        test = re.search(regexPattern, self.lineEditPdfBezeichnung.text())
        if test != None:
            mb = QMessageBox(QMessageBox.Icon.Information, "Hinweis von DosisGDT", "Die PDF-Bezeichnung enthält unerlaubte Zeichen (" + regexPattern[1:-1] + ")", QMessageBox.StandardButton.Ok)
            mb.exec()
            self.lineEditPdfBezeichnung.setFocus()
            self.lineEditPdfBezeichnung.selectAll()
        else:
            if self.lineEditPdfBezeichnung.text() == "":
                self.lineEditPdfBezeichnung.setText(self.lineEditPdfBezeichnung.placeholderText())
            if self.lineEditEinrichtungsname.text() == "":
                self.lineEditEinrichtungsname.setText(self.lineEditEinrichtungsname.placeholderText())
            self.done(1)
import sys, configparser, os, datetime, shutil,logger, re
import gdt, gdtzeile, gdttoolsL
import xml.etree.ElementTree as ElementTree
from fpdf import FPDF, enums
import class_medikament, class_dosierungsplan, dialogUeberDosisGdt, dialogEinstellungenGdt, dialogEinstellungenAllgemein, dialogEinstellungenLanrLizenzschluessel, dialogEinstellungenImportExport, dialogVorlagenVerwalten, dialogEula
from PySide6.QtCore import Qt, QSize, QDate, QTranslator, QLibraryInfo
from PySide6.QtGui import QFont, QAction, QKeySequence, QIcon, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QGroupBox,
    QPushButton,
    QHBoxLayout,
    QGridLayout,
    QRadioButton,
    QButtonGroup,
    QWidget,
    QLabel, 
    QLineEdit,
    QDateEdit,
    QComboBox,
    QMessageBox,
    QTextEdit,
    QStatusBar,
    QFileDialog
)
import requests

basedir = os.path.dirname(__file__)

# Gegebenenfalls pdf- und log-Verzeichnisse anlegen
if not os.path.exists(os.path.join(basedir, "pdf")):
    os.mkdir(os.path.join(basedir, "pdf"), 0o777)
if not os.path.exists(os.path.join(basedir, "log")):
    os.mkdir(os.path.join(basedir, "log"), 0o777)
    logDateinummer = 0
else:
    logListe = os.listdir(os.path.join(basedir, "log"))
    logListe.sort()
    if len(logListe) > 5:
        os.remove(os.path.join(basedir, "log/" + logListe[0]))
datum = datetime.datetime.strftime(datetime.datetime.today(), "%Y%m%d")

def versionVeraltet(versionAktuell:str, versionVergleich:str):
    """
    Vergleicht zwei Versionen im Format x.x.x
    Parameter:
        versionAktuell:str
        versionVergleich:str
    Rückgabe:
        True, wenn versionAktuell veraltet
    """
    versionVeraltet= False
    hunderterBase = int(versionVergleich.split(".")[0])
    zehnerBase = int(versionVergleich.split(".")[1])
    einserBase = int(versionVergleich.split(".")[2])
    hunderter = int(versionAktuell.split(".")[0])
    zehner = int(versionAktuell.split(".")[1])
    einser = int(versionAktuell.split(".")[2])
    if hunderterBase > hunderter:
        versionVeraltet = True
    elif hunderterBase == hunderter:
        if zehnerBase >zehner:
            versionVeraltet = True
        elif zehnerBase == zehner:
            if einserBase > einser:
                versionVeraltet = True
    return versionVeraltet

# Sicherstellen, dass Icon in Windows angezeigt wird
try:
    from ctypes import windll # type: ignore
    mayappid = "gdttools.dosisgdt"
    windll.shell32.SetCurrentProcessExplicitAppUserModelID(mayappid)
except ImportError:
    pass

class MainWindow(QMainWindow):
    # Mainwindow zentrieren
    def resizeEvent(self, e):
        mainwindowBreite = e.size().width()
        mainwindowHoehe = e.size().height()
        ag = self.screen().availableGeometry()
        screenBreite = ag.size().width()
        screenHoehe = ag.size().height()
        left = screenBreite / 2 - mainwindowBreite / 2
        top = screenHoehe / 2 - mainwindowHoehe / 2
        self.setGeometry(left, top, mainwindowBreite, mainwindowHoehe)
    
    def setPreFormularXml(self, xmlDateipdad:str):
        try:
            self.setCursor(Qt.CursorShape.WaitCursor)
            baum = ElementTree.parse(xmlDateipdad)
            dosierungsplanElement = baum.getroot()
            medikamentElement = dosierungsplanElement.find("medikament")
            medikamentenname = str(medikamentElement.findtext("name")) # type: ignore
            einheit = class_medikament.Einheit(str(medikamentElement.findtext("einheit"))) # type: ignore
            darreichungsform = class_medikament.Darreichungsform(medikamentElement.find("darreichungsform").text) # type: ignore
            elementDosenproEinheit = medikamentElement.find("dosenProEinheit") # type: ignore
            dosenProEinheit = []
            for elementDosisProEinheit in elementDosenproEinheit.findall("dosis"): # type: ignore
                dosenProEinheit.append(float(str(elementDosisProEinheit.text)))
            elementTeilbarkeiten = medikamentElement.find("teilbarkeiten") # type: ignore
            teilbarkeiten = []
            for elementTeilbarkeit in elementTeilbarkeiten.findall("teilbarkeit"): # type: ignore
                teilbarkeiten.append(class_medikament.Teilbarkeit(elementTeilbarkeit.text))
            startdosis = float(str(dosierungsplanElement.findtext("startdosis")))
            startdauer = int(str(dosierungsplanElement.findtext("startdauer")))
            aenderungenElement = dosierungsplanElement.find("aenderungen")
            reduktionUm = []
            tage = []
            bis = []
            for aenderungElement in aenderungenElement.findall("aenderung"): # type: ignore
                reduktionUm.append(float(str(aenderungElement.findtext("reduktionUm"))))
                tage.append(int(str(aenderungElement.findtext("tage"))))
                bis.append(float(str(aenderungElement.findtext("bis"))))
            maxTablettenzahl = int(str(dosierungsplanElement.findtext("maxTablettenzahl")))
            medikament = class_medikament.Medikament(medikamentenname, einheit, darreichungsform, dosenProEinheit, teilbarkeiten)

            self.lineEditMediName.setText(medikament.name)
            self.comboBoxMediEinheit.setCurrentText(medikament.einheit.value)
            self.comboBoxMediDarreichungsform.setCurrentText(medikament.darreichungsform.value)
            for i in range(len(medikament.dosenProEinheit)):
                self.lineEditDosisProEinheit[i].setText(str(medikament.dosenProEinheit[i]))
            for i in range(len(medikament.teilbarkeiten)):
                self.comboBoxDosisTeilbarkeit[i].setCurrentText(medikament.teilbarkeiten[i].value)
            self.lineEditStartdosis.setText(str(startdosis))
            self.lineEditStartTage.setText(str(startdauer))
            for i in range(len(reduktionUm)):
                self.lineEditReduktionUm[i].setText(str(reduktionUm[i]))
                self.lineEditTage[i].setText(str(tage[i]))
                self.lineEditBis[i].setText(str(bis[i]))
            self.lineEditMaximaleTablettenzahl.setText(str(maxTablettenzahl))
            self.setStatusMessage("Vorlage " + os.path.basename(xmlDateipdad) + " geladen")
            logger.logger.info("Eingabeformular vor-ausgefüllt")
            self.setCursor(Qt.CursorShape.ArrowCursor)
        except Exception as e:
            mb = QMessageBox(QMessageBox.Icon.Warning, "Hinweis von DosisGDT", "Fehler beim Laden der Vorlage (" + xmlDateipdad + "): " + e.args[1], QMessageBox.StandardButton.Ok)
            mb.exec()

    def __init__(self):
        super().__init__()

        # config.ini lesen
        ersterStart = False
        updateSafePath = ""
        if sys.platform == "win32":
            logger.logger.info("Plattform: win32")
            updateSafePath = os.path.expanduser("~\\appdata\\local\\dosisgdt")
        else:
            logger.logger.info("Plattform: nicht win32")
            updateSafePath = os.path.expanduser("~/.config/dosisgdt")
        self.configPath = updateSafePath
        self.configIni = configparser.ConfigParser()
        if os.path.exists(os.path.join(updateSafePath, "config.ini")):
            logger.logger.info("config.ini in " + updateSafePath + " exisitert")
            self.configPath = updateSafePath
        elif os.path.exists(os.path.join(basedir, "config.ini")):
            logger.logger.info("config.ini in " + updateSafePath + " exisitert nicht")
            try:
                if not os.path.exists(updateSafePath):
                    logger.logger.info(updateSafePath + " exisitert nicht")
                    os.makedirs(updateSafePath, 0o777)
                    logger.logger.info(updateSafePath + "erzeugt")
                shutil.copy(os.path.join(basedir, "config.ini"), updateSafePath)
                logger.logger.info("config.ini von " + basedir + " nach " + updateSafePath + " kopiert")
                self.configPath = updateSafePath
                ersterStart = True
            except:
                logger.logger.error("Problem beim Kopieren der config.ini von " + basedir + " nach " + updateSafePath)
                mb = QMessageBox(QMessageBox.Icon.Warning, "Hinweis von DosisGDT", "Problem beim Kopieren der Konfigurationsdatei. DosisGDT wird mit Standardeinstellungen gestartet.", QMessageBox.StandardButton.Ok)
                mb.exec()
                self.configPath = basedir
        else:
            logger.logger.critical("config.ini fehlt")
            mb = QMessageBox(QMessageBox.Icon.Critical, "Hinweis von DosisGDT", "Die Konfigurationsdatei config.ini fehlt. DosisGDT kann nicht gestartet werden.", QMessageBox.StandardButton.Ok)
            mb.exec()
            sys.exit()

        self.configIni.read(os.path.join(self.configPath, "config.ini"))
        self.gdtImportVerzeichnis = self.configIni["GDT"]["gdtimportverzeichnis"]
        self.gdtExportVerzeichnis = self.configIni["GDT"]["gdtexportverzeichnis"]
        self.kuerzeldosisgdt = self.configIni["GDT"]["kuerzeldosisgdt"]
        self.kuerzelpraxisedv = self.configIni["GDT"]["kuerzelpraxisedv"]
        self.version = self.configIni["Allgemein"]["version"]
        self.defaultXml = self.configIni["Allgemein"]["defaultxml"]

        # Nachträglich hinzufefügte Options
        # 1.1.0
        self.vorlagen = []
        if self.configIni.has_option("Allgemein", "vorlagenverzeichnis"):
            self.vorlagenverzeichnis = self.configIni["Allgemein"]["vorlagenverzeichnis"]
            if self.vorlagenverzeichnis != "" and os.path.exists(self.vorlagenverzeichnis):
                for vorlage in os.listdir(self.vorlagenverzeichnis):
                    if vorlage[-4:] == ".dgv":
                        self.vorlagen.append(vorlage[0:-4])
                self.vorlagen.sort()
            elif self.vorlagenverzeichnis != "":
                mb = QMessageBox(QMessageBox.Icon.Warning, "Hinweis von DosisGDT", "Das Vorlagenverzeichnis " + self.vorlagenverzeichnis + " existiert nicht.", QMessageBox.StandardButton.Ok)
                mb.exec()
        # 1.1.5
        self.eulagelesen = False
        if self.configIni.has_option("Allgemein", "eulagelesen"):
            self.eulagelesen = self.configIni["Allgemein"]["eulagelesen"] == "True"
        # /Nachträglich hinzufefügte Options

        z = self.configIni["GDT"]["zeichensatz"]
        self.zeichensatz = gdt.GdtZeichensatz.IBM_CP437
        if z == "1":
            self.zeichensatz = gdt.GdtZeichensatz.BIT_7
        elif z == "3":
            self.zeichensatz = gdt.GdtZeichensatz.ANSI_CP1252
        self.lanr = self.configIni["Erweiterungen"]["lanr"]
        self.lizenzschluessel = self.configIni["Erweiterungen"]["lizenzschluessel"]

        # Prüfen, ob Lizenzschlüssel unverschlüsselt
        if len(self.lizenzschluessel) == 29:
            logger.logger.info("Lizenzschlüssel unverschlüsselt")
            self.configIni["Erweiterungen"]["lizenzschluessel"] = gdttoolsL.GdtToolsLizenzschluessel.krypt(self.lizenzschluessel)
            with open(os.path.join(self.configPath, "config.ini"), "w") as configfile:
                    self.configIni.write(configfile)
        else:
            self.lizenzschluessel = gdttoolsL.GdtToolsLizenzschluessel.dekrypt(self.lizenzschluessel)

        # Prüfen, ob EULA gelesen
        if not self.eulagelesen:
            de = dialogEula.Eula()
            de.exec()
            if de.checkBoxZustimmung.isChecked():
                self.eulagelesen = True
                self.configIni["Allgemein"]["eulagelesen"] = "True"
                with open(os.path.join(self.configPath, "config.ini"), "w") as configfile:
                    self.configIni.write(configfile)
                logger.logger.info("EULA zugestimmt")
            else:
                mb = QMessageBox(QMessageBox.Icon.Information, "Hinweis von DosisGDT", "Ohne Zustimmung der Lizenzvereinbarung kann DosisGDT nicht gestartet werden.", QMessageBox.StandardButton.Ok)
                mb.exec()
                sys.exit()

        # Grundeinstellungen bei erstem Start
        if ersterStart:
            logger.logger.info("Erster Start")
            mb = QMessageBox(QMessageBox.Icon.Question, "Hinweis von DosisGDT", "Vermutlich starten Sie DosisGDT das erste Mal auf diesem PC.\nMöchten Sie jetzt die Grundeinstellungen vornehmen?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            mb.setDefaultButton(QMessageBox.StandardButton.Yes)
            if mb.exec() == QMessageBox.StandardButton.Yes:
                self.einstellungenLanrLizenzschluessel()
                self.einstellungenGdt()
                self.einstellungenAllgemein(True)

        # Version vergleichen und gegebenenfalls aktualisieren
        configIniBase = configparser.ConfigParser()
        try:
            configIniBase.read(os.path.join(basedir, "config.ini"))
            if versionVeraltet(self.version, configIniBase["Allgemein"]["version"]):
                # Version aktualisieren
                self.configIni["Allgemein"]["version"] = configIniBase["Allgemein"]["version"]
                self.configIni["Allgemein"]["releasedatum"] = configIniBase["Allgemein"]["releasedatum"] 
                # config.ini aktualisieren
                # 1.0.3 -> 1.1.0: ["Allgemein"]["vorlagenverzeichnis"] hinzufügen
                if not self.configIni.has_option("Allgemein", "vorlagenverzeichnis"):
                    self.configIni["Allgemein"]["vorlagenverzeichnis"] = ""
                    self.vorlagenverzeichnis = ""
                # /config.ini aktualisieren

                with open(os.path.join(self.configPath, "config.ini"), "w") as configfile:
                    self.configIni.write(configfile)
                self.version = self.configIni["Allgemein"]["version"]
                logger.logger.info("Version auf " + self.version + " aktualisiert")
                # Prüfen, ob EULA gelesen
                de = dialogEula.Eula(self.version)
                de.exec()
                self.eulagelesen = de.checkBoxZustimmung.isChecked()
                self.configIni["Allgemein"]["eulagelesen"] = str(self.eulagelesen)
                with open(os.path.join(self.configPath, "config.ini"), "w") as configfile:
                    self.configIni.write(configfile)
                if self.eulagelesen:
                    logger.logger.info("EULA zugestimmt")
                else:
                    logger.logger.info("EULA nicht zugestimmt")
                    mb = QMessageBox(QMessageBox.Icon.Information, "Hinweis von DosisGDT", "Ohne  Zustimmung zur Lizenzvereinbarung kann DosisGDT nicht gestartet werden.", QMessageBox.StandardButton.Ok)
                    mb.exec()
                    sys.exit()
        except SystemExit:
            sys.exit()
        except:
            logger.logger.error("Problem beim Aktualisieren auf Version " + configIniBase["Allgemein"]["version"])
            mb = QMessageBox(QMessageBox.Icon.Warning, "Hinweis von DosisGDT", "Problem beim Aktualisieren auf Version " + configIniBase["Allgemein"]["version"], QMessageBox.StandardButton.Ok)
            mb.exec()

        # Pseudo-Lizenz?
        self.pseudoLizenzId = ""
        rePatId = r"^patid\d+$"
        for arg in sys.argv:
            if re.match(rePatId, arg) != None:
                logger.logger.info("Pseudo-Lizenz mit id " + arg[5:])
                self.pseudoLizenzId = arg[5:]

        # Add-Ons freigeschaltet?
        self.addOnsFreigeschaltet = gdttoolsL.GdtToolsLizenzschluessel.lizenzErteilt(self.lizenzschluessel, self.lanr, gdttoolsL.SoftwareId.DOSISGDT) or gdttoolsL.GdtToolsLizenzschluessel.lizenzErteilt(self.lizenzschluessel, self.lanr, gdttoolsL.SoftwareId.DOSISGDTPSEUDO) and self.pseudoLizenzId != ""
        if self.lizenzschluessel != "" and gdttoolsL.GdtToolsLizenzschluessel.getSoftwareId(self.lizenzschluessel) == gdttoolsL.SoftwareId.DOSISGDTPSEUDO and self.pseudoLizenzId == "":
            mb = QMessageBox(QMessageBox.Icon.Warning, "Hinweis von DosisGDT", "Bei Verwendung einer Pseudolizenz muss DosisGDT mit einer Patienten-Id als Startargument im Format \"patid<Pat.-Id>\" ausgeführt werden.", QMessageBox.StandardButton.Ok)
            mb.exec() 
        
        jahr = datetime.datetime.now().year
        copyrightJahre = "2023"
        if jahr > 2023:
            copyrightJahre = "2023-" + str(jahr)
        self.setWindowTitle("DosisGDT V" + self.version + " (\u00a9 Fabian Treusch - GDT-Tools " + copyrightJahre + ")")
        self.fontNormal = QFont()
        self.fontNormal.setBold(False)
        self.fontBold = QFont()
        self.fontBold.setBold(True)
        self.fontKlein = QFont()
        self.fontKlein.setPixelSize(10)
        self.planBeginnInVergangenheit = False

        # GDT-Datei laden
        gd = gdt.GdtDatei()
        self.patId = "-"
        self.vorname = "-"
        self.nachname = "-"
        self.gebdat = "-"
        mbErg = QMessageBox.StandardButton.Yes
        try:
            # Prüfen, ob PVS-GDT-ID eingetragen
            senderId = self.configIni["GDT"]["idpraxisedv"]
            if senderId == "":
                senderId = None
            gd.laden(self.gdtImportVerzeichnis + "/" + self.kuerzeldosisgdt + self.kuerzelpraxisedv + ".gdt", self.zeichensatz, senderId)
            self.patId = str(gd.getInhalt("3000"))
            self.vorname = str(gd.getInhalt("3102"))
            self.nachname = str(gd.getInhalt("3101"))
            gd = str(gd.getInhalt("3103"))
            self.gebdat = gd[0:2] + "." + gd[2:4] + "." + gd[4:8]
            logger.logger.info("PatientIn " + self.vorname + " " + self.nachname + " (ID: " + self.patId + ") geladen")
            if self.pseudoLizenzId != "":
                self.patid = self.pseudoLizenzId
                logger.logger.info("PatId wegen Pseudolizenz auf " + self.pseudoLizenzId + " gesetzt")
        except (IOError, gdtzeile.GdtFehlerException) as e:
            logger.logger.warning("Fehler beim Laden der GDT-Datei: " + str(e))
            mb = QMessageBox(QMessageBox.Icon.Information, "Hinweis von DosisGDT", "Fehler beim Laden der GDT-Datei:\n" + str(e) + "\n\nSoll DosisGDT dennoch geöffnet werden?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            mb.button(QMessageBox.StandardButton.Yes).setText("Ja")
            mb.button(QMessageBox.StandardButton.No).setText("Nein")
            mb.setDefaultButton(QMessageBox.StandardButton.No)
            mbErg = mb.exec()
        if mbErg == QMessageBox.StandardButton.Yes:
            self.widget = QWidget()
            mainLayoutV = QVBoxLayout()
            self.labelPseudolizenz = QLabel("+++ Pseudolizenz für Test-/ Präsentationszwecke +++")
            self.labelPseudolizenz.setStyleSheet("color:rgb(200,0,0);font-style:italic")
            mainSpaltenlayout = QHBoxLayout()
            mainLayoutLinkeSpalte = QVBoxLayout()
            mainLayoutRechteSpalte = QVBoxLayout()
            self.lineEditBreiteKlein = 50
            self.maxDosenProEinheit = 4
            self.maxDosierungsplanAnweisungen = 5
            self.styleSheetHellrot = "background:rgb(255,200,200)"
            self.styleSheetWeiss = "background:rgb(255,255,255)"
            self.patternDosis = r"^\d+([.,]\d+)*$"
            self.patternTage = r"\d+$"
            self.preMedikament = None
            
            # Groupbox Medikament
            medikamentLayout = QGridLayout()
            groupBoxMedikament = QGroupBox("Medikament")
            groupBoxMedikament.setFont(self.fontBold)
            labelMediName = QLabel("Name")
            labelMediName.setFont(self.fontNormal)
            labelMediEinheit = QLabel("Einheit")
            labelMediEinheit.setFont(self.fontNormal)
            labelMediDarreichungsform = QLabel("Darreichungsform")
            labelMediDarreichungsform.setFont(self.fontNormal)
            self.lineEditMediName = QLineEdit()
            self.lineEditMediName.setFont(self.fontNormal)
            self.lineEditMediName.setStyleSheet(self.styleSheetHellrot)
            self.lineEditMediName.textChanged.connect(self.lineEditMediNameTextChanged) # type: ignore
            self.comboBoxMediEinheit = QComboBox()
            self.comboBoxMediEinheit.setFont(self.fontNormal)
            self.comboBoxMediEinheit.addItems(["mg", "µg", "g"])
            self.comboBoxMediEinheit.currentIndexChanged.connect(self.comboBoxMediEinheitIndexChanged) # type: ignore
            self.comboBoxMediDarreichungsform = QComboBox()
            self.comboBoxMediDarreichungsform.setFont(self.fontNormal)
            self.comboBoxMediDarreichungsform.addItems(["Tablette", "Tropfen"])
            self.comboBoxMediDarreichungsform.currentIndexChanged.connect(self.comboBoxMediDarreichungsformIndexChanged) # type: ignore
            labelDosierungTeilbarkeit = QLabel("Dosierungen und Teilbarkeit")
            labelDosierungTeilbarkeit.setFont(self.fontNormal)
            self.lineEditDosisProEinheit = []
            self.labelEinheitProDarreichungsform = []
            self.comboBoxDosisTeilbarkeit= []
            for i in range(self.maxDosenProEinheit):
                self.lineEditDosisProEinheit.append(QLineEdit())
                self.lineEditDosisProEinheit[i].setFont(self.fontNormal)
                self.lineEditDosisProEinheit[i].setFixedWidth(self.lineEditBreiteKlein)
                self.lineEditDosisProEinheit[i].textChanged.connect(self.lineEditDosisProEinheitTextChanged)
                self.labelEinheitProDarreichungsform.append(QLabel(self.comboBoxMediEinheit.currentText() + "/" + self.comboBoxMediDarreichungsform.currentText()))
                self.labelEinheitProDarreichungsform[i].setFont(self.fontNormal)
                self.comboBoxDosisTeilbarkeit.append(QComboBox())
                self.comboBoxDosisTeilbarkeit[i].setFont(self.fontNormal)
                self.comboBoxDosisTeilbarkeit[i].addItems(["halbierbar", "viertelbar", "nicht teilbar"])
            self.lineEditDosisProEinheit[0].setStyleSheet(self.styleSheetHellrot)
            groupBoxMedikament.setLayout(medikamentLayout)

            medikamentLayout.addWidget(labelMediName, 0, 0, 1, 3)
            medikamentLayout.addWidget(labelMediEinheit, 0, 3)
            medikamentLayout.addWidget(labelMediDarreichungsform, 0, 4)
            medikamentLayout.addWidget(self.lineEditMediName, 1, 0, 1, 3)
            medikamentLayout.addWidget(self.comboBoxMediEinheit, 1, 3)
            medikamentLayout.addWidget(self.comboBoxMediDarreichungsform, 1, 4)
            medikamentLayout.addWidget(labelDosierungTeilbarkeit, 2, 0, 1, 3)
            for i in range(self.maxDosenProEinheit):
                medikamentLayout.addWidget(self.lineEditDosisProEinheit[i], i + 3, 0)
                medikamentLayout.addWidget(self.labelEinheitProDarreichungsform[i], i + 3, 1)
                medikamentLayout.addWidget(self.comboBoxDosisTeilbarkeit[i], i + 3, 2)

            # Groupbox Dosierungsplan
            self.dosierungsplanLayout = QGridLayout()
            groupBoxDosierungsplan = QGroupBox("Dosierungsplan")
            groupBoxDosierungsplan.setFont(self.fontBold)
            self.radioButtonAusschleichen = QRadioButton("Ausschleichen")
            self.radioButtonAusschleichen.setFont(self.fontNormal)
            self.radioButtonAusschleichen.setChecked(True)
            self.radioButtonEinschleichen = QRadioButton("Einschleichen")
            self.radioButtonEinschleichen.setFont(self.fontNormal)
            buttonGroupEinAusschleichen = QButtonGroup(groupBoxDosierungsplan)
            buttonGroupEinAusschleichen.addButton(self.radioButtonAusschleichen, 0)
            buttonGroupEinAusschleichen.addButton(self.radioButtonEinschleichen, 1)
            buttonGroupEinAusschleichen.idClicked.connect(self.buttonGroupEinAusschleichenClicked) # type: ignore
            labelAb = QLabel("Ab")
            labelAb.setFont(self.fontNormal)
            self.dateEditAb = QDateEdit()
            self.dateEditAb.setFont(self.fontNormal)
            self.dateEditAb.setDate(QDate().currentDate())
            self.dateEditAb.setDisplayFormat("dd.MM.yyyy")
            self.dateEditAb.setCalendarPopup(True)
            self.dateEditAb.userDateChanged.connect(self.dateEditAbChanged) # type: ignore
            self.lineEditStartdosis = QLineEdit()
            self.lineEditStartdosis.setFont(self.fontNormal)
            self.lineEditStartdosis.setFixedWidth(self.lineEditBreiteKlein)
            self.lineEditStartdosis.setStyleSheet(self.styleSheetHellrot)
            self.lineEditStartdosis.textChanged.connect(self.lineEditStartdosisTextChanged) # type: ignore
            self.labelEinheitAb = QLabel(self.comboBoxMediEinheit.currentText())
            self.labelEinheitAb.setFont(self.fontNormal)
            labelFuer = QLabel("für")
            labelFuer.setFont(self.fontNormal)
            self.lineEditStartTage = QLineEdit()
            self.lineEditStartTage.setFont(self.fontNormal)
            self.lineEditStartTage.setFixedWidth(self.lineEditBreiteKlein)
            self.lineEditStartTage.setStyleSheet(self.styleSheetHellrot)
            self.lineEditStartTage.textChanged.connect(self.lineEditStartTageTextChanged) # type: ignore
            labelTage = QLabel("Tage")
            labelTage.setFont(self.fontNormal)
            self.labelDannReduktion = []
            self.lineEditReduktionUm = []
            self.labelEinheit1 = []
            self.labelAlle = []
            self.lineEditTage = []
            self.labelTageBis = []
            self.lineEditBis = []
            self.labelEinheit2 = []
            for i in range(self.maxDosierungsplanAnweisungen):
                self.labelDannReduktion.append(QLabel("Dann Reduktion um"))
                self.labelDannReduktion[i].setFont(self.fontNormal)
                self.labelDannReduktion[i].setFont(self.fontNormal)
                self.lineEditReduktionUm.append(QLineEdit())
                self.lineEditReduktionUm[i].setFont(self.fontNormal)
                self.lineEditReduktionUm[i].setFixedWidth(self.lineEditBreiteKlein)
                self.labelEinheit1.append(QLabel(self.comboBoxMediEinheit.currentText()))
                self.labelEinheit1[i].setFont(self.fontNormal)
                self.labelAlle.append(QLabel("alle"))
                self.labelAlle[i].setFont(self.fontNormal)
                self.lineEditTage.append(QLineEdit())
                self.lineEditTage[i].setFont(self.fontNormal)
                self.lineEditTage[i].setFixedWidth(self.lineEditBreiteKlein)
                self.labelTageBis.append(QLabel("Tage bis"))
                self.labelTageBis[i].setFont(self.fontNormal)
                self.lineEditBis.append(QLineEdit())
                self.lineEditBis[i].setFont(self.fontNormal)
                self.lineEditBis[i].setFixedWidth(self.lineEditBreiteKlein)
                self.labelEinheit2.append(QLabel(self.comboBoxMediEinheit.currentText()))
                self.labelEinheit2[i].setFont(self.fontNormal)
            self.labelMaximaleTablettenzahl = QLabel("Maximale Tablettenzahl pro Tag und Tablette einer Dosis")
            self.labelMaximaleTablettenzahl.setFont(self.fontNormal)
            self.lineEditMaximaleTablettenzahl = QLineEdit("2")
            self.lineEditMaximaleTablettenzahl.setFont(self.fontNormal)
            self.lineEditMaximaleTablettenzahl.setFixedWidth(self.lineEditBreiteKlein)
            self.lineEditMaximaleTablettenzahl.textChanged.connect(self.lineEditMaximaleTablettenzahlTextChanged) # type: ignore
            # labelTagesdosisVerteilt = QLabel("Tagesdosis verteilt auf")
            # labelTagesdosisVerteilt.setFont(self.fontNormal)
            # self.comboBoxVerteiltAuf = QComboBox()
            # self.comboBoxVerteiltAuf.setFont(self.fontNormal)
            # self.comboBoxVerteiltAuf.addItems(["1", "2"])
            # self.comboBoxVerteiltAuf.currentIndexChanged.connect(self.comboBoxVerteiltAufIndexChanged)
            # self.labelEinzeldosenVerteilt = QLabel("Einzeldosis")
            # self.labelEinzeldosenVerteilt.setFont(self.fontNormal)
            # self.radioButtonPrioritaetMorgens = QRadioButton("Priorität morgens")
            # self.radioButtonPrioritaetMorgens.setFont(self.fontNormal)
            # self.radioButtonPrioritaetMorgens.setChecked(True)
            # self.radioButtonPrioritaetAbends = QRadioButton("Priorität abends")
            # self.radioButtonPrioritaetAbends.setFont(self.fontNormal)
            # buttonGroupPrioritaet = QButtonGroup(groupBoxDosierungsplan)
            # buttonGroupPrioritaet.addButton(self.radioButtonPrioritaetMorgens, 0)
            # buttonGroupPrioritaet.addButton(self.radioButtonPrioritaetAbends, 1)

            self.dosierungsplanLayout.addWidget(self.radioButtonAusschleichen, 0, 0, 1, 4)
            self.dosierungsplanLayout.addWidget(self.radioButtonEinschleichen, 0, 4, 1, 5)
            self.dosierungsplanLayout.addWidget(labelAb, 1, 0)
            self.dosierungsplanLayout.addWidget(self.dateEditAb, 1, 1)
            self.dosierungsplanLayout.addWidget(self.lineEditStartdosis, 1, 2)
            self.dosierungsplanLayout.addWidget(self.labelEinheitAb, 1, 3)
            self.dosierungsplanLayout.addWidget(labelFuer, 1, 4)
            self.dosierungsplanLayout.addWidget(self.lineEditStartTage, 1, 5)
            self.dosierungsplanLayout.addWidget(labelTage, 1, 6)
            for i in range(self.maxDosierungsplanAnweisungen):
                self.dosierungsplanLayout.addWidget(self.labelDannReduktion[i], i + 2, 0, 1, 2)
                self.dosierungsplanLayout.addWidget(self.lineEditReduktionUm[i], i + 2, 2)
                self.dosierungsplanLayout.addWidget(self.labelEinheit1[i], i + 2, 3)
                self.dosierungsplanLayout.addWidget(self.labelAlle[i], i + 2, 4)
                self.dosierungsplanLayout.addWidget(self.lineEditTage[i], i + 2, 5)
                self.dosierungsplanLayout.addWidget(self.labelTageBis[i], i + 2, 6)
                self.dosierungsplanLayout.addWidget(self.lineEditBis[i], i + 2, 7)
                self.dosierungsplanLayout.addWidget(self.labelEinheit2[i], i + 2, 8)
            self.dosierungsplanLayout.addWidget(self.labelMaximaleTablettenzahl, self.maxDosierungsplanAnweisungen + 2, 0, 1, 7)
            self.dosierungsplanLayout.addWidget(self.lineEditMaximaleTablettenzahl, self.maxDosierungsplanAnweisungen + 2, 7)
            # self.dosierungsplanLayout.addWidget(labelTagesdosisVerteilt, self.maxDosierungsplanAnweisungen + 3, 0, 1, 2)
            # self.dosierungsplanLayout.addWidget(self.comboBoxVerteiltAuf, self.maxDosierungsplanAnweisungen + 3, 2)
            # self.dosierungsplanLayout.addWidget(self.labelEinzeldosenVerteilt, self.maxDosierungsplanAnweisungen + 3, 3)
            # self.dosierungsplanLayout.addWidget(self.radioButtonPrioritaetMorgens, self.maxDosierungsplanAnweisungen + 4, 0, 1, 4)
            # self.dosierungsplanLayout.addWidget(self.radioButtonPrioritaetAbends, self.maxDosierungsplanAnweisungen + 4, 4, 1, 5)
            groupBoxDosierungsplan.setLayout(self.dosierungsplanLayout)

            # Buttons
            buttonLayout = QGridLayout()
            buttonLayout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.pushButtonVorschau = QPushButton("Vorschau")
            self.pushButtonVorschau.setFixedSize(QSize(200, 40))
            self.pushButtonVorschau.clicked.connect(self.pushButtonVorschauClicked) # type: ignore
            self.pushButtonSenden = QPushButton("Plan senden")
            self.pushButtonSenden.setFixedSize(QSize(200, 40))
            self.pushButtonSenden.setEnabled(False)
            self.pushButtonSenden.clicked.connect(self.pushButtonSendenClicked) # type: ignore
            self.pushButtonVorlageSpeichern = QPushButton("Als Vorlage speichern...")
            self.pushButtonVorlageSpeichern.setFixedSize(200,40)
            self.pushButtonVorlageSpeichern.clicked.connect(self.pushButtonVorlageSpeichernClicked) # type: ignore
            buttonLayout.addWidget(self.pushButtonVorschau, 0, 0)
            buttonLayout.addWidget(self.pushButtonSenden, 0, 1)
            buttonLayout.addWidget(self.pushButtonVorlageSpeichern, 1, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)

            # Groupbox PatientIn
            patientLayout = QGridLayout()
            groupBoxPatient = QGroupBox("PatientIn")
            groupBoxPatient.setFont(self.fontBold)
            labelVorname = QLabel("Vorname")
            labelVorname.setFont(self.fontNormal)
            labelNachname = QLabel("Nachname")
            labelNachname.setFont(self.fontNormal)
            self.lineEditVorname = QLineEdit(self.vorname)
            self.lineEditVorname.setFont(self.fontNormal)
            self.lineEditVorname.setReadOnly(True)
            self.lineEditNachname = QLineEdit(self.nachname)
            self.lineEditNachname.setFont(self.fontNormal)
            self.lineEditNachname.setReadOnly(True)
            labelGebDat = QLabel("Geburtsdatum")
            labelGebDat.setFont(self.fontNormal)
            labelPatId = QLabel("Pat.-ID")
            labelPatId.setFont(self.fontNormal)
            self.lineEditGebdat = QLineEdit(self.gebdat)
            self.lineEditGebdat.setFont(self.fontNormal)
            self.lineEditGebdat.setReadOnly(True)
            self.lineEditPatId = QLineEdit(self.patId)
            self.lineEditPatId.setFont(self.fontNormal)
            self.lineEditPatId.setReadOnly(True)
            patientLayout.addWidget(labelVorname, 0, 0)
            patientLayout.addWidget(labelNachname, 0, 1)
            patientLayout.addWidget(self.lineEditVorname, 1, 0)
            patientLayout.addWidget(self.lineEditNachname, 1, 1)
            patientLayout.addWidget(labelGebDat, 2, 0)
            patientLayout.addWidget(labelPatId, 2, 1)
            patientLayout.addWidget(self.lineEditGebdat, 3, 0)
            patientLayout.addWidget(self.lineEditPatId, 3, 1)
            groupBoxPatient.setLayout(patientLayout)

            # Vorschau
            vorschauLayout = QVBoxLayout()
            groupBoxVorschau = QGroupBox("Vorschau")
            groupBoxVorschau.setFont(self.fontBold)
            groupBoxVorschau.setMinimumWidth(500)
            self.textEditVorschau = QTextEdit()
            vorschauLayout.addWidget(self.textEditVorschau)
            groupBoxVorschau.setLayout(vorschauLayout)
            
            mainLayoutLinkeSpalte.addWidget(groupBoxMedikament)
            mainLayoutLinkeSpalte.addWidget(groupBoxDosierungsplan)
            mainLayoutLinkeSpalte.addLayout(buttonLayout)
            mainLayoutLinkeSpalte.addWidget(groupBoxPatient)
            mainLayoutRechteSpalte.addWidget(groupBoxVorschau)

            mainSpaltenlayout.addLayout(mainLayoutLinkeSpalte)
            mainSpaltenlayout.addLayout(mainLayoutRechteSpalte)

            # Statusleiste
            self.statusleiste = QStatusBar()
            self.statusleiste.setFont(self.fontKlein)
            mainLayoutLinkeSpalte.addWidget(self.statusleiste)

            if self.addOnsFreigeschaltet and gdttoolsL.GdtToolsLizenzschluessel.getSoftwareId(self.lizenzschluessel) == gdttoolsL.SoftwareId.DOSISGDTPSEUDO:
                mainLayoutV.addWidget(self.labelPseudolizenz, alignment=Qt.AlignmentFlag.AlignCenter)
            
            mainLayoutV.addLayout(mainSpaltenlayout)
            self.widget.setLayout(mainLayoutV)
            self.setCentralWidget(self.widget)
            logger.logger.info("Eingabeformular aufgebaut")

            # Formular ggf. vor-ausfüllen
            if self.defaultXml != "":
                self.setPreFormularXml(os.path.join(basedir, self.vorlagenverzeichnis, self.defaultXml))

            #Menü
            menubar = self.menuBar()
            anwendungMenu = menubar.addMenu("")
            aboutAction = QAction(self)
            aboutAction.setMenuRole(QAction.MenuRole.AboutRole)
            aboutAction.triggered.connect(self.ueberDosisGdt) # type: ignore
            aboutAction.setShortcut(QKeySequence("Ctrl+Ü"))
            updateAction = QAction("Auf Update prüfen", self)
            updateAction.setMenuRole(QAction.MenuRole.ApplicationSpecificRole)
            updateAction.triggered.connect(self.updatePruefung) # type: ignore
            updateAction.setShortcut(QKeySequence("Ctrl+U"))
            vorlagenMenu = menubar.addMenu("Vorlagen")
            i = 0
            vorlagenMenuAction = []
            for vorlage in self.vorlagen:
                vorlagenMenuAction.append(QAction(vorlage, self))
                vorlagenMenuAction[i].triggered.connect(lambda checked=False, name=vorlage: self.vorlagenMenu(checked, name)) # type: ignore
                i += 1
            vorlagenMenuVorlagenVerwaltenAction = QAction("Vorlagen verwalten...", self)
            vorlagenMenuVorlagenVerwaltenAction.setShortcut(QKeySequence("Ctrl+T"))
            vorlagenMenuVorlagenVerwaltenAction.triggered.connect(self.vorlagenMenuVorlagenVerwalten) # type: ignore
            einstellungenMenu = menubar.addMenu("Einstellungen")
            einstellungenAllgemeinAction = QAction("Allgemeine Einstellungen", self)
            einstellungenAllgemeinAction.triggered.connect(lambda neustartfrage: self.einstellungenAllgemein(True)) # type: ignore
            einstellungenAllgemeinAction.setShortcut(QKeySequence("Ctrl+E"))
            einstellungenGdtAction = QAction("GDT-Einstellungen", self)
            einstellungenGdtAction.triggered.connect(lambda neustartfrage: self.einstellungenGdt(True)) # type: ignore
            einstellungenGdtAction.setShortcut(QKeySequence("Ctrl+G"))
            einstellungenErweiterungenAction = QAction("LANR/Lizenzschlüssel", self)
            einstellungenErweiterungenAction.triggered.connect(lambda neustartfrage: self.einstellungenLanrLizenzschluessel(True)) # type: ignore
            einstellungenErweiterungenAction.setShortcut(QKeySequence("Ctrl+L"))
            einstellungenImportExportAction = QAction("Im- /Exportieren", self)
            einstellungenImportExportAction.triggered.connect(self.einstellungenImportExport) # type: ignore
            einstellungenImportExportAction.setShortcut(QKeySequence("Ctrl+I"))
            einstellungenImportExportAction.setMenuRole(QAction.MenuRole.NoRole)
            hilfeMenu = menubar.addMenu("Hilfe")
            hilfeWikiAction = QAction("DosisGDT Wiki", self)
            hilfeWikiAction.triggered.connect(self.dosisgdtWiki) # type: ignore
            hilfeWikiAction.setShortcut(QKeySequence("Ctrl+W"))
            hilfeUpdateAction = QAction("Auf Update prüfen", self)
            hilfeUpdateAction.triggered.connect(self.updatePruefung) # type: ignore
            hilfeUpdateAction.setShortcut(QKeySequence("Ctrl+U"))
            hilfeUeberAction = QAction("Über DosisGDT", self)
            hilfeUeberAction.setMenuRole(QAction.MenuRole.NoRole)
            hilfeUeberAction.triggered.connect(self.ueberDosisGdt) # type: ignore
            hilfeUeberAction.setShortcut(QKeySequence("Ctrl+Ü"))
            hilfeEulaAction = QAction("Lizenzvereinbarung (EULA)", self)
            hilfeEulaAction.triggered.connect(self.eula) 
            hilfeLogExportieren = QAction("Log-Verzeichnis exportieren", self)
            hilfeLogExportieren.triggered.connect(self.logExportieren) # type: ignore
            hilfeLogExportieren.setShortcut(QKeySequence("Ctrl+D"))
            
            anwendungMenu.addAction(aboutAction)
            anwendungMenu.addAction(updateAction)
            for i in range(len(vorlagenMenuAction)):
                vorlagenMenu.addAction(vorlagenMenuAction[i])
            vorlagenMenu.addSeparator()
            vorlagenMenu.addAction(vorlagenMenuVorlagenVerwaltenAction)

            einstellungenMenu.addAction(einstellungenAllgemeinAction)
            einstellungenMenu.addAction(einstellungenGdtAction)
            einstellungenMenu.addAction(einstellungenErweiterungenAction)
            einstellungenMenu.addAction(einstellungenImportExportAction)
            hilfeMenu.addAction(hilfeWikiAction)
            hilfeMenu.addSeparator()
            hilfeMenu.addAction(hilfeUpdateAction)
            hilfeMenu.addSeparator()
            hilfeMenu.addAction(hilfeUeberAction)
            hilfeMenu.addAction(hilfeEulaAction)
            hilfeMenu.addSeparator()
            hilfeMenu.addAction(hilfeLogExportieren)

            # Updateprüfung auf Github
            try:
                self.updatePruefung(meldungNurWennUpdateVerfuegbar=True)
            except Exception as e:
                mb = QMessageBox(QMessageBox.Icon.Warning, "Hinweis von DosisGDT", "Updateprüfung nicht möglich.\nBitte überprüfen Sie Ihre Internetverbindung.", QMessageBox.StandardButton.Ok)
                mb.exec()
                logger.logger.warning("Updateprüfung nicht möglich: " + str(e))
        else:
            sys.exit()

    def setStatusMessage(self, message = ""):
        self.statusleiste.clearMessage()
        if message != "":
            self.statusleiste.showMessage("Statusmeldung: " + message)
            logger.logger.info("Statusmessage: " + message)
    
    def comboBoxMediEinheitIndexChanged(self):
        for i in range(4):
            self.labelEinheitProDarreichungsform[i].setText(self.comboBoxMediEinheit.currentText() + "/" + self.comboBoxMediDarreichungsform.currentText())
        self.labelEinheitAb.setText(self.comboBoxMediEinheit.currentText())
        for i in range(4):
            self.labelEinheit1[i].setText(self.comboBoxMediEinheit.currentText())
            self.labelEinheit2[i].setText(self.comboBoxMediEinheit.currentText())

    def comboBoxMediDarreichungsformIndexChanged(self, index):
        self.labelEinheitProDarreichungsform[0].setText(self.comboBoxMediEinheit.currentText() + "/" + self.comboBoxMediDarreichungsform.currentText())
        if index == 0:
            self.comboBoxDosisTeilbarkeit[0].setEnabled(True)
        else:
            self.comboBoxDosisTeilbarkeit[0].setEnabled(False)
            self.comboBoxDosisTeilbarkeit[0].setCurrentText("nicht teilbar")
        for i in range(1, 4):
            if index == 0:
                self.lineEditDosisProEinheit[i].setEnabled(True)
                self.comboBoxDosisTeilbarkeit[i].setEnabled(True)
                self.labelMaximaleTablettenzahl.setText("Maximale Tablettenzahl pro Tag und Tablette einer Dosis")
                self.lineEditMaximaleTablettenzahl.setText("2")
            else:
                self.lineEditDosisProEinheit[i].setText("")
                self.lineEditDosisProEinheit[i].setEnabled(False)
                self.comboBoxDosisTeilbarkeit[i].setEnabled(False)
                self.labelMaximaleTablettenzahl.setText("Maximale Tropfenanzahl pro Tag")
                self.lineEditMaximaleTablettenzahl.setText("100")
            

    # def comboBoxVerteiltAufIndexChanged(self, index):
    #     if index == 0:
    #         self.labelEinzeldosenVerteilt.setText("Einzeldosis")
    #     else:
    #         self.labelEinzeldosenVerteilt.setText("Einzeldosen")

    def buttonGroupEinAusschleichenClicked(self, id):
        for i in range(4):
            if id == 0:
                self.labelDannReduktion[i].setText("Dann Reduktion um")
            else:
                self.labelDannReduktion[i].setText("Dann Steigerung um")
    
    # Formulareingaben prüfen
    def lineEditMediNameTextChanged(self, text):
        if text.strip() == "":
            self.lineEditMediName.setStyleSheet(self.styleSheetHellrot)
            self.setStatusMessage("Kein Medikamentenname eingetragen")
        else:
            self.lineEditMediName.setStyleSheet(self.styleSheetWeiss)
            self.setStatusMessage()

    def lineEditDosisProEinheitTextChanged(self):
        keineDosisAngegeben = True
        for i in range(self.maxDosenProEinheit):
            if self.lineEditDosisProEinheit[i].text().strip() != "":
                keineDosisAngegeben = False
                break
        if keineDosisAngegeben:
            self.lineEditDosisProEinheit[0].setStyleSheet(self.styleSheetHellrot)
            self.setStatusMessage("Keine Medikamentendosis angegeben")
        else:
            self.lineEditDosisProEinheit[0].setStyleSheet(self.styleSheetWeiss)
            self.setStatusMessage()
            for i in range(self.maxDosenProEinheit):
                if self.lineEditDosisProEinheit[i].text().strip() != "" and re.match(self.patternDosis, self.lineEditDosisProEinheit[i].text().strip()) == None:
                    self.lineEditDosisProEinheit[i].setStyleSheet(self.styleSheetHellrot)
                    self.setStatusMessage("Medikamentendosis unzulässig")
                    break
                else: 
                    self.lineEditDosisProEinheit[i].setStyleSheet(self.styleSheetWeiss)
                    self.setStatusMessage()

    def dateEditAbChanged(self, datum):
        if datum.daysTo(QDate().currentDate()) > 0:
            self.planBeginnInVergangenheit = True

    def lineEditStartdosisTextChanged(self, text):
        if text.strip() == "":
            self.lineEditStartdosis.setStyleSheet(self.styleSheetHellrot)
            self.setStatusMessage("Keine Startdosis eingetragen")
        elif re.match(self.patternDosis, text) == None:
            self.lineEditStartdosis.setStyleSheet(self.styleSheetHellrot)
            self.setStatusMessage("Startdosis unzulässig")
        else:
            self.lineEditStartdosis.setStyleSheet(self.styleSheetWeiss)
            self.setStatusMessage()

    def lineEditStartTageTextChanged(self, text):
        if text.strip() == "":
            self.lineEditStartTage.setStyleSheet(self.styleSheetHellrot)
            self.setStatusMessage("Kein Startdosis-Zeitraum eingetragen")
        elif re.match(self.patternTage, text) == None:
            self.lineEditStartTage.setStyleSheet(self.styleSheetHellrot)
            self.setStatusMessage("Startdosis-Zeitraum unzulässig")
        else:
            self.lineEditStartTage.setStyleSheet(self.styleSheetWeiss)
            self.setStatusMessage()
    
    def lineEditMaximaleTablettenzahlTextChanged(self, text):
        if text.strip() == "":
            self.lineEditMaximaleTablettenzahl.setStyleSheet(self.styleSheetHellrot)
            self.setStatusMessage("Keine Tablettenzahl eingetragen")
        elif re.match(self.patternTage, text) == None:
            self.lineEditMaximaleTablettenzahl.setStyleSheet(self.styleSheetHellrot)
            self.setStatusMessage("Tablettenzahl unzulässig")
        else:
            self.lineEditMaximaleTablettenzahl.setStyleSheet(self.styleSheetWeiss)
            self.setStatusMessage()
    
    def formularPruefen(self):
        """
        Prüft das Eingabeformular auf Formfehler und gibt eine String-Liste mit Fehlern zurück
        Return:
            fehler: list
        """
        fehler = []
        if self.lineEditMediName.text() == "":
            fehler.append("Kein Medikamentenname eingetragen")
        for i in range(len(self.lineEditDosisProEinheit)):
            if self.lineEditDosisProEinheit[i].styleSheet() == self.styleSheetHellrot:
                fehler.append("Ungültiger Eintrag bei Medikament/Dosierungen")
        if self.dateEditAb.styleSheet() == self.styleSheetHellrot:
            fehler.append("Ungültiges Datum bei Dosierungsplan/Ab")
        if self.lineEditStartdosis.styleSheet() == self.styleSheetHellrot:
            fehler.append("Ungültiger Eintrag bei Dosierungsplan/Startdosis")
        if self.lineEditStartTage.styleSheet() == self.styleSheetHellrot:
            fehler.append("Ungültiger Eintrag bei Dosierungsplan/Startzeitraum")
        if self.lineEditMaximaleTablettenzahl.styleSheet() == self.styleSheetHellrot:
            fehler.append("Ungültiger Eintrag bei Dosierungsplan/Maximale Tablettenzahl")
        if len(fehler) == 0:
            if self.radioButtonAusschleichen.isChecked():
                i = 0
                while i < self.maxDosierungsplanAnweisungen and self.lineEditReduktionUm[i].text().strip() != "":
                    if re.match(self.patternDosis, self.lineEditReduktionUm[i].text()) != None:
                        if re.match(self.patternDosis, self.lineEditBis[i].text()) != None:
                            vorherigeDosis = float(self.lineEditStartdosis.text().replace(",", "."))
                            if i > 0:
                                vorherigeDosis = float(self.lineEditBis[i - 1].text().replace(",", "."))
                            reduktionsdosis = float(self.lineEditReduktionUm[i].text().replace(",", "."))
                            if float(self.lineEditBis[i].text().replace(",", ".")) > (vorherigeDosis - reduktionsdosis):
                                fehler.append("Zielreduktionsdosis " + str(i + 1) + " zu groß")
                            if reduktionsdosis > vorherigeDosis:
                                fehler.append("Reduktionsdosis " + str(i + 1) + " zu groß")
                            if re.match(self.patternTage, self.lineEditTage[i].text()) == None or int(self.lineEditTage[i].text()) < 1:
                                fehler.append("Reduktionszeitraum " + str(i + 1) + " ungültig")
                        else:
                            fehler.append("Zielreduktionsdosis " + str(i + 1) + " ungültig")
                    else:
                        fehler.append("Reduktionsdosis " + str(i + 1) + " ungültig")
                    if len(fehler) > 0:
                        break
                    i += 1
            else:
                i = 0
                while i < self.maxDosierungsplanAnweisungen and self.lineEditReduktionUm[i].text().strip() != "":
                    if re.match(self.patternDosis, self.lineEditReduktionUm[i].text()) != None:
                        if re.match(self.patternDosis, self.lineEditBis[i].text()) != None:
                            vorherigeDosis = float(self.lineEditStartdosis.text().replace(",", "."))
                            if i > 0:
                                vorherigeDosis = float(self.lineEditBis[i - 1].text().replace(",", "."))
                            steigerungsdosis = float(self.lineEditReduktionUm[i].text().replace(",", "."))
                            if float(self.lineEditBis[i].text().replace(",", ".")) < (vorherigeDosis + steigerungsdosis):
                                fehler.append("Zielreduktionsdosis " + str(i + 1) + " zu klein")
                            if re.match(self.patternTage, self.lineEditTage[i].text()) == None or int(self.lineEditTage[i].text()) < 1:
                                fehler.append("Reduktionszeitraum " + str(i + 1) + " ungültig")
                        else:
                            fehler.append("Zielreduktionsdosis " + str(i + 1) + " ungültig")
                    else:
                        fehler.append("Reduktionsdosis " + str(i + 1) + " ungültig")
                    if len(fehler) > 0:
                        break
                    i += 1
        return fehler
    
    def dosierungsplanBerechnen(self):
        """
        Berechnet den Dosierungsplan
        Return:
            Tupel mit medikament und Ergebnis von class_dosierungsplan.get_dosierungsplan (Dictionary: vonDatum, bisDatum, dosis, tabletten)
        """
        dosenProEinheit = []
        teilbarkeiten = []
        for i in range(self.maxDosenProEinheit):
            if self.lineEditDosisProEinheit[i].text() != "":
                dosenProEinheit.append(float(self.lineEditDosisProEinheit[i].text().strip().replace(",", ".")))
                if self.comboBoxDosisTeilbarkeit[i].currentText() == "halbierbar":
                    teilbarkeiten.append(class_medikament.Teilbarkeit.HALBIERBAR)
                elif self.comboBoxDosisTeilbarkeit[i].currentText() == "viertelbar":
                    teilbarkeiten.append(class_medikament.Teilbarkeit.VIERTELBAR)
                elif self.comboBoxDosisTeilbarkeit[i].currentText() == "nicht teilbar":
                    teilbarkeiten.append(class_medikament.Teilbarkeit.NICHT_TEILBAR)
        einheit = class_medikament.Einheit.MG
        if self.comboBoxMediEinheit.currentText() == "µg":
            einheit = class_medikament.Einheit.MIG
        elif self.comboBoxMediEinheit.currentText() == "g":
            einheit = class_medikament.Einheit.G
        darreichungsform = class_medikament.Darreichungsform.TABLETTE
        if self.comboBoxMediDarreichungsform.currentText() == "Tropfen":
            darreichungsform = class_medikament.Darreichungsform.TROPFEN

        medikament = class_medikament.Medikament(self.lineEditMediName.text().strip(), einheit, darreichungsform, dosenProEinheit, teilbarkeiten)
        dosierungsplan = class_dosierungsplan.Dosierungsplan(self.radioButtonEinschleichen.isChecked(), medikament, int(self.lineEditMaximaleTablettenzahl.text().strip()), False, True)
        startdatum = "{:>02}".format(str(self.dateEditAb.date().day())) + "{:>02}".format(str(self.dateEditAb.date().month())) + str(self.dateEditAb.date().year())
        dosierungsplan.set_start(startdatum, float(self.lineEditStartdosis.text().strip().replace(",",".")), int(self.lineEditStartTage.text()))
        aenderungen = []
        i = 0
        while self.lineEditReduktionUm[i].text() != "":
            reduktionsdosis = float(self.lineEditReduktionUm[i].text().strip().replace(",","."))
            if self.radioButtonAusschleichen.isChecked():
                reduktionsdosis = -reduktionsdosis
            aenderungen.append(class_dosierungsplan.Aenderung(reduktionsdosis, int(self.lineEditTage[i].text().strip()), float(self.lineEditBis[i].text().strip().replace(",","."))))
            i += 1
        dosierungsplan.set_aenderung(aenderungen)
        dp = []
        try:
            dp = dosierungsplan.get_dosierungsplan()
        except class_dosierungsplan.DosierungsfehlerException as e:
                mb = QMessageBox(QMessageBox.Icon.Warning, "Hinweis von DosisGDT", "Fehler bei der Berechung des Dosierungsplans: " + e.meldung, QMessageBox.StandardButton.Ok)
                mb.exec()
        return (medikament, dp)
    
    def pushButtonVorlageSpeichernClicked(self):
        FILTER = ["DGV-Dateien (*.dgv)", "Alle Dateien (*:*)"]
        filter = ";;".join(FILTER)
        dateiname, filter = QFileDialog.getSaveFileName(self, "Vorlage speichern", self.vorlagenverzeichnis, filter, FILTER[0])
        if dateiname:
            # XML-Datei erzeugen
            dosierungsplanElement = ElementTree.Element("dosierungdsplan")
            medikamentElement = ElementTree.Element("medikament")
            nameElement = ElementTree.Element("name")
            nameElement.text = self.lineEditMediName.text()
            einheitElement = ElementTree.Element("einheit")
            einheitElement.text = self.comboBoxMediEinheit.currentText()
            darreichungsformElement = ElementTree.Element("darreichungsform")
            darreichungsformElement.text = self.comboBoxMediDarreichungsform.currentText()
            dosenProEinheitElement = ElementTree.Element("dosenProEinheit")
            teilbarkeitenElement = ElementTree.Element("teilbarkeiten")
            dosisElement = []
            teilbarkeitElement = []
            for i in range(self.maxDosenProEinheit):
                if self.lineEditDosisProEinheit[i].text() != "":
                    dosisElement.append(ElementTree.Element("dosis"))
                    dosisElement[i].text = self.lineEditDosisProEinheit[i].text()
                    dosenProEinheitElement.append(dosisElement[i])
                    teilbarkeitElement.append(ElementTree.Element("teilbarkeit"))
                    teilbarkeitElement[i].text = self.comboBoxDosisTeilbarkeit[i].currentText()
                    teilbarkeitenElement.append(teilbarkeitElement[i])
                else:
                    break
            medikamentElement.append(nameElement)
            medikamentElement.append(einheitElement)
            medikamentElement.append(darreichungsformElement)
            medikamentElement.append(dosenProEinheitElement)
            medikamentElement.append(teilbarkeitenElement)
            startdosisElement = ElementTree.Element("startdosis")
            startdosisElement.text = self.lineEditStartdosis.text()
            startdauerElement = ElementTree.Element("startdauer")
            startdauerElement.text = self.lineEditStartTage.text()
            aenderungenElement = ElementTree.Element("aenderungen")
            aenderungElement = []
            reduktionUmElement = []
            tageElement = []
            bisElement = []
            for i in range(self.maxDosierungsplanAnweisungen):
                if self.lineEditReduktionUm[i].text() != "":
                    aenderungElement.append(ElementTree.Element("aenderung"))
                    reduktionUmElement.append(ElementTree.Element("reduktionUm"))
                    reduktionUmElement[i].text = self.lineEditReduktionUm[i].text().replace(",",".")
                    aenderungElement[i].append(reduktionUmElement[i])
                    tageElement.append(ElementTree.Element("tage"))
                    tageElement[i].text = self.lineEditTage[i].text()
                    aenderungElement[i].append(tageElement[i])
                    bisElement.append(ElementTree.Element("bis"))
                    bisElement[i].text = self.lineEditBis[i].text().replace(",",".")
                    aenderungElement[i].append(bisElement[i])
                    aenderungenElement.append(aenderungElement[i])
                else:
                    break
            maxTablettenzahlElement = ElementTree.Element("maxTablettenzahl")
            maxTablettenzahlElement.text = self.lineEditMaximaleTablettenzahl.text()
            dosierungsplanElement.append(medikamentElement)
            dosierungsplanElement.append(startdosisElement)
            dosierungsplanElement.append(startdauerElement)
            dosierungsplanElement.append(aenderungenElement)
            dosierungsplanElement.append(maxTablettenzahlElement)
            et = ElementTree.ElementTree(dosierungsplanElement)
            ElementTree.indent(et)
            try:
                et.write(dateiname, "utf-8", True)
                mb = QMessageBox(QMessageBox.Icon.Question, "Hinweis von DosisGDT", "Damit die Vorlage in die Menüleiste übernommen wird, muss DosisGDT neu gestartet werden.\nSoll DosisGDT jetzt neu gestartet werden?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                mb.setDefaultButton(QMessageBox.StandardButton.Yes)
                mb.button(QMessageBox.StandardButton.Yes).setText("Ja")
                mb.button(QMessageBox.StandardButton.No).setText("Nein")
                if mb.exec() == QMessageBox.StandardButton.Yes:
                    os.execl(sys.executable, __file__, *sys.argv)
            except Exception as e:
                self.setStatusMessage("Fehler beim Speichern der Vorlage: " + e.args[1])
                logger.logger.error("Fehler beim Speichern der Vorlage " + dateiname) 
    
    def pushButtonVorschauClicked(self):
        self.textEditVorschau.clear()
        fehler = self.formularPruefen()
        if len(fehler) != 0:
            text = ""
            for f in fehler:
                text += "\u26a0" + " " + f + "<br />"
            html = "<span style='font-weight:normal;color:rgb(200,0,0)'>" + text + "</span>"
            self.textEditVorschau.setHtml(html)
        else:
            self.pushButtonSenden.setEnabled(True)
            medikament, dp = self.dosierungsplanBerechnen()
            if len(dp) > 0:
                darreichungsform = "Tabletten"
                if medikament.darreichungsform == class_medikament.Darreichungsform.TROPFEN:
                    darreichungsform = "Tropfen"
                text = "<style>table.dosierungsplan { margin-top:6px;border-collapse:collapse } table.dosierungsplan td { padding:2px;border:1px solid rgb(0,0,0);font-weight:normal; } table.dosierungsplan td table {border-collapse:collapse;padding:0px } table.dosierungsplan td table td {border:none;padding:0px 2px 0px 2px; } </style>"
                text += "<div style='font-weight:bold'>" + self.lineEditMediName.text().strip() + "-Dosierungsplan:</div>"
                text += "<table class='dosierungsplan'>"
                text += "<tr><td><b>Von</b></td><td><b>Bis</b></td><td><b>Dosis</b></td><td><b>" + darreichungsform + "-Einnahme</b></td></tr>"
                j = 0
                for zeile in dp:
                    tablettenaufteilung = ""
                    einheit = "mg"
                    if medikament.einheit == class_medikament.Einheit.MIG:
                        einheit = "µg"
                    elif medikament.einheit == class_medikament.Einheit.G:
                        einheit = "g"
                    i = 0
                    d = []
                    for dosisProEinheit in medikament.dosenProEinheit:
                        if medikament.darreichungsform == class_medikament.Darreichungsform.TABLETTE:
                            if zeile["tabletten"][str(dosisProEinheit)] > 0:
                                d.append(str(zeile["tabletten"][str(dosisProEinheit)]).replace(".",",") + "x " + str(dosisProEinheit).replace(".",",") + " " + einheit)
                        else: # Tropfen
                            d.append(str(int(zeile["tabletten"][str(dosisProEinheit)])))
                        i += 1
                    tablettenaufteilung = str.join(" und<br />", d)
                    tablettenaufteilung = tablettenaufteilung.replace(",0", "")
                    tablettenaufteilung = tablettenaufteilung.replace("0,5", "\u00bd")
                    tablettenaufteilung = tablettenaufteilung.replace(",5", "\u00bd")
                    tablettenaufteilung = tablettenaufteilung.replace("0,25", "\u00bc")
                    tablettenaufteilung = tablettenaufteilung.replace(",25", "\u00bc")
                    if j < len(dp) - 1:
                        text += "<tr><td>" + zeile["vonDatum"] + "</td><td>" + zeile["bisDatum"] + "</td><td>" + zeile["dosis"] + "</td><td>" + tablettenaufteilung + "</td></tr>"
                    else:
                        text += "<tr><td colspan='2'>Ab " + zeile["vonDatum"] + "</td>"
                        dosis = zeile["dosis"]
                        if zeile["dosis"][0:3] == "0,0":
                            dosis = "Keine " + medikament.darreichungsform.value + " mehr"
                            text += "<td colspan='2'>" + dosis + "</td>"
                        else:
                            text += "<td>" + dosis + "</td><td>" + tablettenaufteilung + "</td></tr>"
                    j += 1
                text += "</table>"
                text += "<table style='margin-top:10px;border:none;border-collapse:collapse'>"
                text +=" <tr><td colspan='2'><b>" + medikament.name + "-Verbrauch ab " + datetime.date.today().strftime("%d.%m.%Y") + ":</b></td></tr>"
                tablettenGesamtmengen = class_dosierungsplan.Dosierungsplan.getTablettenGesamtmengen(dp, medikament, False)
                if gdttoolsL.GdtToolsLizenzschluessel.lizenzErteilt(self.lizenzschluessel, self.lanr, gdttoolsL.SoftwareId.DOSISGDT):
                    for tablette in tablettenGesamtmengen:
                        if medikament.darreichungsform == class_medikament.Darreichungsform.TABLETTE:
                            text += "<tr style='font-weight:normal'><td>" + tablette + " " + medikament.einheit.value + ":</td><td style='text-align:right'>" + str(tablettenGesamtmengen[tablette]).replace(".",",") + " Stück</td></tr>"
                        else:
                            text += "<tr style='font-weight:normal'><td>" + str(tablettenGesamtmengen[tablette]).replace(".",",") + " Tropfen (" + str(tablettenGesamtmengen[tablette] * float(tablette)).replace(".",",") + " " + medikament.einheit.value + ")"
                else:
                    text+= "<tr><td colspan='2' style='font-weight:normal;color:rgb(200,0,0)'>Für diese Funktion ist eine gültige LANR/Lizenzschlüsselkombination erforderlich.</td></tr>"
                text += "</table>"
                self.textEditVorschau.clear()
                self.textEditVorschau.setHtml(text)


    def pushButtonSendenClicked(self):
        untdatDatetime = datetime.datetime.now()
        fehler = self.formularPruefen()
        medikament = None
        dp = None
        if len(fehler) == 0:
            medikament, dp = self.dosierungsplanBerechnen()
            # PDF erstellen
            darreichungsform = "Tabletten"
            if medikament.darreichungsform == class_medikament.Darreichungsform.TROPFEN:
                darreichungsform = "Tropfen"
            pdf = FPDF()
            logger.logger.info("FPDF-Instanz erzeugt")
            pdf.add_page()
            pdf.set_font("helvetica", "B", 20)
            pdf.cell(0, 10, medikament.name + "-Dosierungsplan", align="C", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("helvetica", "", 14)
            pdf.cell(0, 10, "für " + self.vorname + " " + self.nachname + " (*" + self.gebdat + ")", align="C", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("helvetica", "", 10)
            erstelltAmText = "Erstellt am " + untdatDatetime.strftime("%d.%m.%Y")
            if self.configIni["Allgemein"]["einrichtungaufpdf"] == "1":
                erstelltAmText += " von " + self.configIni["Allgemein"]["einrichtungsname"]
            pdf.cell(0,6, erstelltAmText, align="C", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("helvetica", "", 14)
            pdf.cell(0, 10, "", new_x="LMARGIN", new_y="NEXT")
            titelzeile = ["Von", "Bis", "Dosis", darreichungsform + "-Einnahme"]
            with pdf.table(v_align=enums.VAlign.T, line_height=1.5 * pdf.font_size, cell_fill_color=(230,230,230), cell_fill_mode="ROWS", col_widths=(20,20,10, 50)) as table: # type: ignore
                pdf.set_font("helvetica", "B", 12)
                row = table.row()
                for titel in titelzeile:
                    row.cell(text=titel)
                pdf.set_font("helvetica", "", 12)
                j = 0
                for zeile in dp:
                    einheit = "mg"
                    if medikament.einheit == class_medikament.Einheit.MIG:
                        einheit = "µg"
                    elif medikament.einheit == class_medikament.Einheit.G:
                        einheit = "g"
                    i = 0
                    d = []
                    for dosisProEinheit in medikament.dosenProEinheit:
                        if medikament.darreichungsform == class_medikament.Darreichungsform.TABLETTE:
                            if zeile["tabletten"][str(dosisProEinheit)] > 0:
                                d.append(str(zeile["tabletten"][str(dosisProEinheit)]).replace(".",",") + "x " + str(dosisProEinheit).replace(".",",") + " " + einheit)
                        else: # Tropfen
                            d.append(str(int(zeile["tabletten"][str(dosisProEinheit)])))
                        i += 1
                    tablettenaufteilung = str.join(" und ", d)
                    tablettenaufteilung = tablettenaufteilung.replace(",0", "")
                    tablettenaufteilung = tablettenaufteilung.replace("0,5", "\u00bd")
                    tablettenaufteilung = tablettenaufteilung.replace(",5", "\u00bd")
                    tablettenaufteilung = tablettenaufteilung.replace("0,25", "\u00bc")
                    tablettenaufteilung = tablettenaufteilung.replace(",25", "\u00bc")
                    row = table.row()
                    if j < len(dp) - 1:
                        row.cell(text=zeile["vonDatum"])
                        row.cell(text=zeile["bisDatum"])
                        row.cell(text=zeile["dosis"])
                        row.cell(text=tablettenaufteilung)
                    else:
                        row.cell("Ab " + zeile["vonDatum"], colspan=2)
                        dosis = zeile["dosis"]
                        if zeile["dosis"][0:3] == "0,0":
                            dosis = "Keine " + medikament.darreichungsform.value + " mehr"
                            row.cell(dosis, colspan=2)
                        else:
                            row.cell(text=dosis)
                            row.cell(text=tablettenaufteilung)
                    j += 1
            pdf.set_y(-30)
            pdf.set_font("helvetica", "I", 10)
            pdf.cell(0, 10, "Generiert von DosisGDT V" + self.version + " (\u00a9 GDT-Tools " + str(datetime.date.today().year) + ")", align="R")
            logger.logger.info("PDF-Seite aufgebaut")
            if self.configIni["Allgemein"]["pdferstellen"] == "1":
                try:
                    pdf.output(os.path.join(basedir, "pdf/dosierungsplan_temp.pdf"))
                    logger.logger.info("PDF-Output nach " + os.path.join(basedir, "pdf/dosierungsplan_temp.pdf") + " erfolgreich")
                    self.setStatusMessage("PDF-Datei erstellt")
                except Exception as e:
                    self.setStatusMessage("Fehler bei PDF-Datei-Erstellung: " + e.args[1])
                    logger.logger.error("Fehler bei PDF-Erstellung nach " + os.path.join(basedir, "pdf/dosierungsplan_temp.pdf"))
            
            # GDT-Datei erzeugen
            sh = gdt.SatzHeader(gdt.Satzart.DATEN_EINER_UNTERSUCHUNG_UEBERMITTELN_6310, self.configIni["GDT"]["idpraxisedv"], self.configIni["GDT"]["iddosisgdt"], self.zeichensatz, "2.10", "Fabian Treusch - GDT-Tools", "DosisGDT", self.version, self.patId)
            gd = gdt.GdtDatei()
            logger.logger.info("GdtDatei-Instanz erzeugt")
            gd.erzeugeGdtDatei(sh.getSatzheader())
            logger.logger.info("Satzheader 6310 erzeugt")
            gd.addZeile("6200", untdatDatetime.strftime("%d%m%Y"))
            gd.addZeile("6201", untdatDatetime.strftime("%H%M%S"))
            gd.addZeile("8402", "ALLG01")
            # PDF hinzufügen
            if self.configIni["Allgemein"]["pdferstellen"] == "1" and gdttoolsL.GdtToolsLizenzschluessel.lizenzErteilt(self.lizenzschluessel, self.lanr, gdttoolsL.SoftwareId.DOSISGDT):
                gd.addZeile("6302", "dosierungsplan")
                gd.addZeile("6303", "pdf")
                gd.addZeile("6304", self.configIni["Allgemein"]["pdfbezeichnung"])
                gd.addZeile("6305", os.path.join(basedir, "pdf/dosierungsplan_temp.pdf"))
            gd.addZeile("6220", medikament.name + "-Dosierungsplan")
            gd.addZeile("6226", str(len(dp)))
            for zeile in dp:
                gd.addZeile("6228", zeile["vonDatum"] + " - " + zeile["bisDatum"] + ": " + zeile["dosis"])
            gd.addZeile("6228", "")
            gd.addZeile("6228", medikament.name + "-Verbrauch ab " + untdatDatetime.strftime("%d.%m.%Y") + ":")
            tablettenGesamtmengen = class_dosierungsplan.Dosierungsplan.getTablettenGesamtmengen(dp, medikament, False)
            if gdttoolsL.GdtToolsLizenzschluessel.lizenzErteilt(self.lizenzschluessel, self.lanr, gdttoolsL.SoftwareId.DOSISGDT):
                for tablette in tablettenGesamtmengen:
                    if medikament.darreichungsform == class_medikament.Darreichungsform.TABLETTE:
                        gd.addZeile("6228", tablette + " " + medikament.einheit.value + ": " + str(tablettenGesamtmengen[tablette]).replace(".",",") + " Stück")
                    else:
                        gd.addZeile("6228",  str(tablettenGesamtmengen[tablette]).replace(".",",") + " Tropfen (" + str(tablettenGesamtmengen[tablette] * float(tablette)).replace(".",",") + " " + medikament.einheit.value + ")")
            # GDT-Datei exportieren
            if not gd.speichern(self.gdtExportVerzeichnis + "/" + self.kuerzelpraxisedv + self.kuerzeldosisgdt + ".gdt", self.zeichensatz):
                logger.logger.error("Fehler bei GDT-Dateiexport nach " + self.gdtExportVerzeichnis + "/" + self.kuerzelpraxisedv + self.kuerzeldosisgdt + ".gdt")
                self.setStatusMessage("Fehler beim GDT-Export")
                mb = QMessageBox(QMessageBox.Icon.Warning, "Hinweis von DosisGDT", "GDT-Export nicht möglich.\nBitte überprüfen Sie die Angabe des Exportverzeichnisses.", QMessageBox.StandardButton.Ok)
                mb.exec()
            else:    
                self.setStatusMessage("GDT-Export erfolgreich")
                logger.logger.info("GDT-Datei " + self.gdtExportVerzeichnis + "/" + self.kuerzelpraxisedv + self.kuerzeldosisgdt + ".gdt gespeichert")
            sys.exit()

        else:
            mb = QMessageBox(QMessageBox.Icon.Information, "Hinweis von DosisGDT", "Der Dosierungsplan kann nicht gesendet werden, da das Formular Fehler enthält.", QMessageBox.StandardButton.Ok)
            mb.setTextFormat(Qt.TextFormat.RichText)
            mb.exec()

    def vorlagenMenu(self, checked, name):
        self.setPreFormularXml(os.path.join(self.vorlagenverzeichnis, name + ".dgv"))

    def vorlagenMenuVorlagenVerwalten(self):
        if self.vorlagenverzeichnis != "" and os.path.exists(self.vorlagenverzeichnis):
            defaultxmlkopie = self.defaultXml
            vorlagenkopie = []
            for vorlage in self.vorlagen:
                vorlagenkopie.append(vorlage)
            dv = dialogVorlagenVerwalten.VorlagenVerwalten(vorlagenkopie, defaultxmlkopie)
            if dv.exec() == 1:
                i = 0
                for neueVorlage in dv.vorlagen:
                    if neueVorlage != self.vorlagen[i] and not dv.listWidgetVorlagen.item(i).font().strikeOut():
                        os.rename(os.path.join(self.vorlagenverzeichnis, self.vorlagen[i] + ".dgv"), os.path.join(self.vorlagenverzeichnis, neueVorlage + ".dgv"))
                        if self.vorlagen[i] == self.defaultXml[0:-4]:
                            self.configIni["Allgemein"]["defaultxml"] = neueVorlage + ".dgv"
                        self.vorlagen[i] = neueVorlage
                    elif dv.listWidgetVorlagen.item(i).font().strikeOut():
                        os.remove(os.path.join(self.vorlagenverzeichnis, self.vorlagen[i] + ".dgv"))
                        if self.vorlagen[i] == self.defaultXml[0:-4]:
                            self.configIni["Allgemein"]["defaultxml"] = ""
                    i += 1
                if dv.defaultxml != self.defaultXml:
                    self.defaultXml = dv.defaultxml
                    self.configIni["Allgemein"]["defaultxml"] = dv.defaultxml
                with open(os.path.join(self.configPath, "config.ini"), "w") as configfile:
                    self.configIni.write(configfile)
                mb = QMessageBox(QMessageBox.Icon.Question, "Hinweis von DosisGDT", "Damit die Vorlagen in der Menüleiste aktualisiert werden, muss DosisGDT neu gestartet werden.\nSoll DosisGDT jetzt neu gestartet werden?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                mb.setDefaultButton(QMessageBox.StandardButton.Yes)
                mb.button(QMessageBox.StandardButton.Yes).setText("Ja")
                mb.button(QMessageBox.StandardButton.No).setText("Nein")
                if mb.exec() == QMessageBox.StandardButton.Yes:
                    os.execl(sys.executable, __file__, *sys.argv)
        else:
            mb = QMessageBox(QMessageBox.Icon.Information, "Hinweis von DosisGDT", "Bitte legen Sie in den Allgemeinen Einstellungen ein gültiges Vorlagenverzeichnis an.", QMessageBox.StandardButton.Ok)
            mb.setTextFormat(Qt.TextFormat.RichText)
            mb.exec()
        
    def einstellungenAllgemein(self, neustartfrage = False):
        de = dialogEinstellungenAllgemein.EinstellungenAllgemein(self.configPath)
        if de.exec() == 1:
            self.configIni["Allgemein"]["einrichtungsname"] = de.lineEditEinrichtungsname.text()
            self.configIni["Allgemein"]["pdferstellen"] = "0"
            if de.checkboxPdfErstellen.isChecked():
                self.configIni["Allgemein"]["pdferstellen"] = "1"  
            self.configIni["Allgemein"]["pdfbezeichnung"] = de.lineEditPdfBezeichnung.text()
            self.configIni["Allgemein"]["einrichtungAufPdf"] = "0"
            if de.checkboxEinrichtungAufPdf.isChecked():
                self.configIni["Allgemein"]["einrichtungAufPdf"] = "1"
            self.configIni["Allgemein"]["vorlagenverzeichnis"] = de.lineEditVorlagenverzeichnis.text()
            with open(os.path.join(self.configPath, "config.ini"), "w") as configfile:
                self.configIni.write(configfile)
            if neustartfrage:
                mb = QMessageBox(QMessageBox.Icon.Question, "Hinweis von DosisGDT", "Damit die Einstellungsänderungen wirksam werden, sollte DosisGDT neu gestartet werden.\nSoll DosisGDT jetzt neu gestartet werden?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                mb.setDefaultButton(QMessageBox.StandardButton.Yes)
                mb.button(QMessageBox.StandardButton.Yes).setText("Ja")
                mb.button(QMessageBox.StandardButton.No).setText("Nein")
                if mb.exec() == QMessageBox.StandardButton.Yes:
                    os.execl(sys.executable, __file__, *sys.argv)
        
    def einstellungenGdt(self, neustartfrage=False):
        de = dialogEinstellungenGdt.EinstellungenGdt(self.configPath)
        if de.exec() == 1:
            self.configIni["GDT"]["iddosisgdt"] = de.lineEditDosisGdtId.text()
            self.configIni["GDT"]["idpraxisedv"] = de.lineEditPraxisEdvId.text()
            self.configIni["GDT"]["gdtimportverzeichnis"] = de.lineEditImport.text()
            self.configIni["GDT"]["gdtexportverzeichnis"] = de.lineEditExport.text()
            self.configIni["GDT"]["kuerzeldosisgdt"] = de.lineEditDosisGdtKuerzel.text()
            self.configIni["GDT"]["kuerzelpraxisedv"] = de.lineEditPraxisEdvKuerzel.text()
            self.configIni["GDT"]["zeichensatz"] = str(de.aktuelleZeichensatznummer + 1)
            with open(os.path.join(self.configPath, "config.ini"), "w") as configfile:
                self.configIni.write(configfile)
            if neustartfrage:
                mb = QMessageBox(QMessageBox.Icon.Question, "Hinweis von DosisGDT", "Damit die Einstellungsänderungen wirksam werden, sollte DosisGDT neu gestartet werden.\nSoll DosisGDT jetzt neu gestartet werden?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                mb.setDefaultButton(QMessageBox.StandardButton.Yes)
                mb.button(QMessageBox.StandardButton.Yes).setText("Ja")
                mb.button(QMessageBox.StandardButton.No).setText("Nein")
                if mb.exec() == QMessageBox.StandardButton.Yes:
                    os.execl(sys.executable, __file__, *sys.argv)
    
    def einstellungenLanrLizenzschluessel(self, neustartfrage=False):
        de = dialogEinstellungenLanrLizenzschluessel.EinstellungenProgrammerweiterungen(self.configPath)
        if de.exec() == 1:
            self.configIni["Erweiterungen"]["lanr"] = de.lineEditLanr.text()
            self.configIni["Erweiterungen"]["lizenzschluessel"] = gdttoolsL.GdtToolsLizenzschluessel.krypt(de.lineEditLizenzschluessel.text())
            if de.lineEditLanr.text() == "" and de.lineEditLizenzschluessel.text() == "":
                self.configIni["Allgemein"]["pdferstellen"] = "0"
                self.configIni["Allgemein"]["einrichtungaufpdf"] = "0"
                self.configIni["Allgemein"]["pdfbezeichnung"] = "Dosierungsplan"
            with open(os.path.join(self.configPath, "config.ini"), "w") as configfile:
                self.configIni.write(configfile)
            if neustartfrage:
                mb = QMessageBox(QMessageBox.Icon.Question, "Hinweis von DosisGDT", "Damit die Einstellungsänderungen wirksam werden, sollte DosisGDT neu gestartet werden.\nSoll DosisGDT jetzt neu gestartet werden?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                mb.setDefaultButton(QMessageBox.StandardButton.Yes)
                mb.button(QMessageBox.StandardButton.Yes).setText("Ja")
                mb.button(QMessageBox.StandardButton.No).setText("Nein")
                if mb.exec() == QMessageBox.StandardButton.Yes:
                    os.execl(sys.executable, __file__, *sys.argv)

    def einstellungenImportExport(self):
        de = dialogEinstellungenImportExport.EinstellungenImportExport(self.configPath)
        if de.exec() == 1:
            pass    

    def dosisgdtWiki(self, link):
        QDesktopServices.openUrl("https://github.com/retconx/dosisgdt/wiki")

    def logExportieren(self):
        if (os.path.exists(os.path.join(basedir, "log"))):
            downloadPath = ""
            if sys.platform == "win32":
                downloadPath = os.path.expanduser("~\\Downloads")
            else:
                downloadPath = os.path.expanduser("~/Downloads")
            try:
                if shutil.copytree(os.path.join(basedir, "log"), os.path.join(downloadPath, "Log_DosisGDT"), dirs_exist_ok=True):
                    shutil.make_archive(os.path.join(downloadPath, "Log_DosisGDT"), "zip", root_dir=os.path.join(downloadPath, "Log_DosisGDT"))
                    shutil.rmtree(os.path.join(downloadPath, "Log_DosisGDT"))
                    mb = QMessageBox(QMessageBox.Icon.Warning, "Hinweis von DosisGDT", "Das Log-Verzeichnis wurde in den Ordner " + downloadPath + " kopiert.", QMessageBox.StandardButton.Ok)
                    mb.exec()
            except Exception as e:
                mb = QMessageBox(QMessageBox.Icon.Warning, "Hinweis von DosisGDT", "Problem beim Download des Log-Verzeichnisses: " + str(e), QMessageBox.StandardButton.Ok)
                mb.exec()
        else:
            mb = QMessageBox(QMessageBox.Icon.Warning, "Hinweis von DosisGDT", "Das Log-Verzeichnis wurde nicht gefunden.", QMessageBox.StandardButton.Ok)
            mb.exec() 
                
    def updatePruefung(self, meldungNurWennUpdateVerfuegbar = False):
        response = requests.get("https://api.github.com/repos/retconx/dosisgdt/releases/latest")
        githubRelaseTag = response.json()["tag_name"]
        latestVersion = githubRelaseTag[1:] # ohne v
        if versionVeraltet(self.version, latestVersion):
            mb = QMessageBox(QMessageBox.Icon.Warning, "Hinweis von DosisGDT", "Die aktuellere DosisGDT-Version " + latestVersion + " ist auf <a href='https://www.github.com/retconx/dosisgdt/releases'>Github</a> verfügbar.", QMessageBox.StandardButton.Ok)
            mb.setTextFormat(Qt.TextFormat.RichText)
            mb.exec()
        elif not meldungNurWennUpdateVerfuegbar:
            mb = QMessageBox(QMessageBox.Icon.Warning, "Hinweis von DosisGDT", "Sie nutzen die aktuelle DosisGDT-Version.", QMessageBox.StandardButton.Ok)
            mb.exec()
    
    def ueberDosisGdt(self):
        de = dialogUeberDosisGdt.UeberDosisGdt()
        de.exec()
    
    def eula(self):
        QDesktopServices.openUrl("https://gdttools.de/Lizenzvereinbarung_DosisGDT.pdf")

app = QApplication(sys.argv)
qt = QTranslator()
filename = "qtbase_de"
directory = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
qt.load(filename, directory)
app.installTranslator(qt)
app.setWindowIcon(QIcon(os.path.join(basedir, "icons/program.png")))
window = MainWindow()
window.show()

app.exec()
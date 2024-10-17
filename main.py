import sys, configparser, os, datetime, shutil,logger, re, atexit, subprocess
import gdt, gdtzeile
## Nur mit Lizenz
import gdttoolsL
## /Nur mit Lizenz
import xml.etree.ElementTree as ElementTree
from fpdf import FPDF, enums
import class_dosierungsplan, class_enums, datetime, class_tablette
import dialogUeberDosisGdt, dialogEinstellungenGdt, dialogEinstellungenAllgemein, dialogEinstellungenLanrLizenzschluessel, dialogEinstellungenImportExport, dialogVorlagenVerwalten, dialogEula
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
    QFileDialog,
    QCheckBox
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
        os.remove(os.path.join(basedir, "log", logListe[0]))
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
            einheit = class_enums.Einheit(str(medikamentElement.findtext("einheit"))) # type: ignore
            darreichungsform = class_enums.Applikationsart(medikamentElement.find("darreichungsform").text) # type: ignore
            elementDosenproEinheit = medikamentElement.find("dosenProEinheit") # type: ignore
            dosenProEinheit = []
            for elementDosisProEinheit in elementDosenproEinheit.findall("dosis"): # type: ignore
                if elementDosisProEinheit.text != None:
                    dosenProEinheit.append(str(elementDosisProEinheit.text).replace(".", ","))
                else:
                    dosenProEinheit.append("")
            elementTeilbarkeiten = medikamentElement.find("teilbarkeiten") # type: ignore
            teilbarkeiten = []
            for elementTeilbarkeit in elementTeilbarkeiten.findall("teilbarkeit"): # type: ignore
                teilbarkeiten.append(class_enums.Teilbarkeit(elementTeilbarkeit.text))
            startdosis = str(dosierungsplanElement.findtext("startdosis")).replace(".", ",")
            startdauer = str(dosierungsplanElement.findtext("startdauer"))
            aenderungenElement = dosierungsplanElement.find("aenderungen")
            aenderungUm = []
            tage = []
            bis = []
            for aenderungElement in aenderungenElement.findall("aenderung"): # type: ignore
                if aenderungElement.findtext("reduktionUm") != None:
                    aenderungUm.append(str(aenderungElement.findtext("reduktionUm")).replace(".", ","))
                    tage.append(str(aenderungElement.findtext("tage")))
                    bis.append(str(aenderungElement.findtext("bis")).replace(".", ","))
                elif aenderungElement.findtext("aenderungUm") != None: # ab 1.3.0
                    aenderungUm.append(str(aenderungElement.findtext("aenderungUm")).replace(".", ","))
                    tage.append(str(aenderungElement.findtext("tage")))
                    bis.append(str(aenderungElement.findtext("bis")).replace(".", ","))
                else:
                    aenderungUm.append("")
                    tage.append("")
                    bis.append("")

            # Ab 1.3.0
            einschleichen = False
            einschleichenElement = dosierungsplanElement.find("einschleichen")
            if einschleichenElement != None:
                einschleichen = str(einschleichenElement.text) == "True" # type: ignore
            zweimalTaeglicheeinnahme = False
            if dosierungsplanElement.findtext("zweimaltaeglicheeinnahme") != None:
                zweimalTaeglicheeinnahme = str(dosierungsplanElement.findtext("zweimaltaeglicheeinnahme")) == "True"
            prioritaet = 0
            if dosierungsplanElement.findtext("prioritaet") != None:
                prioritaet = int(str(dosierungsplanElement.findtext("prioritaet")))

            self.lineEditMediName.setText(medikamentenname)
            self.comboBoxMediEinheit.setCurrentText(einheit.value)
            self.comboBoxMediDarreichungsform.setCurrentText(darreichungsform.value)
            for i in range(len(dosenProEinheit)):
                self.lineEditDosisProEinheit[i].setText(dosenProEinheit[i])
            for i in range(len(teilbarkeiten)):
                self.comboBoxDosisTeilbarkeit[i].setCurrentText(teilbarkeiten[i].value)
            self.radioButtonAusschleichen.setChecked(not einschleichen)
            self.radioButtonEinschleichen.setChecked(einschleichen)
            self.lineEditStartdosis.setText(startdosis)
            self.lineEditStartTage.setText(startdauer)
            for i in range(len(aenderungUm)):
                self.lineEditReduktionUm[i].setText(aenderungUm[i])
                self.lineEditTage[i].setText(tage[i])
                self.lineEditBis[i].setText(bis[i])
            self.checkBoxZweimalTaeglicheEinnahme.setChecked(zweimalTaeglicheeinnahme)
            self.radioButtonPrioritaetMorgens.setChecked(prioritaet == 0)
            self.radioButtonPrioritaetAbends.setChecked(prioritaet == 1)
            self.setStatusMessage("Vorlage " + os.path.basename(xmlDateipdad) + " geladen")
            logger.logger.info("Eingabeformular vor-ausgefüllt")
            self.setCursor(Qt.CursorShape.ArrowCursor)
        except Exception as e:
            mb = QMessageBox(QMessageBox.Icon.Warning, "Hinweis von DosisGDT", "Fehler beim Laden der Vorlage (" + xmlDateipdad + "): " + e.args[1], QMessageBox.StandardButton.Ok)
            mb.exec()

    def __init__(self):
        super().__init__()
        self.dosierungsplanfehlerGemeldet = False

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
        # 1.2.0
        self.autoupdate = True
        self.updaterpfad = ""
        if self.configIni.has_option("Allgemein", "autoupdate"):
            self.autoupdate = self.configIni["Allgemein"]["autoupdate"] == "True"
        if self.configIni.has_option("Allgemein", "updaterpfad"):
            self.updaterpfad = self.configIni["Allgemein"]["updaterpfad"]
        # /Nachträglich hinzufefügte Options

        z = self.configIni["GDT"]["zeichensatz"]
        self.zeichensatz = gdt.GdtZeichensatz.IBM_CP437
        if z == "1":
            self.zeichensatz = gdt.GdtZeichensatz.BIT_7
        elif z == "3":
            self.zeichensatz = gdt.GdtZeichensatz.ANSI_CP1252
        self.lanr = self.configIni["Erweiterungen"]["lanr"]
        self.lizenzschluessel = self.configIni["Erweiterungen"]["lizenzschluessel"]

        ## Nur mit Lizenz
        # Prüfen, ob Lizenzschlüssel unverschlüsselt
        if len(self.lizenzschluessel) == 29:
            logger.logger.info("Lizenzschlüssel unverschlüsselt")
            self.configIni["Erweiterungen"]["lizenzschluessel"] = gdttoolsL.GdtToolsLizenzschluessel.krypt(self.lizenzschluessel)
            with open(os.path.join(self.configPath, "config.ini"), "w") as configfile:
                    self.configIni.write(configfile)
        else:
            self.lizenzschluessel = gdttoolsL.GdtToolsLizenzschluessel.dekrypt(self.lizenzschluessel)
        ## /Nur mit Lizenz

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
                ## Nur mit Lizenz
                self.einstellungenLanrLizenzschluessel(False, False)
                ## /Nur mit Lizenz
                self.einstellungenGdt(False, False)
                self.einstellungenAllgemein(False, False)
                mb = QMessageBox(QMessageBox.Icon.Warning, "Hinweis von DosisGDT", "Die Ersteinrichtung ist abgeschlossen. DosisGDT wird beendet.", QMessageBox.StandardButton.Ok)
                mb.exec()
                sys.exit()

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
                # 1.1.10 -> 1.2.0 ["Allgemein"]["autoupdate"] und ["Allgemein"]["updaterpfad"] hinzufügen
                if not self.configIni.has_option("Allgemein", "autoupdate"):
                    self.configIni["Allgemein"]["autoupdate"] = "True"
                if not self.configIni.has_option("Allgemein", "updaterpfad"):
                    self.configIni["Allgemein"]["updaterpfad"] = ""
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

        self.addOnsFreigeschaltet = True
        
        ## Nur mit Lizenz
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
        ## /Nur mit Lizenz
        
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
            ## Nur mit Lizenz
            if self.pseudoLizenzId != "":
                self.patId = self.pseudoLizenzId
                logger.logger.info("PatId wegen Pseudolizenz auf " + self.pseudoLizenzId + " gesetzt")
            ## /Nur mit Lizenz
        except (IOError, gdtzeile.GdtFehlerException) as e:
            logger.logger.warning("Fehler beim Laden der GDT-Datei: " + str(e))
            mb = QMessageBox(QMessageBox.Icon.Information, "Hinweis von DosisGDT", "Fehler beim Laden der GDT-Datei:\n" + str(e) + "\n\nDieser Fehler hat in der Regel eine der folgenden Ursachen:\n- Die im PVS und in DosisGDT konfigurierten GDT-Austauschverzeichnisse stimmen nicht überein.\n- DosisGDT wurde nicht aus dem PVS heraus gestartet, so dass keine vom PVS erzeugte GDT-Datei gefunden werden konnte.\n\nSoll DosisGDT dennoch geöffnet werden?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
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
            self.lineEditMediName.textChanged.connect(self.pushButtonPlanSendenDisable) 
            self.comboBoxMediEinheit = QComboBox()
            self.comboBoxMediEinheit.setFont(self.fontNormal)
            self.comboBoxMediEinheit.addItems(["mg", "µg", "g"])
            self.comboBoxMediEinheit.currentIndexChanged.connect(self.comboBoxMediEinheitIndexChanged)
            self.comboBoxMediEinheit.currentIndexChanged.connect(self.pushButtonPlanSendenDisable) 
            self.comboBoxMediDarreichungsform = QComboBox()
            self.comboBoxMediDarreichungsform.setFont(self.fontNormal)
            self.comboBoxMediDarreichungsform.addItems(["Tablette", "Tropfen"])
            self.comboBoxMediDarreichungsform.currentIndexChanged.connect(self.comboBoxMediDarreichungsformIndexChanged)
            self.comboBoxMediDarreichungsform.currentIndexChanged.connect(self.pushButtonPlanSendenDisable) 
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
                self.lineEditDosisProEinheit[i].textChanged.connect(self.pushButtonPlanSendenDisable) 
                self.labelEinheitProDarreichungsform.append(QLabel(self.comboBoxMediEinheit.currentText() + "/" + self.comboBoxMediDarreichungsform.currentText()))
                self.labelEinheitProDarreichungsform[i].setFont(self.fontNormal)
                self.comboBoxDosisTeilbarkeit.append(QComboBox())
                self.comboBoxDosisTeilbarkeit[i].setFont(self.fontNormal)
                self.comboBoxDosisTeilbarkeit[i].addItems(["halbierbar", "viertelbar", "nicht teilbar"])
                self.comboBoxDosisTeilbarkeit[i].currentIndexChanged.connect(self.pushButtonPlanSendenDisable)
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
            self.radioButtonAusschleichen.clicked.connect(self.pushButtonPlanSendenDisable) 
            self.radioButtonEinschleichen = QRadioButton("Einschleichen")
            self.radioButtonEinschleichen.setFont(self.fontNormal)
            self.radioButtonEinschleichen.clicked.connect(self.pushButtonPlanSendenDisable) 
            self.pushButtonFormularZuruecksetzen = QPushButton("Zurücksetzen")
            self.pushButtonFormularZuruecksetzen.setFont(self.fontNormal)
            self.pushButtonFormularZuruecksetzen.clicked.connect(self.pushButtonFormularZuruecksetzenClicked)
            buttonGroupEinAusschleichen = QButtonGroup(groupBoxDosierungsplan)
            buttonGroupEinAusschleichen.addButton(self.radioButtonAusschleichen, 0)
            buttonGroupEinAusschleichen.addButton(self.radioButtonEinschleichen, 1)
            buttonGroupEinAusschleichen.idClicked.connect(self.buttonGroupEinAusschleichenClicked)
            labelAb = QLabel("Ab")
            labelAb.setFont(self.fontNormal)
            self.dateEditAb = QDateEdit()
            self.dateEditAb.setFont(self.fontNormal)
            self.dateEditAb.setDate(QDate().currentDate())
            self.dateEditAb.setDisplayFormat("dd.MM.yyyy")
            self.dateEditAb.setCalendarPopup(True)
            self.dateEditAb.userDateChanged.connect(self.dateEditAbChanged)
            self.dateEditAb.userDateChanged.connect(self.pushButtonPlanSendenDisable) 
            self.lineEditStartdosis = QLineEdit()
            self.lineEditStartdosis.setFont(self.fontNormal)
            self.lineEditStartdosis.setFixedWidth(self.lineEditBreiteKlein)
            self.lineEditStartdosis.setStyleSheet(self.styleSheetHellrot)
            self.lineEditStartdosis.textChanged.connect(self.lineEditStartdosisTextChanged)
            self.lineEditStartdosis.textChanged.connect(self.pushButtonPlanSendenDisable) 
            self.labelEinheitAb = QLabel(self.comboBoxMediEinheit.currentText())
            self.labelEinheitAb.setFont(self.fontNormal)
            labelFuer = QLabel("für")
            labelFuer.setFont(self.fontNormal)
            self.lineEditStartTage = QLineEdit()
            self.lineEditStartTage.setFont(self.fontNormal)
            self.lineEditStartTage.setFixedWidth(self.lineEditBreiteKlein)
            self.lineEditStartTage.setStyleSheet(self.styleSheetHellrot)
            self.lineEditStartTage.textChanged.connect(self.lineEditStartTageTextChanged)
            self.lineEditStartTage.textChanged.connect(self.pushButtonPlanSendenDisable) 
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
                self.lineEditReduktionUm[i].textChanged.connect(self.pushButtonPlanSendenDisable) 
                self.labelEinheit1.append(QLabel(self.comboBoxMediEinheit.currentText()))
                self.labelEinheit1[i].setFont(self.fontNormal)
                self.labelAlle.append(QLabel("alle"))
                self.labelAlle[i].setFont(self.fontNormal)
                self.lineEditTage.append(QLineEdit())
                self.lineEditTage[i].setFont(self.fontNormal)
                self.lineEditTage[i].setFixedWidth(self.lineEditBreiteKlein)
                self.lineEditTage[i].textChanged.connect(self.pushButtonPlanSendenDisable) 
                self.labelTageBis.append(QLabel("Tage bis"))
                self.labelTageBis[i].setFont(self.fontNormal)
                self.lineEditBis.append(QLineEdit())
                self.lineEditBis[i].setFont(self.fontNormal)
                self.lineEditBis[i].setFixedWidth(self.lineEditBreiteKlein)
                self.lineEditBis[i].textChanged.connect(self.pushButtonPlanSendenDisable) 
                self.labelEinheit2.append(QLabel(self.comboBoxMediEinheit.currentText()))
                self.labelEinheit2[i].setFont(self.fontNormal)
            self.checkBoxZweimalTaeglicheEinnahme = QCheckBox("Zweimal tägliche Einnahme")
            self.checkBoxZweimalTaeglicheEinnahme.setFont(self.fontNormal)
            self.checkBoxZweimalTaeglicheEinnahme.clicked.connect(self.pushButtonPlanSendenDisable) 
            self.radioButtonPrioritaetMorgens = QRadioButton("Priorität morgens")
            self.radioButtonPrioritaetMorgens.setFont(self.fontNormal)
            self.radioButtonPrioritaetMorgens.setChecked(True)
            self.radioButtonPrioritaetMorgens.clicked.connect(self.pushButtonPlanSendenDisable) 
            self.radioButtonPrioritaetAbends = QRadioButton("Priorität abends")
            self.radioButtonPrioritaetAbends.setFont(self.fontNormal)
            self.radioButtonPrioritaetAbends.clicked.connect(self.pushButtonPlanSendenDisable) 

            self.dosierungsplanLayout.addWidget(self.radioButtonAusschleichen, 0, 0, 1, 4)
            self.dosierungsplanLayout.addWidget(self.radioButtonEinschleichen, 0, 4, 1, 3)
            self.dosierungsplanLayout.addWidget(self.pushButtonFormularZuruecksetzen, 0, 7, 1, 2)
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
            self.dosierungsplanLayout.addWidget(self.checkBoxZweimalTaeglicheEinnahme, self.maxDosierungsplanAnweisungen + 2, 0, 1, 3)
            self.dosierungsplanLayout.addWidget(self.radioButtonPrioritaetMorgens, self.maxDosierungsplanAnweisungen + 2, 3, 1, 3)
            self.dosierungsplanLayout.addWidget(self.radioButtonPrioritaetAbends, self.maxDosierungsplanAnweisungen + 2, 6
                                                , 1, 3)
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
            groupBoxVorschau.setMinimumWidth(600)
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

            ## Nur mit Lizenz
            if self.addOnsFreigeschaltet and gdttoolsL.GdtToolsLizenzschluessel.getSoftwareId(self.lizenzschluessel) == gdttoolsL.SoftwareId.DOSISGDTPSEUDO:
                mainLayoutV.addWidget(self.labelPseudolizenz, alignment=Qt.AlignmentFlag.AlignCenter)
            ## /Nur mit Lizenz

            mainLayoutV.addLayout(mainSpaltenlayout)
            ## Nur mit Lizenz
            if self.addOnsFreigeschaltet:
                gueltigeLizenztage = gdttoolsL.GdtToolsLizenzschluessel.nochTageGueltig(self.lizenzschluessel)
                if gueltigeLizenztage  > 0 and gueltigeLizenztage <= 30:
                    labelLizenzLaeuftAus = QLabel("Die genutzte Lizenz ist noch " + str(gueltigeLizenztage) + " Tage gültig.")
                    labelLizenzLaeuftAus.setStyleSheet("color:rgb(200,0,0)")
                    mainLayoutV.addWidget(labelLizenzLaeuftAus, alignment=Qt.AlignmentFlag.AlignCenter)
            else:
                self.pushButtonSenden.setEnabled(False)
                self.pushButtonSenden.setText("Keine gültige Lizenz")
            ## /Nur mit Lizenz
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
            aboutAction.triggered.connect(self.ueberDosisGdt) 
            aboutAction.setShortcut(QKeySequence("Ctrl+Ü"))
            updateAction = QAction("Auf Update prüfen", self)
            updateAction.setMenuRole(QAction.MenuRole.ApplicationSpecificRole)
            updateAction.triggered.connect(self.updatePruefung) 
            updateAction.setShortcut(QKeySequence("Ctrl+U"))
            vorlagenMenu = menubar.addMenu("Vorlagen")
            i = 0
            vorlagenMenuAction = []
            for vorlage in self.vorlagen:
                vorlagenMenuAction.append(QAction(vorlage, self))
                vorlagenMenuAction[i].triggered.connect(lambda checked=False, name=vorlage: self.vorlagenMenu(checked, name))
                i += 1
            vorlagenMenuVorlagenVerwaltenAction = QAction("Vorlagen verwalten...", self)
            vorlagenMenuVorlagenVerwaltenAction.setShortcut(QKeySequence("Ctrl+T"))
            vorlagenMenuVorlagenVerwaltenAction.triggered.connect(self.vorlagenMenuVorlagenVerwalten)
            einstellungenMenu = menubar.addMenu("Einstellungen")
            einstellungenAllgemeinAction = QAction("Allgemeine Einstellungen", self)
            einstellungenAllgemeinAction.triggered.connect(lambda checked = False, neustartfrage = True: self.einstellungenAllgemein(checked, neustartfrage))
            einstellungenAllgemeinAction.setShortcut(QKeySequence("Ctrl+E"))
            einstellungenGdtAction = QAction("GDT-Einstellungen", self)
            einstellungenGdtAction.triggered.connect(lambda checked = False, neustartfrage = True: self.einstellungenGdt(checked, neustartfrage)) 
            einstellungenGdtAction.setShortcut(QKeySequence("Ctrl+G"))
            ## Nur mit Lizenz
            einstellungenErweiterungenAction = QAction("LANR/Lizenzschlüssel", self)
            einstellungenErweiterungenAction.triggered.connect(lambda checked = False, neustartfrage = True: self.einstellungenLanrLizenzschluessel(checked, neustartfrage))
            einstellungenErweiterungenAction.setShortcut(QKeySequence("Ctrl+L"))
            einstellungenImportExportAction = QAction("Im- /Exportieren", self)
            einstellungenImportExportAction.triggered.connect(self.einstellungenImportExport)
            einstellungenImportExportAction.setShortcut(QKeySequence("Ctrl+I"))
            einstellungenImportExportAction.setMenuRole(QAction.MenuRole.NoRole)
            ## /Nur mit Lizenz
            hilfeMenu = menubar.addMenu("Hilfe")
            hilfeWikiAction = QAction("DosisGDT Wiki", self)
            hilfeWikiAction.triggered.connect(self.dosisgdtWiki)
            hilfeWikiAction.setShortcut(QKeySequence("Ctrl+W"))
            hilfeUpdateAction = QAction("Auf Update prüfen", self)
            hilfeUpdateAction.triggered.connect(self.updatePruefung)
            hilfeUpdateAction.setShortcut(QKeySequence("Ctrl+U"))
            hilfeAutoUpdateAction = QAction("Automatisch auf Update prüfen", self)
            hilfeAutoUpdateAction.setCheckable(True)
            hilfeAutoUpdateAction.setChecked(self.autoupdate)
            hilfeAutoUpdateAction.triggered.connect(self.autoUpdatePruefung)
            hilfeUeberAction = QAction("Über DosisGDT", self)
            hilfeUeberAction.setMenuRole(QAction.MenuRole.NoRole)
            hilfeUeberAction.triggered.connect(self.ueberDosisGdt)
            hilfeUeberAction.setShortcut(QKeySequence("Ctrl+Ü"))
            hilfeEulaAction = QAction("Lizenzvereinbarung (EULA)", self)
            hilfeEulaAction.triggered.connect(self.eula) 
            hilfeLogExportieren = QAction("Log-Verzeichnis exportieren", self)
            hilfeLogExportieren.triggered.connect(self.logExportieren)
            hilfeLogExportieren.setShortcut(QKeySequence("Ctrl+D"))
            
            anwendungMenu.addAction(aboutAction)
            anwendungMenu.addAction(updateAction)
            for i in range(len(vorlagenMenuAction)):
                vorlagenMenu.addAction(vorlagenMenuAction[i])
            vorlagenMenu.addSeparator()
            vorlagenMenu.addAction(vorlagenMenuVorlagenVerwaltenAction)

            einstellungenMenu.addAction(einstellungenAllgemeinAction)
            einstellungenMenu.addAction(einstellungenGdtAction)
            ## Nur mit Lizenz
            einstellungenMenu.addAction(einstellungenErweiterungenAction)
            einstellungenMenu.addAction(einstellungenImportExportAction)
            ## /Nur mit Lizenz
            hilfeMenu.addAction(hilfeWikiAction)
            hilfeMenu.addSeparator()
            hilfeMenu.addAction(hilfeUpdateAction)
            hilfeMenu.addAction(hilfeAutoUpdateAction)
            hilfeMenu.addSeparator()
            hilfeMenu.addAction(hilfeUeberAction)
            hilfeMenu.addAction(hilfeEulaAction)
            hilfeMenu.addSeparator()
            hilfeMenu.addAction(hilfeLogExportieren)

            # Updateprüfung auf Github
            if self.autoupdate:
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

    def pushButtonPlanSendenDisable(self):
        self.pushButtonSenden.setEnabled(False)
    
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
            for i in range(self.maxDosenProEinheit):
                self.comboBoxDosisTeilbarkeit[i].setCurrentText("halbierbar")
        else:
            self.comboBoxDosisTeilbarkeit[0].setEnabled(False)
            self.comboBoxDosisTeilbarkeit[0].setCurrentText("nicht teilbar")
        self.lineEditDosisProEinheit[0].setText("")
        for i in range(1, self.maxDosenProEinheit):
            self.lineEditDosisProEinheit[i].setStyleSheet(self.styleSheetWeiss)
            if index == 0:
                self.lineEditDosisProEinheit[i].setEnabled(True)
                self.comboBoxDosisTeilbarkeit[i].setEnabled(True)
            else:
                self.lineEditDosisProEinheit[i].setText("")
                self.lineEditDosisProEinheit[i].setEnabled(False)
                self.comboBoxDosisTeilbarkeit[i].setEnabled(False)

    def buttonGroupEinAusschleichenClicked(self, id):
        for i in range(4):
            if id == 0:
                self.labelDannReduktion[i].setText("Dann Reduktion um")
            else:
                self.labelDannReduktion[i].setText("Dann Steigerung um")

    def pushButtonFormularZuruecksetzenClicked(self):
        self.dateEditAb.setDate(QDate().currentDate())
        self.radioButtonAusschleichen.setChecked(True)
        self.lineEditStartdosis.setText("")
        self.lineEditStartTage.setText("")
        for i in range(self.maxDosierungsplanAnweisungen):
            self.lineEditReduktionUm[i].setText("")
            self.lineEditTage[i].setText("")
            self.lineEditBis[i].setText("")
        self.checkBoxZweimalTaeglicheEinnahme.setChecked(False)
        self.radioButtonPrioritaetMorgens.setChecked(True)
    
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
                                fehler.append("Zieländerungsdosis " + str(i + 1) + " zu groß")
                            if reduktionsdosis > vorherigeDosis:
                                fehler.append("Änderungsdosis " + str(i + 1) + " zu groß")
                            if re.match(self.patternTage, self.lineEditTage[i].text()) == None or int(self.lineEditTage[i].text()) < 1:
                                fehler.append("Änderungszeitraum " + str(i + 1) + " ungültig")
                        else:
                            fehler.append("Zieländerungsdosis " + str(i + 1) + " ungültig")
                    else:
                        fehler.append("Änderungsdosis " + str(i + 1) + " ungültig")
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
                                fehler.append("Zieländerungsdosis " + str(i + 1) + " zu klein")
                            if re.match(self.patternTage, self.lineEditTage[i].text()) == None or int(self.lineEditTage[i].text()) < 1:
                                fehler.append("Änderungszeitraum " + str(i + 1) + " ungültig")
                        else:
                            fehler.append("Zieländerungsdosis " + str(i + 1) + " ungültig")
                    else:
                        fehler.append("Änderungsdosis " + str(i + 1) + " ungültig")
                    if len(fehler) > 0:
                        break
                    i += 1
        return fehler
    
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
                dosisElement.append(ElementTree.Element("dosis"))
                dosisElement[i].text = self.lineEditDosisProEinheit[i].text()
                dosenProEinheitElement.append(dosisElement[i])
                teilbarkeitElement.append(ElementTree.Element("teilbarkeit"))
                teilbarkeitElement[i].text = self.comboBoxDosisTeilbarkeit[i].currentText()
                teilbarkeitenElement.append(teilbarkeitElement[i])
            medikamentElement.append(nameElement)
            medikamentElement.append(einheitElement)
            medikamentElement.append(darreichungsformElement)
            medikamentElement.append(dosenProEinheitElement)
            medikamentElement.append(teilbarkeitenElement)
            einschleichenElement = ElementTree.Element("einschleichen")
            einschleichenElement.text = str(self.radioButtonEinschleichen.isChecked())
            startdosisElement = ElementTree.Element("startdosis")
            startdosisElement.text = self.lineEditStartdosis.text()
            startdauerElement = ElementTree.Element("startdauer")
            startdauerElement.text = self.lineEditStartTage.text()
            aenderungenElement = ElementTree.Element("aenderungen")
            aenderungElement = []
            aenderungUmElement = []
            tageElement = []
            bisElement = []
            for i in range(self.maxDosierungsplanAnweisungen):
                aenderungElement = ElementTree.Element("aenderung")
                aenderungUmElement = ElementTree.Element("aenderungUm")
                aenderungUmElement.text = self.lineEditReduktionUm[i].text().replace(",",".")
                tageElement = ElementTree.Element("tage")
                tageElement.text = self.lineEditTage[i].text()
                bisElement = ElementTree.Element("bis")
                bisElement.text = self.lineEditBis[i].text().replace(",",".")
                aenderungElement.append(aenderungUmElement)
                aenderungElement.append(tageElement)
                aenderungElement.append(bisElement)
                aenderungenElement.append(aenderungElement)
            zweimalTaeglicheEinnahmeElement = ElementTree.Element("zweimaltaeglicheeinnahme")
            zweimalTaeglicheEinnahmeElement.text = str(self.checkBoxZweimalTaeglicheEinnahme.isChecked())
            prioritaetElement = ElementTree.Element("prioritaet")
            prioritaetElement.text = "0"
            if self.radioButtonPrioritaetAbends.isChecked():
                prioritaetElement.text = "1"
            dosierungsplanElement.append(medikamentElement)
            dosierungsplanElement.append(einschleichenElement)
            dosierungsplanElement.append(startdosisElement)
            dosierungsplanElement.append(startdauerElement)
            dosierungsplanElement.append(aenderungenElement)
            dosierungsplanElement.append(zweimalTaeglicheEinnahmeElement)
            dosierungsplanElement.append(prioritaetElement)
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

    def getPlan(self):
        applikationsart = class_enums.Applikationsart.TABLETTE
        if self.comboBoxMediDarreichungsform.currentText() == "Tropfen":
            applikationsart = class_enums.Applikationsart.TROPFEN
        applikationen = []
        einheit = class_enums.Einheit(self.comboBoxMediEinheit.currentText())
        for i in range(self.maxDosenProEinheit):
            if self.lineEditDosisProEinheit[i].text() != "":
                wirkstoffmenge = self.lineEditDosisProEinheit[i].text().replace(",", ".")
                teilbarkeit = class_enums.Teilung.HALB
                if self.comboBoxDosisTeilbarkeit[i].currentText() == "viertelbar":
                    teilbarkeit = class_enums.Teilung.VIERTEL
                elif self.comboBoxDosisTeilbarkeit[i].currentText() == "nicht teilbar":
                    teilbarkeit = class_enums.Teilung.GANZ
                applikationen.append(class_tablette.Tablette(applikationsart, float(wirkstoffmenge), einheit, teilbarkeit))
        startDatum = datetime.date(self.dateEditAb.date().year(), self.dateEditAb.date().month(), self.dateEditAb.date().day())
        startDosis = float(self.lineEditStartdosis.text().replace(",", "."))
        startZeitraum = int(self.lineEditStartTage.text())
        anzahlTagesDosen = class_enums.AnzahlTagesdosen.EINMALTAEGLICH
        if self.checkBoxZweimalTaeglicheEinnahme.isChecked():
            anzahlTagesDosen = class_enums.AnzahlTagesdosen.ZWEIMALTAEGLICH
        prioritaet = 0
        if self.radioButtonPrioritaetAbends.isChecked():
            prioritaet = 1
        dosierungsplan = class_dosierungsplan.Dosierungsplan(applikationen, startDosis, startDatum, startZeitraum, anzahlTagesDosen, class_enums.DosisteilWichtung(prioritaet), self.radioButtonEinschleichen.isChecked())
        for i in range(self.maxDosierungsplanAnweisungen):
            if self.lineEditReduktionUm[i].isEnabled() and self.lineEditReduktionUm[i].text() != "":
                aenderungUm = float(self.lineEditReduktionUm[i].text().replace(",", "."))
                aenderungFuer = int(self.lineEditTage[i].text())
                aenderungAuf = float(self.lineEditBis[i].text().replace(",", "."))
                dosierungsplan.addAenderungsanweisung(aenderungUm, aenderungFuer, aenderungAuf)
        try:
            dosierungsplan.berechnePlan()
        except class_dosierungsplan.DosierungsplanFehler as e:
            if not self.dosierungsplanfehlerGemeldet:
                mb = QMessageBox(QMessageBox.Icon.Warning, "Hinweis von DosisGDT", "Dosierungsplanfehler: " + e.message, QMessageBox.StandardButton.Ok)
                mb.exec()
                self.dosierungsplanfehlerGemeldet = True
        return {"plan" : dosierungsplan, "applikationsart" : applikationsart, "einheit" : einheit}
    
    def pushButtonVorschauClicked(self):
        self.dosierungsplanfehlerGemeldet = False
        self.textEditVorschau.clear()
        fehler = self.formularPruefen()
        if len(fehler) != 0:
            text = ""
            for f in fehler:
                text += "\u26a0" + " " + f + "<br />"
            html = "<span style='font-weight:normal;color:rgb(200,0,0)'>" + text + "</span>"
            self.textEditVorschau.setHtml(html)
        else:
            dosierungsplan = self.getPlan()["plan"]
            applikationsart = self.getPlan()["applikationsart"]
            einheit = self.getPlan()["einheit"]
            if len(dosierungsplan.getDosierungsplan()) > 0:
                text = "<style>table.dosierungsplan { margin-top:6px;border-collapse:collapse } table.dosierungsplan td { padding:2px;border:1px solid rgb(0,0,0);font-weight:normal; } table.dosierungsplan td table {border-collapse:collapse;padding:0px } table.dosierungsplan td table td {border:none;padding:0px 2px 0px 2px; } </style>"
                text += "<div style='font-weight:bold'>" + self.lineEditMediName.text().strip() + "-Dosierungsplan:</div>"
                text += "<table class='dosierungsplan'>"
                if self.checkBoxZweimalTaeglicheEinnahme.isChecked():
                    text += "<tr><td><b>Von</b></td><td><b>Bis</b></td><td><b>Dosis</b></td><td><b>Einnahmevorschlag<br />morgens</b></td><td><b>Einnahmevorschlag<br />abends</b></td></tr>"
                else:
                    if self.radioButtonPrioritaetMorgens.isChecked():
                        text += "<tr><td><b>Von</b></td><td><b>Bis</b></td><td><b>Dosis</b></td><td><b>Einnahmevorschlag morgens</b></td></tr>"
                    else:
                        text += "<tr><td><b>Von</b></td><td><b>Bis</b></td><td><b>Dosis</b></td><td><b>Einnahmevorschlag abends</b></td></tr>"
                j = 0
                for zeile in dosierungsplan.getDosierungsplan():
                    dosierungsplanzeile = zeile.getDosierungsplanzeile()
                    evMorgens = MainWindow.getEinnahmevorschriftHtmlFormatiert(dosierungsplanzeile["einnahmevorschriftenMorgens"], einheit.value)
                    evAbends = MainWindow.getEinnahmevorschriftHtmlFormatiert(dosierungsplanzeile["einnahmevorschriftenAbends"], einheit.value)
                    if applikationsart == class_enums.Applikationsart.TROPFEN:
                            evMorgens = evMorgens.replace("x " + self.lineEditDosisProEinheit[0].text() + " " + einheit.value, "Tropfen")
                            evAbends = evAbends.replace("x " + self.lineEditDosisProEinheit[0].text() + " " + einheit.value, "Tropfen")
                    if j < len(dosierungsplan.getDosierungsplan()) - 1:
                        if self.checkBoxZweimalTaeglicheEinnahme.isChecked():
                            text += "<tr><td>" + dosierungsplanzeile["von"] + "</td><td>" + dosierungsplanzeile["bis"] + "</td><td>" + dosierungsplanzeile["tagesdosis"] + " " + einheit.value + "</td><td>" + evMorgens + "</td><td>" + evAbends + "</td></tr>"
                        else:
                            text += "<tr><td>" + dosierungsplanzeile["von"] + "</td><td>" + dosierungsplanzeile["bis"] + "</td><td>" + dosierungsplanzeile["tagesdosis"] + " " + einheit.value + "</td><td>" + evMorgens + "</td></tr>"
                    else:
                        text += "<tr><td colspan='2'>Ab " + dosierungsplanzeile["von"] + "</td>"
                        dosis = dosierungsplanzeile["tagesdosis"]
                        if dosierungsplanzeile["tagesdosis"][0:3] == "0,0":
                            colspan = "2"
                            if self.checkBoxZweimalTaeglicheEinnahme.isChecked():
                                colspan = "3"
                            dosis = "Keine Medikation mehr"
                            text += "<td colspan='" + colspan + "'>" + dosis + "</td>"
                        else:
                            if self.checkBoxZweimalTaeglicheEinnahme.isChecked():
                                text += "<td>" + dosis + "</td><td>" + evMorgens + "</td><td>" + evAbends + "</td></tr>"
                            else:
                                text += "<td>" + dosis + "</td><td>" + evMorgens + "</td></tr>"
                    j += 1
                text += "</table>"
                # Gesamtmengenangaben
                text += "<table style='margin-top:10px;border:none;border-collapse:collapse'>"
                text +=" <tr><td colspan='2'><b>" + self.lineEditMediName.text() + "-Verbrauch ab " + datetime.date.today().strftime("%d.%m.%Y") + ":</b></td></tr>"
                tablettenGesamtmengen = dosierungsplan.getApplikationsgesamtmengen()
                if gdttoolsL.GdtToolsLizenzschluessel.lizenzErteilt(self.lizenzschluessel, self.lanr, gdttoolsL.SoftwareId.DOSISGDT):
                    for tablette in tablettenGesamtmengen:
                        if applikationsart == class_enums.Applikationsart.TABLETTE:
                            text += "<tr style='font-weight:normal'><td>" + str(tablette).replace(".", ",") + " " + einheit.value + ":</td><td style='text-align:right'>" + str(tablettenGesamtmengen[tablette]).replace(".",",") + " Stück</td></tr>"
                        elif applikationsart == class_enums.Applikationsart.TROPFEN:
                            text += "<tr style='font-weight:normal'><td>" + str(tablettenGesamtmengen[tablette]).replace(".",",") + " Tropfen (" + str(tablettenGesamtmengen[tablette] * float(tablette)).replace(".",",") + " " + einheit.value + ")"
                else:
                    text+= "<tr><td colspan='2' style='font-weight:normal;color:rgb(200,0,0)'>Für diese Funktion ist eine gültige LANR/Lizenzschlüsselkombination erforderlich.</td></tr>"
                text += "</table>"
                if not self.dosierungsplanfehlerGemeldet:
                    self.textEditVorschau.clear()
                    self.textEditVorschau.setHtml(text)
                    self.pushButtonSenden.setEnabled(True)

    @staticmethod
    def getEinnahmevorschriftHtmlFormatiert(einnahmevorschriften:list, einheit:str):
        for i in range(len(einnahmevorschriften)):
            if einnahmevorschriften[i] != "":
                einnahmevorschriften[i] += " " + einheit
        formatiert = str.join(" und<br />", einnahmevorschriften)
        formatiert = formatiert.replace(",0", "")
        formatiert = formatiert.replace("0,5", "\u00bd")
        formatiert = formatiert.replace(",5", "\u00bd")
        formatiert = formatiert.replace("0,25", "\u00bc")
        formatiert = formatiert.replace(",25", "\u00bc")
        formatiert = formatiert.replace("0,75", "\u00be")
        formatiert = formatiert.replace(",75", "\u00be")
        return formatiert
    
    @staticmethod
    def getEinnahmevorschriftFpdfFormatiert(einnahmevorschriften:list, einheit:str):
        for i in range(len(einnahmevorschriften)):
            if einnahmevorschriften[i] != "":
                einnahmevorschriften[i] += " " + einheit
        formatiert = str.join(" und\n", einnahmevorschriften)
        formatiert = formatiert.replace(",0", "")
        formatiert = formatiert.replace("0,5", "\u00bd")
        formatiert = formatiert.replace(",5", "\u00bd")
        formatiert = formatiert.replace("0,25", "\u00bc")
        formatiert = formatiert.replace(",25", "\u00bc")
        formatiert = formatiert.replace("0,75", "\u00be")
        formatiert = formatiert.replace(",75", "\u00be")
        return formatiert


    def pushButtonSendenClicked(self):
        untdatDatetime = datetime.datetime.now()
        fehler = self.formularPruefen()
        medikament = None
        dp = None
        if len(fehler) == 0:
            dosierungsplan = self.getPlan()["plan"]
            applikationsart = self.getPlan()["applikationsart"]
            einheit = self.getPlan()["einheit"]
            # PDF erstellen
            darreichungsform = "Tabletten"
            if applikationsart == class_enums.Applikationsart.TROPFEN:
                darreichungsform = "Tropfen"
            pdf = FPDF()
            logger.logger.info("FPDF-Instanz erzeugt")
            pdf.add_page()
            pdf.set_font("helvetica", "B", 20)
            pdf.cell(0, 10, self.lineEditMediName.text() + "-Dosierungsplan", align="C", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("helvetica", "", 14)
            pdf.cell(0, 10, "für " + self.vorname + " " + self.nachname + " (*" + self.gebdat + ")", align="C", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("helvetica", "", 10)
            erstelltAmText = "Erstellt am " + untdatDatetime.strftime("%d.%m.%Y")
            if self.configIni["Allgemein"]["einrichtungaufpdf"] == "1":
                erstelltAmText += " von " + self.configIni["Allgemein"]["einrichtungsname"]
            pdf.cell(0,6, erstelltAmText, align="C", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("helvetica", "", 14)
            pdf.cell(0, 10, "", new_x="LMARGIN", new_y="NEXT")
            if self.radioButtonPrioritaetMorgens.isChecked():
                titelzeile = ["Von", "Bis", "Dosis", "Einnahmevorschlag morgens"]
            else:
                titelzeile = ["Von", "Bis", "Dosis", "Einnahmevorschlag abends"]
            colWidths = (15,15,20,50)
            if self.checkBoxZweimalTaeglicheEinnahme.isChecked():
                titelzeile = ["Von", "Bis", "Dosis", "Einnahmevorschlag morgens", "Einnahmevorschlag abends"]
                colWidths = (15,15,20,25,25)
            with pdf.table(v_align=enums.VAlign.T, line_height=1.5 * pdf.font_size, cell_fill_color=(230,230,230), cell_fill_mode="ROWS", col_widths=colWidths) as table: # type: ignore
                pdf.set_font("helvetica", "B", 12)
                row = table.row()
                for titel in titelzeile:
                    row.cell(text=titel)
                pdf.set_font("helvetica", "", 12)
                j = 0
                for zeile in dosierungsplan.getDosierungsplan():
                    dosierungsplanzeile = zeile.getDosierungsplanzeile()
                    evMorgens = MainWindow.getEinnahmevorschriftFpdfFormatiert(dosierungsplanzeile["einnahmevorschriftenMorgens"], einheit.value)
                    evAbends = MainWindow.getEinnahmevorschriftFpdfFormatiert(dosierungsplanzeile["einnahmevorschriftenAbends"], einheit.value)
                    if applikationsart == class_enums.Applikationsart.TROPFEN:
                            evMorgens = evMorgens.replace("x " + self.lineEditDosisProEinheit[0].text() + " " + einheit.value, "Tropfen")
                            evAbends = evAbends.replace("x " + self.lineEditDosisProEinheit[0].text() + " " + einheit.value, "Tropfen")
                    row = table.row()
                    if j < len(dosierungsplan.getDosierungsplan()) - 1:
                        row.cell(text=dosierungsplanzeile["von"])
                        row.cell(text=dosierungsplanzeile["bis"])
                        row.cell(text=dosierungsplanzeile["tagesdosis"] + " " + einheit.value)
                        row.cell(text=evMorgens)
                        if evAbends != "":
                            row.cell(text=evAbends)
                    else:
                        row.cell("Ab " + dosierungsplanzeile["von"], colspan=2)
                        dosis = dosierungsplanzeile["tagesdosis"] + " " + einheit.value
                        if dosierungsplanzeile["tagesdosis"][0:3] == "0,0":
                            dosis = "Keine Medikation mehr"
                            row.cell(dosis, colspan=2)
                        else:
                            row.cell(text=dosis)
                            row.cell(text=evMorgens)
                            if evAbends != "":
                                row.cell(text=evAbends)
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
            if self.configIni["Allgemein"]["pdferstellen"] == "1" and (gdttoolsL.GdtToolsLizenzschluessel.lizenzErteilt(self.lizenzschluessel, self.lanr, gdttoolsL.SoftwareId.DOSISGDT) or gdttoolsL.GdtToolsLizenzschluessel.lizenzErteilt(self.lizenzschluessel, self.lanr, gdttoolsL.SoftwareId.DOSISGDTPSEUDO)):
                gd.addZeile("6302", "dosierungsplan")
                gd.addZeile("6303", "pdf")
                gd.addZeile("6304", self.configIni["Allgemein"]["pdfbezeichnung"])
                gd.addZeile("6305", os.path.join(basedir, "pdf/dosierungsplan_temp.pdf"))
            gd.addZeile("6220", self.lineEditMediName.text() + "-Dosierungsplan")
            gd.addZeile("6226", str(len(dosierungsplan.getDosierungsplan())))
            for zeile in dosierungsplan.getDosierungsplan():
                dosierungsplanzeile = zeile.getDosierungsplanzeile()
                gd.addZeile("6228", dosierungsplanzeile["von"] + " - " + dosierungsplanzeile["bis"] + ": " + dosierungsplanzeile["tagesdosis"])
            gd.addZeile("6228", "")
            gd.addZeile("6228", self.lineEditMediName.text() + "-Verbrauch ab " + untdatDatetime.strftime("%d.%m.%Y") + ":")
            tablettenGesamtmengen = dosierungsplan.getApplikationsgesamtmengen()
            if gdttoolsL.GdtToolsLizenzschluessel.lizenzErteilt(self.lizenzschluessel, self.lanr, gdttoolsL.SoftwareId.DOSISGDT):
                for tablette in tablettenGesamtmengen:
                    if applikationsart == class_enums.Applikationsart.TABLETTE:
                        gd.addZeile("6228", tablette + " " + einheit.value + ": " + str(tablettenGesamtmengen[tablette]).replace(".",",") + " Stück")
                    elif applikationsart == class_enums.Applikationsart.TROPFEN:
                        gd.addZeile("6228",  str(tablettenGesamtmengen[tablette]).replace(".",",") + " Tropfen (" + str(tablettenGesamtmengen[tablette] * float(tablette)).replace(".",",") + " " + einheit.value + ")")
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
        
    def einstellungenAllgemein(self, checked, neustartfrage):
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
            self.configIni["Allgemein"]["updaterpfad"] = de.lineEditUpdaterPfad.text()
            self.configIni["Allgemein"]["autoupdate"] = str(de.checkBoxAutoUpdate.isChecked())  
            with open(os.path.join(self.configPath, "config.ini"), "w") as configfile:
                self.configIni.write(configfile)
            if neustartfrage:
                mb = QMessageBox(QMessageBox.Icon.Question, "Hinweis von DosisGDT", "Damit die Einstellungsänderungen wirksam werden, sollte DosisGDT neu gestartet werden.\nSoll DosisGDT jetzt neu gestartet werden?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                mb.setDefaultButton(QMessageBox.StandardButton.Yes)
                mb.button(QMessageBox.StandardButton.Yes).setText("Ja")
                mb.button(QMessageBox.StandardButton.No).setText("Nein")
                if mb.exec() == QMessageBox.StandardButton.Yes:
                    os.execl(sys.executable, __file__, *sys.argv)
        
    def einstellungenGdt(self, checked, neustartfrage):
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
    
    ## Nur mit Lizenz
    def einstellungenLanrLizenzschluessel(self, checked, neustartfrage):
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
    ## /Nur mit Lizenz

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
                
    # def updatePruefung(self, meldungNurWennUpdateVerfuegbar = False):
    #     response = requests.get("https://api.github.com/repos/retconx/dosisgdt/releases/latest")
    #     githubRelaseTag = response.json()["tag_name"]
    #     latestVersion = githubRelaseTag[1:] # ohne v
    #     if versionVeraltet(self.version, latestVersion):
    #         mb = QMessageBox(QMessageBox.Icon.Warning, "Hinweis von DosisGDT", "Die aktuellere DosisGDT-Version " + latestVersion + " ist auf <a href='https://github.com/retconx/dosisgdt/releases'>Github</a> verfügbar.", QMessageBox.StandardButton.Ok)
    #         mb.setTextFormat(Qt.TextFormat.RichText)
    #         mb.exec()
    #     elif not meldungNurWennUpdateVerfuegbar:
    #         mb = QMessageBox(QMessageBox.Icon.Warning, "Hinweis von DosisGDT", "Sie nutzen die aktuelle DosisGDT-Version.", QMessageBox.StandardButton.Ok)
    #         mb.exec()
    
    def autoUpdatePruefung(self, checked):
        self.autoupdate = checked
        self.configIni["Allgemein"]["autoupdate"] = str(checked)
        with open(os.path.join(self.configPath, "config.ini"), "w") as configfile:
            self.configIni.write(configfile)

    def updatePruefung(self, meldungNurWennUpdateVerfuegbar = False):
        logger.logger.info("Updateprüfung")
        response = requests.get("https://api.github.com/repos/retconx/dosisgdt/releases/latest")
        githubRelaseTag = response.json()["tag_name"]
        latestVersion = githubRelaseTag[1:] # ohne v
        if versionVeraltet(self.version, latestVersion):
            logger.logger.info("Bisher: " + self.version + ", neu: " + latestVersion)
            if os.path.exists(self.updaterpfad):
                mb = QMessageBox(QMessageBox.Icon.Question, "Hinweis von DosisGDT", "Die aktuellere DosisGDT-Version " + latestVersion + " ist auf Github verfügbar.\nSoll der GDT-Tools Updater geladen werden?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                mb.setDefaultButton(QMessageBox.StandardButton.Yes)
                mb.button(QMessageBox.StandardButton.Yes).setText("Ja")
                mb.button(QMessageBox.StandardButton.No).setText("Nein")
                if mb.exec() == QMessageBox.StandardButton.Yes:
                    logger.logger.info("Updater wird geladen")
                    atexit.register(self.updaterLaden)
                    sys.exit()
            else:
                mb = QMessageBox(QMessageBox.Icon.Warning, "Hinweis von DosisGDT", "Die aktuellere DosisGDT-Version " + latestVersion + " ist auf <a href='https://github.com/retconx/dosisgdt/releases'>Github</a> verfügbar.<br />Bitte beachten Sie auch die Möglichkeit, den Updateprozess mit dem <a href='https://github.com/retconx/gdttoolsupdater/wiki'>GDT-Tools Updater</a> zu automatisieren.", QMessageBox.StandardButton.Ok)
                mb.setTextFormat(Qt.TextFormat.RichText)
                mb.exec()
        elif not meldungNurWennUpdateVerfuegbar:
            mb = QMessageBox(QMessageBox.Icon.Warning, "Hinweis von DosisGDT", "Sie nutzen die aktuelle DosisGDT-Version.", QMessageBox.StandardButton.Ok)
            mb.exec()

    def updaterLaden(self):
        sex = sys.executable
        programmverzeichnis = ""
        logger.logger.info("sys.executable: " + sex)
        if "win32" in sys.platform:
            programmverzeichnis = sex[:sex.rfind("dosisgdt.exe")]
        elif "darwin" in sys.platform:
            programmverzeichnis = sex[:sex.find("DosisGDT.app")]
        elif "win32" in sys.platform:
            programmverzeichnis = sex[:sex.rfind("dosisgdt")]
        logger.logger.info("Programmverzeichnis: " + programmverzeichnis)
        try:
            if "win32" in sys.platform:
                subprocess.Popen([self.updaterpfad, "dosisgdt", self.version, programmverzeichnis], creationflags=subprocess.DETACHED_PROCESS) # type: ignore
            elif "darwin" in sys.platform:
                subprocess.Popen(["open", "-a", self.updaterpfad, "--args", "dosisgdt", self.version, programmverzeichnis])
            elif "linux" in sys.platform:
                subprocess.Popen([self.updaterpfad, "dosisgdt", self.version, programmverzeichnis])
        except Exception as e:
            mb = QMessageBox(QMessageBox.Icon.Warning, "Hinweis von DosisGDT", "Der GDT-Tools Updater konnte nicht gestartet werden", QMessageBox.StandardButton.Ok)
            logger.logger.error("Fehler beim Starten des GDT-Tools Updaters: " + str(e))
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
app.setWindowIcon(QIcon(os.path.join(basedir, "icons", "program.png")))
window = MainWindow()
window.show()

app.exec()
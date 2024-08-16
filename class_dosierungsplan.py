import class_tageseinnahme, class_enums, class_tablette, logger
import datetime


class DosierungsplanFehler(Exception):
    def __init__(self, message:str):
        self.message = message

    def __str__(self):
        return "Dosierungsplanfehler: " + self.message
    
class Dosierungsplan:
    def __init__(self, applikationsliste:list, startDosis:float, startDatum:datetime.date, startZeitraum:int, anzahlTagesdosen:class_enums.AnzahlTagesdosen, dosisTeilWichtung:class_enums.DosisteilWichtung, einschleichen:bool):
        self.applikationsliste = applikationsliste
        self.startDosis = startDosis
        self.startDatum = startDatum
        self.startZeitraum = startZeitraum
        self.aenderungsanweisungen = [] # Liste von {reduktionUm:float, reduktionFuer:int, reduktionAuf:float}
        self.anzahlTagesdosen = anzahlTagesdosen
        self.dosisTeilWichtung = dosisTeilWichtung
        self.einschleichen = einschleichen
        self.dosierungsplan = [] # Liste von Tageseinnahmen

    def getApplikationsliste(self):
        return self.applikationsliste
    
    def addAenderungsanweisung(self, aenderungUm:float, aenderungFuer:int, aenderungAuf:float):
        self.aenderungsanweisungen.append({"aenderungUm" : aenderungUm, "aenderungFuer" : aenderungFuer, "aenderungAuf" : aenderungAuf})

    def berechnePlan(self):
        self.dosierungsplan.clear()
        aktuellVon = self.startDatum
        aktuellBis = self.startDatum + datetime.timedelta(days=self.startZeitraum - 1)
        aktuelleDosis = self.startDosis
        bisherigeTagesdosen = [{"0" : 0} for i in range(self.anzahlTagesdosen.value)]
        tempEinnahmeVorschrift = Dosierungsplan.getNeueEinnahmevorschrift(self.applikationsliste, bisherigeTagesdosen, aktuelleDosis, True, self.dosisTeilWichtung)
        self.dosierungsplan.append(class_tageseinnahme.Dosisierungsplanzeile(aktuellVon, aktuellBis, tempEinnahmeVorschrift))
        for aenderungsanweisung in self.aenderungsanweisungen:
            if self.einschleichen:
                while aktuelleDosis < aenderungsanweisung["aenderungAuf"]:
                    aktuellVon = aktuellBis + datetime.timedelta(days=1)
                    aktuellBis = aktuellVon + datetime.timedelta(days=aenderungsanweisung["aenderungFuer"] - 1)
                    aktuelleDosis += aenderungsanweisung["aenderungUm"]
                    tempEinnahmeVorschrift = Dosierungsplan.getNeueEinnahmevorschrift(self.applikationsliste, tempEinnahmeVorschrift, aenderungsanweisung["aenderungUm"], self.einschleichen, self.dosisTeilWichtung)
                    self.dosierungsplan.append(class_tageseinnahme.Dosisierungsplanzeile(aktuellVon, aktuellBis, tempEinnahmeVorschrift))
            else:
                while aktuelleDosis > aenderungsanweisung["aenderungAuf"]:
                    aktuellVon = aktuellBis + datetime.timedelta(days=1)
                    aktuellBis = aktuellVon + datetime.timedelta(days=aenderungsanweisung["aenderungFuer"] - 1)
                    aktuelleDosis -= aenderungsanweisung["aenderungUm"]
                    tempEinnahmeVorschrift = Dosierungsplan.getNeueEinnahmevorschrift(self.applikationsliste, tempEinnahmeVorschrift, aenderungsanweisung["aenderungUm"], self.einschleichen, self.dosisTeilWichtung)
                    self.dosierungsplan.append(class_tageseinnahme.Dosisierungsplanzeile(aktuellVon, aktuellBis, tempEinnahmeVorschrift))

    def getDosierungsplan(self):
        return self.dosierungsplan
    
    def getApplikationsgesamtmengen(self):
        """
        Gibt die Applikationsgesamtmengen  zurück
        Return:
            Dict mit key: dosis (str) und value menge (float)
        """
        applikationen = {}
        for zeile in self.dosierungsplan:
            dosierungsplanzeile = zeile.getDosierungsplanzeile()
            evMorgens = dosierungsplanzeile["einnahmevorschriftenMorgens"]
            evAbends = dosierungsplanzeile["einnahmevorschriftenAbends"]
            tage = 0
            for evm in evMorgens:
                if " x " in evm:
                    tage = (zeile.getBis() - zeile.getVon()).days + 1
                    menge = evm.split(" x ")[0].replace(",", ".")
                    dosis = evm.split(" x ")[1].replace(",", ".")
                    if not dosis in applikationen:
                        applikationen[dosis] = float(menge) * tage
                    else:
                        applikationen[dosis] += float(menge) * tage
            for evm in evAbends:
                if " x " in evm:
                    menge = evm.split(" x ")[0].replace(",", ".")
                    dosis = evm.split(" x ")[1].replace(",", ".")
                    if not dosis in applikationen:
                        applikationen[dosis] = float(menge) * tage
                    else:
                        applikationen[dosis] += float(menge) * tage
        return applikationen



    @staticmethod
    def getNeueEinnahmevorschrift(zurVerfuegungStehendeApplikationen:list, bisherigeTagesdosen:list, aenderungUm:float, einschleichen:bool, dosisTeilwichtung:class_enums.DosisteilWichtung):
        """
        Gibt eine neue Einnahmevorschrift zurück
        Parameter: 
            zurVerfuegungStehendeApplikationen:list von class_applikation:Applikation
            bisherigeTagesdosen:dict von Tagesdosen mit key:Applikationsmenge, value: Anzahl
            aenderungUm:float
            einschleichen:bool
            dosisTeilwichtung:class_enums.DosisteilWichtung
        Return:
            list aus dicts mit key: Applikationsmenge, value: Anzahl
        Exception:
            DosierungsplanFehler
        """
        einschleichfaktor = 1
        if not einschleichen:
            einschleichfaktor = -1
        neueEinnahmevorschrift = []
        anzahlTagesdosen = len(bisherigeTagesdosen)
        if anzahlTagesdosen == 1:
            dosisTag = 0
            tagDosen = bisherigeTagesdosen[0]
            for tagDosis in tagDosen:
                menge = tagDosen[tagDosis]
                dosisTag += float(tagDosis) * menge
            dosisTag += aenderungUm * einschleichfaktor
            try:
                neueEinnahmevorschrift.append(class_tablette.getOptimaleMengen(dosisTag, zurVerfuegungStehendeApplikationen, False))
            except class_tablette.OptimaleMengenFehler as e:
                logger.logger.warning("Fehler #1 bei der Berechnung der Dosis " + str(dosisTag) + ": " + e.message)
                raise DosierungsplanFehler("Die Dosis " + str(dosisTag) + " kann aus den zur Verfügung stehenden Darreichungsformen nicht hergestellt werden.")
        elif anzahlTagesdosen == 2:
            # Gesamtdosen morgens und abends berechnen
            mitVielfachenEinerMenge = False
            dosisMorgens, dosisAbends = 0, 0
            morgensDosen, abendsDosen = bisherigeTagesdosen[0], bisherigeTagesdosen[1]
            for morgensDosis in morgensDosen:
                menge = morgensDosen[morgensDosis]
                dosisMorgens += float(morgensDosis) * menge
            for abendsDosis in abendsDosen:
                menge = abendsDosen[abendsDosis]
                dosisAbends += float(abendsDosis) * menge
            neueGesamtdosis = dosisMorgens + dosisAbends + aenderungUm * einschleichfaktor
            try:
                class_tablette.getOptimaleMengen(neueGesamtdosis / 2, zurVerfuegungStehendeApplikationen, False)
                dosisMorgens = neueGesamtdosis / 2
                dosisAbends = neueGesamtdosis / 2
            except class_tablette.OptimaleMengenFehler as e:
                logger.logger.warning("OptimaleMengenFehler Zweimalgabe 1: " + e.message)
                dosisGefunden = False
                for i in range(2):
                    mitVielfachenEinerMenge = i == 1
                    if mitVielfachenEinerMenge:
                        logger.logger.info("Mengenberechnung mit Vielfachen einer Menge, neue Tagesdosis: " + str(neueGesamtdosis))
                    moeglicheMengenSortiert = sorted(list(class_tablette.getMoeglicheMengenAusTablettenliste(zurVerfuegungStehendeApplikationen, mitVielfachenEinerMenge)), key=lambda m: float(m), reverse=True)
                    naechstKleinereMenge = []
                    try:
                        naechstKleinereMenge = class_tablette.getNaechstKleinereMengen(moeglicheMengenSortiert, neueGesamtdosis / 2)
                    except class_tablette.NaechstKleinereMengenFehler:
                        naechstKleinereMenge = ["0"] # Keine nächst kleinere Menge vorhanden
                    for menge in naechstKleinereMenge:
                        mengeFloat = float(menge)
                        if mengeFloat <= neueGesamtdosis / 2:
                            try:
                                uebrigeMenge = neueGesamtdosis - mengeFloat
                                class_tablette.getOptimaleMengen(uebrigeMenge, zurVerfuegungStehendeApplikationen, mitVielfachenEinerMenge)
                                if dosisTeilwichtung == class_enums.DosisteilWichtung.PRIOMORGENS:
                                    dosisMorgens = neueGesamtdosis - mengeFloat
                                    dosisAbends = mengeFloat
                                elif dosisTeilwichtung == class_enums.DosisteilWichtung.PRIOABENDS:
                                    dosisMorgens = mengeFloat
                                    dosisAbends = neueGesamtdosis - mengeFloat
                                # Prüfen, ob Dosisunterschied zwischen morgens und abends kleiner als die Hälfte der neuen Tagesdosis
                                if abs(dosisMorgens - dosisAbends) < neueGesamtdosis / 2:
                                    dosisGefunden = True
                                    break
                            except class_tablette.OptimaleMengenFehler as e:
                                logger.logger.warning("OptimaleMengenFehler Zweimalgabe 2: " + e.message)
                    if dosisGefunden:
                        break
            try:
                neueEinnahmevorschrift.append(class_tablette.getOptimaleMengen(dosisMorgens, zurVerfuegungStehendeApplikationen, mitVielfachenEinerMenge))
                neueEinnahmevorschrift.append(class_tablette.getOptimaleMengen(dosisAbends, zurVerfuegungStehendeApplikationen, mitVielfachenEinerMenge))
            except class_tablette.OptimaleMengenFehler as e:
                logger.logger.warning("Fehler #2 bei der Berechnung der Dosis " + str(neueGesamtdosis) + ": " + e.message)
                raise DosierungsplanFehler("Die Dosis " + str(neueGesamtdosis) + " kann aus den zur Verfügung stehenden Darreichungsformen nicht hergestellt werden.")
        else:
            raise DosierungsplanFehler("Ungültige Anzahl von Tagesdosen: " + str(anzahlTagesdosen))
        return neueEinnahmevorschrift


import class_medikament, logger
import datetime

class DosierungsfehlerException(Exception):
    def __init__(self, meldung:str, aenderungsanweisung:int):
        self.meldung = meldung
        self.aenderungsanweisung = aenderungsanweisung
    def __str__(self):
        return self.meldung
    
class Dosierungsplan():
    def __init__(self, einschleichen:bool, medikament:class_medikament.Medikament, maximaleTablettenzahlProEinheit: int, verteiltAufZweiDosen:bool, prioritaetMorgens:bool):
        self.einschleichen = einschleichen
        self.medikament = medikament
        self.maximaleTablettenzahlProEinheit = maximaleTablettenzahlProEinheit
        self.verteiltAufZweiDosen = verteiltAufZweiDosen
        self.prioritaetMorgens = prioritaetMorgens
    
    def set_start(self, datumTTMMJJJJ:str, dosis:float, tage:int):
        tag = int(datumTTMMJJJJ[0:2])
        monat = int(datumTTMMJJJJ[2:4])
        jahr = int(datumTTMMJJJJ[4:8])
        self.startdatum = datetime.date(jahr, monat, tag)
        self.startdosis = dosis
        self.startdauer = tage

    def set_aenderung(self, aenderungen:list):
        self.aenderungen = aenderungen

    def dosisIstHerstellbar(self, dosis:float):
        """
        Prüft, ob eine Tablettendosis mit den angegebenen Tablettendosierungen herstellbar ist
        Return:
            True oder False
        """
        herstellbar = False
        for verfuegbareDosis in self.medikament.get_verfuegbareDosen():
            herstellbar = (dosis % verfuegbareDosis == 0)
            if herstellbar:
                break
        return herstellbar
    
    def get_dosisMasken(self, wert1:str, wert2:str, anzahlDosen:int):
        """
        Gibt eine Bitmaske zurück, die für die Berechnung der Tablettendosis benötigt wird
        """
        maxWert = pow(2, anzahlDosen)            
        masken = []
        for i in range (maxWert):
            formatString = "{zahl:0" + str(anzahlDosen) + "b}"
            maske = formatString.format(zahl=i).replace("1", wert2)
            maske = maske.replace("0", wert1)
            masken.append(maske)
        return masken
    
    def get_tablettendosis(self, tagesdosis:float):
        """
        Gibt ein Dictionary mit jeweils key: Tablettendosierung / value: Tablettenanzahl für eine Tagesdosis zurück
        Return:
            Z. B. {"20" : 2, "5" : 2.5, "2" : 0}
        """
        maskenwerte = [(1,2), (1,4), (2,4)]
        tablettenverteilung = {}
        dosisGefunden = False
        for maskenwert in maskenwerte:
            dosismasken = self.get_dosisMasken(str(maskenwert[0]), str(maskenwert[1]), len(self.medikament.dosenProEinheit))
            for maske in dosismasken:
                dosenProEinheitMaskiert = []
                i = 0
                for maskenstelle in maske:
                    if maskenstelle == "1":
                        dosenProEinheitMaskiert.append(self.medikament.dosenProEinheit[i])
                    elif maskenstelle == "2" and (self.medikament.teilbarkeiten[i] == class_medikament.Teilbarkeit.HALBIERBAR or self.medikament.teilbarkeiten[i] == class_medikament.Teilbarkeit.VIERTELBAR):
                        dosenProEinheitMaskiert.append(self.medikament.dosenProEinheit[i] / 2)
                    elif maskenstelle == "4" and self.medikament.teilbarkeiten[i] == class_medikament.Teilbarkeit.VIERTELBAR:
                        dosenProEinheitMaskiert.append(self.medikament.dosenProEinheit[i] / 4)
                    i += 1
                if len(dosenProEinheitMaskiert) == len(self.medikament.dosenProEinheit):
                    tablettenverteilung.clear()
                    tempdosis = tagesdosis
                    i = 0
                    for dosisProEinheitMaskiert in dosenProEinheitMaskiert:
                        tablettenverteilung[str(self.medikament.dosenProEinheit[i])] = 0
                        if tempdosis / dosisProEinheitMaskiert >= 1 and tempdosis / self.medikament.dosenProEinheit[i] <= self.maximaleTablettenzahlProEinheit:
                            tablettenverteilung[str(self.medikament.dosenProEinheit[i])] += int(tempdosis / dosisProEinheitMaskiert) / (self.medikament.dosenProEinheit[i] / dosisProEinheitMaskiert)
                            tempdosis = tempdosis % dosisProEinheitMaskiert
                        i += 1
                    if tempdosis == 0:
                        dosisGefunden = True
                        break
                if dosisGefunden:
                    break
            if dosisGefunden:
                break        
        if not dosisGefunden:
            raise DosierungsfehlerException("Die Dosis " + str(tagesdosis).replace(".",",") + " " + self.medikament.einheit.value + " ist aufgrund der maximal zugelassenen " + self.medikament.darreichungsform.value + "-Anzahl (" + str(self.maximaleTablettenzahlProEinheit ) + ") nicht herstellbar.", -1)
        return tablettenverteilung

    # def get_DosisZweimalTaeglich(self, dosis:float, prioritaetMorgens:bool):
    #     morgensAbends = (0, 0)
    #     halbeDosis = dosis / 2
    #     if self.dosisIstHerstellbar(halbeDosis):
    #         morgensAbends = (halbeDosis, halbeDosis)
    #     else:
    #         tempDosis = halbeDosis
    #         restDosis = halbeDosis
    #         while (not self.dosisIstHerstellbar(tempDosis) or not self.dosisIstHerstellbar(restDosis)) and tempDosis >=0 and restDosis >=0:
    #             if prioritaetMorgens:
    #                 tempDosis += 0.01
    #             else:
    #                 tempDosis -= 0.01
    #             restDosis = dosis - tempDosis
    #         if tempDosis < 0 or restDosis < 0:
    #             morgensAbends = (-1, -1)
    #         morgensAbends = (tempDosis, restDosis)
    #         return morgensAbends

    def get_dosierungsplan(self):
        """
        Gibt einen Dosierungsplan als Dictionary mit den keys vonDatum, bisDatum, dosis und tabletten zurück, wobei tabletten wiederum ein von self.get_tablettendosis zurückgegebenes Dictionary ist
        """
        zeilen = []
        tempDosis = self.startdosis
        tempDauer = self. startdauer
        tempStartDatum = self.startdatum
        tempEndDatum = tempStartDatum + datetime.timedelta(days=tempDauer - 1)
        # Erste Zeile des Plans
        if self.dosisIstHerstellbar(tempDosis):
            tablettenverteilung = self.get_tablettendosis(tempDosis)
            zeilen.append({"vonDatum" : tempStartDatum.strftime("%d.%m.%Y"), "bisDatum" : tempEndDatum.strftime("%d.%m.%Y"), "dosis" : str(tempDosis).replace(".",",") + " " + str(self.medikament.einheit.value), "tabletten" : tablettenverteilung})
        else:
            logger.logger.info("Die Startdosis " + str(tempDosis).replace(".",",") + " ist nicht herstellbar.")
            raise DosierungsfehlerException("Die Startdosis " + str(tempDosis).replace(".",",") + " ist nicht herstellbar.", 0)
        
        i = 1
        # Weitere Zeilen des Plans
        for aenderung in self.aenderungen:
            if self.dosisIstHerstellbar(tempDosis + aenderung.aenderungsdosis):
                tempDauer = aenderung.tage
                tempZieldosis = aenderung.zieldosis
                #while tempDosis != tempZieldosis:
                while (aenderung.aenderungsdosis < 0 and tempDosis > tempZieldosis) or (aenderung.aenderungsdosis > 0 and tempDosis < tempZieldosis):
                    tempDosis = tempDosis + aenderung.aenderungsdosis
                    tempStartDatum = tempEndDatum + datetime.timedelta(days=1)
                    tempEndDatum = tempStartDatum + datetime.timedelta(days=tempDauer - 1)
                    tablettenverteilung = self.get_tablettendosis(tempDosis)
                    zeilen.append({"vonDatum" : tempStartDatum.strftime("%d.%m.%Y"), "bisDatum" : tempEndDatum.strftime("%d.%m.%Y"), "dosis" : str(tempDosis).replace(".",",") + " " + str(self.medikament.einheit.value), "tabletten" : tablettenverteilung})
            else:
                logger.logger.info("Dosierungsfehler: Die Dosis " + str(tempDosis + aenderung.aenderungsdosis).replace(".",",") + " " + self.medikament.einheit.value + " ist nicht herstellbar (Änderungsanweisung Nr. " + str(i) +").")
                raise DosierungsfehlerException("Die Dosis " + str(tempDosis + aenderung.aenderungsdosis).replace(".",",") + " " + self.medikament.einheit.value + " ist nicht herstellbar (Änderungsanweisung Nr. " + str(i) +").", i)
            i += 1
        return zeilen
    
    @staticmethod
    def getTablettenGesamtmengen(dosierungsplanzeilen, medikament, berechnungAusVergangenheit:bool):
        """
        Gibt den Medikamentenverbrauch eines Dosierungsplans zurück
        Parameter:
            Ergebnis von get_dosierungsplan
            berechnungAusVergangenheit:bool Wenn True, Berechung gegbenenfalls aus der Vergangenheit, wenn False, ab heute
        Return:
            Dictionary mit jeweils key: Medikamentendosis / value: Anzahl Tabletten/Tropfen
        """
        tablettenGesamtmengen = {}
        heute = datetime.date.today()
        for dosisProEinheit in medikament.dosenProEinheit:
            tablettenGesamtmengen[str(dosisProEinheit)] = 0
        for zeile in dosierungsplanzeilen:
            vonJahr = int(zeile["vonDatum"][6:10])
            vonMonat = int(zeile["vonDatum"][3:5])
            vonTag = int(zeile["vonDatum"][0:2])
            bisJahr = int(zeile["bisDatum"][6:10])
            bisMonat = int(zeile["bisDatum"][3:5])
            bisTag = int(zeile["bisDatum"][0:2])
            vonDatum = datetime.date(vonJahr, vonMonat, vonTag)
            bisDatum = datetime.date(bisJahr, bisMonat, bisTag)
            delta = bisDatum - vonDatum
            anzahlTage = delta.days + 1
            if not berechnungAusVergangenheit:
                if bisDatum < heute:
                    anzahlTage = 0
                elif vonDatum < heute:
                    anzahlTage -= (heute - bisDatum).days
            for tablette in zeile["tabletten"]:
                tablettenGesamtmengen[tablette] += zeile["tabletten"][tablette] * anzahlTage
        return tablettenGesamtmengen

class Aenderung():
    def __init__(self, aenderungsdosis:float, tage:int, zieldosis:float):
        self.aenderungsdosis = aenderungsdosis
        self.tage = tage
        self.zieldosis = zieldosis

if __name__ == "__main__":
    print("1")
    medikamentenname = "Prednisolon"
    einheit = class_medikament.Einheit.MG
    darreichungsform = class_medikament.Darreichungsform.TABLETTE
    dosenProEinheit = [20,5,2]
    teilbarkeiten = [class_medikament.Teilbarkeit.VIERTELBAR, class_medikament.Teilbarkeit.HALBIERBAR, class_medikament.Teilbarkeit.HALBIERBAR]
    einschleichen = False
    dosenProTag = 2
    startDatum = "15112023"
    startDosis = 25
    startDosisDauer = 7

    medikament = class_medikament.Medikament(medikamentenname, einheit, darreichungsform, dosenProEinheit, teilbarkeiten)
    dosierungsplan = Dosierungsplan(einschleichen, medikament, dosenProTag, False, True)
    dosierungsplan.set_start(startDatum, startDosis, startDosisDauer)
    aenderung = []
    aenderung.append(Aenderung(-2.5, 7, 10))
    aenderung.append(Aenderung(-1, 28, 0))
    dosierungsplan.set_aenderung(aenderung)

    for zeile in dosierungsplan.get_dosierungsplan():
        print(zeile)
    print(Dosierungsplan.getTablettenGesamtmengen(dosierungsplan.get_dosierungsplan(), medikament, False))
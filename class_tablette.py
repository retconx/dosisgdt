import class_enums
from enum import Enum
    
class NaechstKleinereMengenFehler(Exception):
    def __init__(self, message:str):
        self.message = message
    def __str__(self):
        return "Nächst kleinere Mengen-Fehler: " + self.message
    
class NaechstGroessereMengenFehler(Exception):
    def __init__(self, message:str):
        self.message = message
    def __str__(self):
        return "Nächst größere Mengen-Fehler: " + self.message
    
class OptimaleMengenFehler(Exception):
    def __init__(self, message:str):
        self.message = message
    def __str__(self):
        return "Optimale Mengen-Fehler: " + self.message

class Tablette:
    def __init__(self, art:class_enums.Applikationsart, wirkstoffmenge:float, einheit:class_enums.Einheit, teilbarkeit:class_enums.Teilung):
        self.art = art
        self.wirkstoffmenge = wirkstoffmenge
        self.einheit = einheit
        self.teilbarkeit = teilbarkeit
    
    def getArt(self):
        return self.art
    
    def getWirkstoffmenge(self):
        return self.wirkstoffmenge
    
    def getEinheit(self):
        return self.einheit
        
    def getTeilbarkeit(self):
        return self.teilbarkeit
    
    def getMoeglicheMengen(self, mitVielfachenEinerMenge:bool):
        """
        Gibt die möglichen Mengen einer Applikation unter Berücksichtigung der Teilbarkeit zurück
        Parameter: 
            mitVielfachenEinerMenge: Wenn True, werden auch Vielfache der Menge als möglich betrachtet
        Return: Liste möglicher Mengen (größte zuerst)
        """
        moeglicheMengen = []
        if mitVielfachenEinerMenge:
            step = 1 / self.teilbarkeit.value
            i = 2
            while i < 40:
                moeglicheMengen.append(i * self.wirkstoffmenge)
                if i < 5: # Bis zur 4-fachen Menge auch Viertel- und Halb-Vielfache
                    i += step
                else:
                    i += step
        moeglicheMengen.append(self.wirkstoffmenge)
        if self.teilbarkeit == class_enums.Teilung.VIERTEL:
            moeglicheMengen.append(self.wirkstoffmenge / class_enums.Teilung.HALB.value)
            moeglicheMengen.append(self.wirkstoffmenge / 4 * 3)
        if self.teilbarkeit != class_enums.Teilung.GANZ:
            moeglicheMengen.append(self.wirkstoffmenge / self.teilbarkeit.value)
        moeglicheMengen.sort(reverse=True)
        return moeglicheMengen
    
@staticmethod
def getMoeglicheMengenAusTablettenliste(tabletten:list, mitVielfachenEinerMenge:bool):
    """
    Gibt die möglichen Wirkstoffmengen einer Tablettenliste unter Berücksichtigung der Teilbarkeit zurück
    Parameter:
        tabletten: Tablette[]
        mitVielfachenEinerMenge: Wenn True, werden auch Vielfache der Menge als möglich betrachtet
    Return:
        Mengen-Dict (key: mögliche geteilte Menge, value:Liste ungeteilter Mengen)
    """
    moeglicheMengen = {}
    for tablette in tabletten:
        for menge in tablette.getMoeglicheMengen(mitVielfachenEinerMenge):
            key = str(menge).replace(",", ".").replace(".0", "")
            if not key in moeglicheMengen:
                moeglicheMengen[key] = []
            moeglicheMengen[key].append(tablette.getWirkstoffmenge())
        keysSortiert = sorted(list(moeglicheMengen), key=lambda k:float(k), reverse=True)
        moeglicheMengenSortiert = {k : moeglicheMengen[k] for k in keysSortiert}
    return moeglicheMengenSortiert

@staticmethod
def getNaechstKleinereMengen(mengenliste:list, testmenge:float):
    """
    Gibt die im Vergleich zu einer Testmenge nächst kleinere Menge einer Mengenliste zurück
    Parameter:
        mengenliste: Mengen-Liste
        testmenge: float
    Return:
        Liste der nächst kleineren Mengen (nächste zuerst)
    Exception:
        NaechstKleinereMengenFehler, wenn keine nächst kleinere Menge gefunden
    """
    differenzen = {} # key: menge, value: differenz zu testmenge
    for geteilteMenge in mengenliste:
        geteilteMengeFloat = float(geteilteMenge)
        diff = testmenge - geteilteMengeFloat
        if diff >= 0:
            differenzen[str(geteilteMenge).replace(",", ".").replace(".0", "")] = diff
    if len(differenzen.items()) == 0:
        raise NaechstKleinereMengenFehler("Für die Menge " + str(testmenge) + " gibt es keine nächst kleinere Menge.")
    return [k[0] for k in sorted(differenzen.items(), key=lambda v:v[1])]

@staticmethod
def mengenZurDosisherstellungVerfuegbar(mengenliste:list, pruefDosis, naechstKleinereMengeNummer:int):
    """
    Führt fogende Prüfungen durch:
        1. Exisitert für eine Prüfdosis eine nächst kleinere Menge innerhalb einer Mengenliste
        2. Existieren für die um die weiteren gefundenen nächst kleineren Mengen reduzierte Prüfdosen jeweils nächst kleinere Mengen innerhalb der Mengenliste, so dass die Dosis aus den zur Verfügung stehenden Mengen hergestellt werden kann
    Return: 
        0, wenn beide Prüfungen erfolgreich sind
        1, wenn die 1. Prüfung nicht erfolgreich ist
        2, wenn die 2. Prüfung nicht erfolgreich ist
    """
    ergebnis = 0
    tempdosis = float(pruefDosis)
    try:    
        nkm = float(getNaechstKleinereMengen(mengenliste, tempdosis)[naechstKleinereMengeNummer])
        tempdosis -= nkm
        if tempdosis > 0:
            try:
                while tempdosis > 0:
                    nkm = float(getNaechstKleinereMengen(mengenliste, tempdosis)[0])
                    tempdosis -= nkm
            except:
                ergebnis = 2
    except:
        ergebnis = 1
    return ergebnis

@staticmethod
def getOptimaleMengen(gewuenschteDosis:float, tabletten:list, mitVielfachenEinerMenge:bool):
    """
    Berechnet die optimalen Mengen einer zur Verfügung stehenden Tablettenliste um eine gewünschte Dosis zu erhalten
    Parameter:
        gewuenschte Dosis:float
        tabletten: Tablette-Liste
        mitVielfachenEinerMenge: Wenn True, werden auch Vielfache der Menge als möglich betrachtet
    Return:
        Dictionary mit key: Tabletten-Wirkstoffmenge, value: Anzahl
    Exception:
        OptimaleMengenFehler, falls gewünschte Dosis nicht hergestellt werden kann
    """
    if gewuenschteDosis == 0:
        return {"0" : 0}
    verfuegbareMengen = list(getMoeglicheMengenAusTablettenliste(tabletten, mitVielfachenEinerMenge))
    naechstKleinereMengeNummer = 0
    teileJeTablette = []
    tempDosis = gewuenschteDosis
    dosisGefunden = False
    try:
        while not dosisGefunden and naechstKleinereMengeNummer < len(getNaechstKleinereMengen(verfuegbareMengen, tempDosis)): 
            # logger: print("tempDosis: {0}, naechstKleinereMengeNummer: {1}, ergebnis: {2}".format(tempDosis, naechstKleinereMengeNummer, mengenVerfuegbar(verfuegbareMengen, tempDosis, naechstKleinereMengeNummer)))
            if mengenZurDosisherstellungVerfuegbar(verfuegbareMengen, tempDosis, naechstKleinereMengeNummer) == 0:
                # Liste optimaler Mengen füllen
                try:
                    nkm = getNaechstKleinereMengen(verfuegbareMengen, tempDosis)[naechstKleinereMengeNummer]
                except NaechstKleinereMengenFehler as e:
                    raise OptimaleMengenFehler("NächstkleinereMengenFehler in getOptimale Mengen 1: " + e.message)
                moeglicheMengen = getMoeglicheMengenAusTablettenliste(tabletten, mitVielfachenEinerMenge)[nkm]
                # logger: print("Tempdosis: {0}, nkm: {1}, moeglicheMengen: {2}".format(tempDosis, nkm, moeglicheMengen))
                if float(nkm) in moeglicheMengen: # Ganze Tablette für Menge vorhanden
                    teileJeTablette.append((1, moeglicheMengen[moeglicheMengen.index(float(nkm))]))
                else: # Keine ganze Tablette für Menge vorhanden
                    teileJeTablette.append((float(nkm) / moeglicheMengen[0], moeglicheMengen[0]))
                tempDosis -= float(nkm)
                naechstKleinereMengeNummer = 0
            else:
                naechstKleinereMengeNummer += 1
            if tempDosis == 0:
                dosisGefunden = True
    except NaechstKleinereMengenFehler as e:
        raise OptimaleMengenFehler("NächstkleinereMengenFehler in getOptimale Mengen 2: " + e.message)
    # Tablettenanzahl zusammenfassen
    optimaleMengen = {}
    for teilJeTablette in teileJeTablette:
        tablette = str(teilJeTablette[1])
        if not tablette in optimaleMengen:
            optimaleMengen[tablette] = teilJeTablette[0]
        else:
            optimaleMengen[tablette] += teilJeTablette[0]
    # Sortieren, größte Menge zuerst
    optimaleMengenSortiert = dict(sorted(optimaleMengen.items(), key=lambda tablette:float(tablette[0]), reverse=True))
    if dosisGefunden:
        return optimaleMengenSortiert
    raise OptimaleMengenFehler("Die Dosis " + str(gewuenschteDosis) + " kann aus den zur Verfügung stehenden Darreichungsformen nicht hergestellt werden.")



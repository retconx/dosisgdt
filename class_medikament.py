from enum import Enum

class Einheit(Enum):
    G = "g"
    MG = "mg"
    MIG = "µg"

class Teilbarkeit(Enum):
    NICHT_TEILBAR = "nicht teilbar"
    HALBIERBAR = "halbierbar"
    VIERTELBAR = "viertelbar"

class Darreichungsform(Enum):
    TABLETTE = "Tablette"
    TROPFEN = "Tropfen"

class Medikament():
    def __init__(self, name:str, einheit:Einheit, darreichungsform:Darreichungsform, dosenProEinheit:list, teilbarkeiten:list):
        self.name = name
        self.einheit = einheit
        self.darreichungsform = darreichungsform
        self.dosenProEinheit = dosenProEinheit
        self.dosenProEinheit.sort(reverse=True)
        self.teilbarkeiten = teilbarkeiten
    
    def get_verfuegbareDosen(self):
        verfuegbareDosen = []
        i = 0
        for dosis in self.dosenProEinheit:
            teiler = [1]
            if self.teilbarkeiten[i] == Teilbarkeit.HALBIERBAR:
                teiler.append(2)
            elif self.teilbarkeiten[i] == Teilbarkeit.VIERTELBAR:
                teiler.append(2)
                teiler.append(4)
            for t in teiler:
                verfuegbareDosen.append(dosis/t)
            i += 1
        verfuegbareDosen.sort(reverse=True)
        # Doppelte Dosen entfernen
        d = dict.fromkeys(verfuegbareDosen)
        verfuegbareDosen = list(d)

        return verfuegbareDosen
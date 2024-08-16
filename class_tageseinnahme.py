import datetime
import class_enums, class_tablette

class TageseinnahmeFehler(Exception):
    def __init__(self, message:str):
        self.message = message
    
    def __str__(self):
        return "Tageseinnahmefehler: " + self.message

class Dosisierungsplanzeile:
    def __init__(self, von:datetime.date, bis:datetime.date, einnahmevorschrift:list):
        self.von = von
        self.bis = bis
        self.einnahmevorschrift = einnahmevorschrift
        self.tagesdosis = 0
        for ev in self.einnahmevorschrift:
            for dosisApplikation in ev:
                menge = float(ev[dosisApplikation])
                self.tagesdosis += menge * float(dosisApplikation)
    
    def __str__(self):
        return  self.von.strftime("%d.%m.%Y") + " - " + self.bis.strftime("%d.%m.%Y") + ": " + str(self.tagesdosis) + " (" + str(self.einnahmevorschrift) + ")"
    
    def getVon(self):
        return self.von

    def getBis(self):
        return self.bis
    
    def getDosierungsplanzeile(self):
        """
        Gibt eine Dosierungsplanzeile als Dict zurück mit von : dd.mm.jjjj (str), bis : dd.mm.jjjj (str), tagesdosis : a,b (str), einnahmevorschriftenMorgens : a,b x c,v (str) (list), einnahmevorschriftenAbends: a,b x c,v (str) (list)
        """
        zeile = {}
        zeile["von"] = self.von.strftime("%d.%m.%Y")
        zeile["bis"] = self.bis.strftime("%d.%m.%Y")
        zeile["tagesdosis"] = str(self.tagesdosis).replace(".", ",")
        einnahmevorschriftenMorgens = []
        for dosisApplikation in self.einnahmevorschrift[0]:
            menge = self.einnahmevorschrift[0][dosisApplikation]
            if menge > 0:
                einnahmevorschriftenMorgens.append(str(menge).replace(".", ",") + " x " + dosisApplikation.replace(".", ","))
            else:
                einnahmevorschriftenMorgens.append("")
        einnahmevorschriftenAbends = []
        if len(self.einnahmevorschrift) == 2:
            for dosisApplikation in self.einnahmevorschrift[1]:
                menge = self.einnahmevorschrift[1][dosisApplikation]
                if menge > 0:
                    einnahmevorschriftenAbends.append(str(menge).replace(".", ",") + " x " + dosisApplikation.replace(".", ","))
                else:
                    einnahmevorschriftenAbends.append("")
        zeile["einnahmevorschriftenMorgens"] = einnahmevorschriftenMorgens
        zeile["einnahmevorschriftenAbends"] = einnahmevorschriftenAbends
        return zeile

    
    
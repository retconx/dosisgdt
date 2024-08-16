from enum import Enum

class Applikationsart(Enum):
    TROPFEN = "Tropfen"
    TABLETTE = "Tablette"

class Einheit(Enum):
    MIK = "µg"
    MG = "mg"
    G = "g"

class Teilung(Enum):
    VIERTEL = 4
    HALB = 2
    GANZ = 1

class Teilbarkeit(Enum):
    VIERTELBAR = "viertelbar"
    HALBIERBAR = "halbierbar"
    NICHT_TEILBAR = "nicht teilbar"


class AnzahlTagesdosen(Enum):
    EINMALTAEGLICH = 1
    ZWEIMALTAEGLICH = 2
    
class DosisteilWichtung(Enum):
    PRIOMORGENS = 0
    PRIOABENDS = 1
    
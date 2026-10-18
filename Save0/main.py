import go
import Boden
import Saat
import Plantage
import Schatz
import Schwarm


while (True):
	for i in range(2200):
		if spawn_drone(Schwarm.Reihe):
			move(East)
	Boden.Ernte()
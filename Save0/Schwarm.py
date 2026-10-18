import go
import Boden
import Saat


def Reihe():
	for i in range(get_world_size()):
		Boden.Pflug()
		Saat.Kürbis()
		go.up()
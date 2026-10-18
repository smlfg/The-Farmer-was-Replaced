import Boden
import Saat

def Baum():
	Boden.Wasser()
	plant(Entities.Tree)
	
	
def Möhren():
	Boden.Pflug()
	Boden.Wasser()
	plant(Entities.Carrot)
	
def Kürbis():
	Boden.Wasser()
	plant(Entities.Pumpkin)
	
def Kaktus():
	Boden.Pflug()
	plant(Entities.Cactus)
	
def Gold():
	plant(Entities.Bush)
	use_item(Items.Weird_Substance,2)
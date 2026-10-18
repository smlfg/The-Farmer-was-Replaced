import Saat
import Boden
import go
def Ernte():
	if can_harvest():
		harvest()
def Wasser():
		if get_water() <= 0.1:
			use_item(Items.Water)
def Pflug():
	if get_ground_type()==Grounds.Grassland:
		till()
def Tot():
	if get_entity_type()==Entities.Dead_Pumpkin:
		use_item(Items.Fertilizer) 
		Boden.Wasser()
		Saat.Kürbis()
		

def Gras():
	if get_ground_type()==Grounds.Soil:
		till()
		
def Kürbis():
	for i in range(12):
		Pflug()
		Saat.Kürbis()
		go.up()
		
	for i in range(random()):
		Saat.Kürbis()
		Boden.Tot()
		go.right()

		
		
import go
import Boden
import Saat
def KundB():
	x = get_pos_x()
	y = get_pos_y()
			
	go.left()
	print(x)
			
	Boden.Ernte()
			
			
	if Boden.Tot():
		Saat.Kürbis()
			
	for i in range(7):
		Boden.Ernte()
		if get_pos_x()%2==0 and get_pos_y()%2==0: 
			Boden.Ernte()
			Saat.Baum()
			go.up()
		if get_pos_x()%2==1 and get_pos_y()%2==1: 
			Boden.Ernte()
			Saat.Baum()
			go.up()
		Boden.Ernte()
		Saat.Möhren()
		go.up()
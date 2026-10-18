def dd():
	for i in range(1600):
		
		go.left()
		
		for i in range(16):
			for i in range(16):
				go.right()
				Saat.Kürbis()
			
			go.down()
			
	
spawn_drone(dd)
Boden.Ernte()
while(True):
	go.left()
	for i in range(get_world_size()):
		Saat.Kürbis()
		go.up()
		
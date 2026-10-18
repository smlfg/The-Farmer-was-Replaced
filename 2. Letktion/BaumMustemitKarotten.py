while True:
	for i in range(get_world_size()):
		for j in range(get_world_size()//2):
			
			use_item(Items.Water)
			harvest()
			plant(Entities.Tree)
			move(North)
			harvest()
			if plant(Entities.Carrot) != True:
				till()
			plant(Entities.Carrot)
			move(North)
		move(East)
		for k in range(get_world_size()):
			harvest()
			move(North)
		move(East)
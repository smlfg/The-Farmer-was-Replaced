def BaumMuster()
	
	for i in range(get_world_size()):
		move(North)
		harvest()
		if get_pos_x() % 2 == 0 and get_pos_y() % 2== 0:
			use_item(Items.Water)
			plant(Entities.Tree)
		else:
			plant(Entities.Grass)
	move(East)
	if get_pos_x()==0 and get_pos_y()==0:
		use_item(Items.Water)
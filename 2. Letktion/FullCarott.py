while True:
	for i in range(get_world_size()):
		for j in range(get_world_size()):
			if can_harvest():
				harvest()
			if get_ground_type()==Grounds.Grassland:
				till()
			if j %2 ==0:
				plant(Entities.Carrot)
				move(North)
			elif get_pos_y()%2==0:
				use_item(Items.Water)
				plant(Entities.Tree)
				move(North)
		move(East)
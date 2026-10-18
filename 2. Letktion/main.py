
for i in range(get_world_size()):
	for j in range(get_world_size()):
		move(North)
		if can_harvest():
			harvest()
			if get_ground_type()==Grounds.Grassland:
				till()
			
		
	move(East)

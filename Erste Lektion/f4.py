def full_harvest():
	move(East)
	for i in range(get_world_size()):
		harvest()
		move(North)
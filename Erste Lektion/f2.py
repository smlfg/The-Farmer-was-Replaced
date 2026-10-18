def full_Bush():
	move(East)
	for i in range(get_world_size()):
		harvest()
		plant(Entities.Carrot)
		move(North)
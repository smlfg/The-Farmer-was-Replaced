def full_till():
	move(East)
	for i in range(get_world_size()):
		till()
		move(North)
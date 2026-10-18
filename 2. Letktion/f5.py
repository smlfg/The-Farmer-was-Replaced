def do():
	if get_entity_type() == Entities.Dead_Pumpkin:
		till()
		till()
		use_item(Items.Water)
		plant(Entities.Pumpkin)
		use_item(Items.Fertilizer)

	if get_ground_type() == Grounds.Grassland:
		till()
	plant(Entities.Pumpkin)
	
counter = 0
while True:


	for i in range(get_world_size()):
		move(North)
		if get_pos_y() % 2 == 0:
			do()
		else:
			move(East)
			do()
			move(West)
	move(East)

	for i in range(get_world_size()):
		do()

	
	for j in range(WORLD):
		for i in range(WORLD):
			move(North)
			if can_harvest():
				war x * x also feld size war. dann kännen wir ernenten
				wie mache ich den comunter logkisch 
				wir platziere ihc ihn an die richtige stelle
		move(East)


	
			

	
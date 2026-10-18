def saat():
	if get_ground_type() == Grounds.Grassland:
		till()
	for i in range(get_world_size()):
		plant(Entities.Pumpkin)
		move(North)
	for i in range(get_world_size()):
		plant(Entities.Pumpkin)
		move(East)
	for i in range(get_world_size()):	
		plant(Entities.Pumpkin)
		move(South)
	for i in range(get_world_size()):
		plant(Entities.Pumpkin)
		move(West)

def check():
	if get_entity_type() == Entities.Dead_Pumpkin:		
		till()
		tIll()
		plant(Entities.Pumpkin)
	move(North)
	if get_entity_type() == Entities.Dead_Pumpkin:		
		till()
		tIll()
		plant(Entities.Pumpkin)
	move(East)
	if get_entity_type() == Entities.Dead_Pumpkin:		
		till()
		tIll()
		plant(Entities.Pumpkin)
	move(South)
	if get_entity_type() == Entities.Dead_Pumpkin:		
		till()
		till()
		plant(Entities.Pumpkin)
	move(West)
	return True

while True:
	saat()
	if check():
		harvest()	
	
	


	

		
import Boden
import Saat
def up():
	move(North)

def down():
	move(South)
	
def left():
	move(West)
	
def right():
	move(East)
	
def Reihe():
	for i in range (get_world_size()):
		move(South)
		Boden.Ernte()
	move(East)
from shutil import move


WORLD = get_world_size()

def navigation_grundgeruest():
	# Äußerer Loop: Jede Reihe durchgehen (Y-Achse)
	for zeile in range(WORLD):

		# Innerer Loop: Die Schritte nach Osten machen (X-Achse)
		for schritt in range(WORLD - 1):
			move(East)             # Wir wandern nach Osten

		# Jetzt steht er am rechten Rand. Zurück zum Start der Reihe!
		for zurueck in range(WORLD - 1):
			move(West)

		# Und jetzt eine Zeile hochschalten für den nächsten Rundenlauf:
		if zeile < WORLD - 1:
			move(North)

def navigation_schachbrett():
	for zeile in range(WORLD):             # 1. Die Reihe starten (Y-Achse)
		for schritt in range(WORLD - 1):   # 2. Die Schritte nach Osten (X-Achse)
			move(East)                     # <- Das muss hier drin sein!

		# 3. Zurück nach links, bevor wir hochschalten:
		for x in range(WORLD - 1):
			move(West)
			
		# 4. Jetzt erst hochschalten:
		if zeile < WORLD - 1:
			move(North)


# Das Hauptprogramm:
clear()
navigation_grundgeruest()
print("Navigation fertig!")
navigation_schachbrett()

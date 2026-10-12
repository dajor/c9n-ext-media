# c9n-ext-media 1.0.0

ffmpeg, Tesseract (Deutsch, Englisch), poppler und qpdf als Erweiterung für c9n. Texterkennung für Wissens-Screenshots und die Medienwerkzeuge der Agenten laufen über diesen Dienst, sobald die Erweiterung aktiv ist. Verlangt c9n mit Erweiterungs-Schnittstelle 1 (ab c9n 0.9.16).

Der Dienst hat keinen veröffentlichten Anschluss und ist nur unter einem geheimen Pfad erreichbar, den c9n beim Aktivieren erzeugt. Er arbeitet auf dem gemeinsamen Datenordner von c9n; Pfade außerhalb davon, „..“ und Netzwerk-Eingaben weist er ab, und nur die aufgeführten Werkzeuge laufen.

Grenze: Werkzeuge sehen nur Dateien im gemeinsamen Datenordner, nicht den Temp-Ordner eines Skript-Containers. Die Ausgabe eines Aufrufs ist auf 8 MB begrenzt; größere Ergebnisse gehören in eine Datei.

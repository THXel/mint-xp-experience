# Explorer 1.6: Dateiaktionen und Netzwerk

Stand: 2026-10-04, Linux Mint 22.3 Cinnamon 6.6.9, GTK 3 / GVfs 1.54.4.

## Bedienung

- Entf verschiebt in normalen Ordnern in den Papierkorb. Im Papierkorb löscht Entf endgültig, jeweils mit Bestätigung. Umschalt+Entf löscht in normalen Ordnern nach Bestätigung endgültig.
- Rechtsklick im Papierkorb bietet Wiederherstellen und Endgültig löschen. Auf dem Hintergrund, der Papierkorb-Seitenleistenverknüpfung und dem Baumknoten gibt es Papierkorb leeren. Neue Einträge nach der Bestätigungsvorbereitung werden nicht mitgelöscht.
- Strg+C/X/V/A: Kopieren, Ausschneiden, Einfügen, alles auswählen. Strg+Z nimmt zusammengehörige Dateivorgänge gemeinsam zurück. F2 benennt um. Strg+Umschalt+N erstellt einen Ordner.
- Strg+N/W: neues Fenster/schließen; Strg+L: Adresse; Strg+H: versteckte Dateien; F5/Strg+R: aktualisieren; Alt+Links/Rechts/Oben: Navigation; Alt+Enter: Eigenschaften; Umschalt+F10: Kontextmenü.
- Textfelder behalten ihre eigenen Text-Tastenkürzel. Die Dateiaktionen beziehen sich auf die Auswahl im Hauptbereich; der Ordnerbaum besitzt Navigation und Orts-Kontextmenüs, aber noch keine vollständigen Dateiaktionen per Tastatur.
- Unter Extras bzw. in der Netzwerkumgebung: Mit Server verbinden. Adresse beispielsweise smb://server/freigabe oder sftp://server. Zugangsdaten nur im nativen Anmeldedialog; Passwörter in Adressen werden abgewiesen.
- Verbundene Netzwerkfreigaben erscheinen im Arbeitsplatz. Verbindung trennen meldet eine Freigabe regulär über GVfs ab; offene Dateien vorher schließen.

## Geprüft

30 Dateioperations- und Regressionstests in einer Desktop-Sitzung; 14 Gruppen echter GTK/X11-Tastatureingaben und Dialogaktionen. Dazu Drag-and-drop zwischen zwei Fenstern, Umschalt-Verschieben/Rückgängig, Ablage im Ordnerbaum, Ordnerüberwachung, gespeicherte Ansichten, Konflikt- und Suchdialoge, MIME-Kontextmenüs, Eigenschaften sowie Text/PDF/Video-Vorschau.

Ein echter SMB-Server wurde mit gespeicherter Systemanmeldung verbunden. Serveransicht -> Freigabe, Baumansicht und Erstellen/Kopieren/Umbenennen/Lesen/Rückgängig/Löschen funktionierten in einem ausschließlich dafür erzeugten Testordner. Dieser wurde entfernt. Kein frischer Passwortdialog war nötig; andere Netzwerkprotokolle wurden nicht live geprüft. GVfs-Backends müssen installiert sein.

Papierkorb leeren wurde mit der echten Bestätigungs- und Löschfunktion auf eine isolierte Liste eigener Testeinträge begrenzt geprüft, einschließlich eines Ordners mit Unterdatei. Bestehende persönliche Papierkorbeinträge wurden nicht geleert. Rückgängig prüft Ziel-Metadaten auf zwischenzeitliche Änderungen; dauerhaftes Löschen und Papierkorb leeren sind nicht rückgängig machbar. Die Theme-Sicherung ist keine Sicherung gelöschter Benutzerdaten.

## Grenzen

Rückgängig gilt innerhalb der laufenden Explorer-Sitzung, nicht nach Neustart; kein Wiederholen/Redo. Bei Namenskonflikten: beide behalten, überspringen oder abbrechen; kein automatisches Überschreiben. Papierkorb-Unterstützung auf Netzwerkfreigaben hängt vom Server/Backend ab. SFTP, FTP und WebDAV nutzen GVfs, sind durch diesen SMB-Test aber nicht als getestet ausgewiesen. USB-Auswerfen und Verbindungsabbruch während großer Transfers wurden nicht live geprüft.

Die portable Regression ist mit `python3 -B -m unittest discover -s tests -v` ausführbar. Papierkorb-Integration nur ausdrücklich in einer GVfs-Desktop-Sitzung aktivieren: `MINTXP_TEST_TRASH=1 python3 -B -m unittest discover -s tests -p test_explorer.py -v`. Sie erzeugt eigene Testdaten und löscht nur diese.

Technische Referenzen: [GIO target-uri](https://docs.gtk.org/gio/const.FILE_ATTRIBUTE_STANDARD_TARGET_URI.html), [GIO mount_enclosing_volume](https://docs.gtk.org/gio/method.File.mount_enclosing_volume.html), [GIO delete](https://docs.gtk.org/gio/method.File.delete.html).

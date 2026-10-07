Hinweis ab Preview 30: Es werden keine Sounds mitgeliefert. Ohne eigenes Pack bleiben die vorhandenen Sounds unverändert. ISO, Ordner und Archive lassen sich später in den Einstellungen importieren. Dort kann zwischen mitgelieferten und importierten Icons gewechselt werden.

# DEB installieren und selbst testen

1. `mint-xp-experience_0.1.0~preview.38_all.deb` auf den VM-Desktop kopieren.
2. Doppelklicken, im Mint-Paketinstaller „Paket installieren“ wählen und das
   VM-Passwort eingeben. Alternativ im Verzeichnis der Datei:

```sh
sudo apt install ./mint-xp-experience_0.1.0~preview.38_all.deb
```

3. Der Einrichtungsassistent öffnet sich automatisch in der aktiven Desktop-Sitzung. Falls der Sitzungsdienst nicht erreichbar ist, erscheint er beim nächsten Cinnamon-Login. Er bleibt auch im Startmenü erreichbar. Der Paketinstaller aktiviert
   noch kein Theme. Zuerst Sprache und Medien auf Willkommen wählen; danach werden die Bestandteile freigegeben.
   Wallpaper, Startmenü, Taskleiste, Tray und Welcome sind ausdrücklich wählbar.
4. Vorschau prüfen und anwenden. Erst wird der aktuelle Desktop gesichert.
   Die Abschlussseite nennt aktive/abgewählte Bestandteile und den Sicherungsort.
5. Ab-/anmelden, wenn die Abschlussseite es empfiehlt. Boot/Login wird bei Auswahl bereits am Anfang der Installation mit einer Administratorabfrage eingerichtet.
   WAVs als Ordner/Archiv importieren. Bei verschiedenen Treffern vor der
   Auswahl mit **Anhören** vergleichen. Abbrechen beendet die Vorschau.
7. Erstinstallation, Kategorien/Hotkeys, kleine Fenster, Skalierung und
   Tastaturbedienung testen. Anschließend bei Bedarf unter **Deinstallation**
   den ursprünglichen Desktop wiederherstellen. Danach kann das DEB weg:

```sh
sudo apt remove mint-xp-experience
```

Die Paketentfernung alleine setzt keine persönlichen Einstellungen zurück.
Sie löscht keine privaten Backups oder separat installierten Spiele. Die lokale
Verwaltung und Rettungskopie bleiben nach einer Theme-Installation verfügbar,
auch wenn das DEB bereits entfernt wurde. DEB-Updates werden erst nach erneutem
Anwenden im Assistenten auf das persönliche Theme übertragen.

Unterstützt: Linux Mint 22.3 Cinnamon 6.6.x mit X11. Andere Mint-/Cinnamon-Versionen
sind nicht freigegeben. Das Basispaket ist architekturunabhängig; die optionalen
Legacy-Spiele unterstützen derzeit x86_64. Neue Fachtexte außerhalb DE/EN haben
englische Rückfalltexte. Backup/Undo ersetzt keine vollständige Systemsicherung.

Für Rückmeldungen: Version, genaue Schritte, erwartetes/tatsächliches Ergebnis,
Screenshot ohne private Inhalte und optional Diagnoseexport aus Installationsstatus.
Keine Sicherungsarchive oder Passwörter weitergeben.

## Einrichtung und spätere Verwaltung

`mint-xp-experience setup` öffnet den Einrichtungsassistenten;
`mint-xp-experience settings` öffnet die Theme-Einstellungen mit Sicherungen
und Deinstallation. Ohne Argument entscheidet der Installationszustand.
Unter Willkommen stehen die Bestandteile direkt unter den Schaltflächen
„Alles installieren“ und „Ausgewählte installieren“. Beide zeigen zuerst
eine Bestätigung und sichern den bisherigen Zustand vor der Änderung.
Sprachwechsel erhalten die Seite und Auswahl. Die neue Medienauswahl und die zugehörigen Installationsschaltflächen sind in allen 14 auswählbaren Sprachen übersetzt. Ältere Dialoge und technische Fehlermeldungen enthalten teilweise noch englische Rückfalltexte; eine vollständige Übersetzung der gesamten Anwendung wird nicht behauptet.

Die Spiele-Einbindung darf auf einem frischen Rechner leer sein. Spiele und
Paint werden unter Spiele und Zubehör separat mit Quellen- und Lizenzhinweisen
installiert. „Alles installieren“ wählt alle aufgeführten Desktop-Bestandteile, die vier Spiele/Zubehör-Einträge sowie Boot und Anmeldung. Die Systemoptik wird zu Beginn mit einer Administratorabfrage und eigener Sicherung eingerichtet. Bei Abbruch starten weder Desktop-Änderungen noch Downloads. Der Gesamtfortschritt zählt abgeschlossene Schritte; Dateikopien und Downloads setzen ihn nicht zurück. Originale Microsoft-Sounds und -Icons werden nicht heruntergeladen. Abgebrochene Zusatzschritte werden am Ende als unvollständig ausgewiesen.

Der automatische Paketstart nutzt aktive lokale grafische Benutzersitzungen
und deren bestehenden systemd-Benutzerdienst. Unter SSH oder ohne grafische
Sitzung startet keine Root-Oberfläche; Cinnamon-Autostart dient als Ausweichweg.
Bereits eingerichtete Benutzer werden nicht erneut aufgefordert. Nach dem
Schließen öffnet sich dieselbe Version nicht bei jeder Anmeldung erneut.

## Kompakte Einrichtung ab Preview 20

Die Startseite zeigt die Medienauswahl direkt unter der Sprache und danach alle Bestandteile in drei Gruppen. ISO und Archive werden dort eingelesen; Sounds und weitere Optionen bleiben zusätzlich auf eigenen Seiten erreichbar. Bei 1020×670 Pixeln passen diese vier Einrichtungsseiten ohne Scrollen; bei sehr kleinen Fenstern und größerer Schrift bleibt Scrollen als Ausweichmöglichkeit erhalten. Importierte Dateien bleiben privat; siehe ISO-IMPORT.de.md.

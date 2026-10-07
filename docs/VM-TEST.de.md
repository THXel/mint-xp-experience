# Abnahme in einer frischen Linux-Mint-VM

Ziel: Linux Mint 22.3 Cinnamon 6.6 mit X11. Diese Liste ist ein vorbereiteter
Prüfplan, kein Bericht bereits durchgeführter VM-Tests. Ergebnisse pro Zeile mit
**bestanden / Fehler / nicht geprüft** sowie bei Fehlern Reproduktionsschritten
festhalten. Nur das öffentliche Release in die VM kopieren, keine Host-Backups.

## 1. Ausgangszustand

- Mint vollständig installieren, anmelden und die Standardsitzung prüfen.
- Vor der ersten XP-Installation in VirtualBox einen Snapshot „Vor Mint XP“
  anlegen. Paketbackup und VM-Snapshot ergänzen sich; beide behalten.
- Release-Archiv plus zugehörige SHA256SUMS übertragen. Im Übertragungsordner:

```sh
sha256sum -c SHA256SUMS
```

Für den DEB-Test zuerst [DEB-Anleitung](DEB.de.md) verwenden. Für den Quellarchiv-Test: Archiv entpacken, ein Terminal im Paketordner öffnen:

```sh
python3 -B tools/vm_check.py
python3 -B launch.py
```

Die Vorprüfung liest Voraussetzungen; sie installiert nichts. Erst bei fehlenden
Voraussetzungen gezielt nachbessern. Der Benutzer-Installer läuft ohne sudo.

## 2. Benutzerinstallation und Darstellung

- Assistent: Systemsprache, manuelle Sprachwahl, Komponenten-Vorschau und Abbruch.
- Zuerst GTK, Cinnamon, Cursor, Fonts, Explorer und Systemsteuerung auswählen;
  danach Startmenü, Taskleiste und einklappbaren Infobereich gezielt aktivieren.
- Bestätigen, dass das Original-Backup vorhanden ist; `mint-xp-experience verify`.
- Ab-/anmelden, Startmenü öffnen, Alle Programme/Kategorien, letzte Programme,
  Terminal und Systeminformationen prüfen. Schließen bleibt im Taskleistenmenü unten.
- Startknopf und Tray in Normal-, Hover-, Fokus- und geöffnetem Zustand prüfen.
- Fenster maximieren, Monitor-/Fenstergröße der VM ändern und passende größere
  Skalierung in Mint testen. Keine abgeschnittenen Pfeile, Menüs oder Dialoge.
- Passwortdialog, Ausschalten-Dialog und Abbrechen prüfen, ohne vorzeitig zu beenden.

## 3. Infobereich und Neustart-Persistenz

- Einen in der VM vorhandenen Tray-Eintrag benutzen; Nyxie ist keine Voraussetzung
  und wird nicht als Teil dieses Pakets installiert.
- Ausklappen → sichtbare Trennlinie zwischen einklappbaren Einträgen und Favoriten.
- Symbol nach rechts ziehen: Vorschau folgt der Maus, Einfügelinie zeigt Position.
- Reihenfolge ändern, zurückziehen, außerhalb loslassen und mit Escape abbrechen.
- Im Anpassungsdialog dasselbe prüfen; „Immer alle Symbole anzeigen“ ein/aus.
- Normale Links-/Rechtsklickmenüs und Lautstärke-/Netzwerk-Applets testen.
- Favorit und Reihenfolge festlegen. Abmelden/anmelden und später VM neu starten:
  Anordnung unverändert, Favorit auch eingeklappt sichtbar. Prüfen, ob neu gestartete
  Apps wieder an derselben Position auftauchen; IDs dürfen nicht vom Prozess abhängen.
- Infobereich-Komponente abwählen: native Symbole müssen wieder vollständig und
  normal bedienbar sein. Wieder aktivieren und gespeicherte Favoriten prüfen.

## 4. Explorer mit ausschließlich eigenen Testdateien

- Testordner mit Text, Bild, PDF, Archiv, Unterordner und Leerzeichen/Umlauten anlegen.
- Navigation, Baumansicht, Suche, Vorschau, Datei-/Ordner-Kontextmenüs und leerer
  Arbeitsplatz-Hintergrund. Datenträgerbalken mit tatsächlicher Belegung vergleichen.
- Strg+C/X/V, Entfernen, Strg+Z, F2 und Rückgängig nach mehreren Dateiaktionen.
- Kopierkonflikte/Abbruch, Papierkorb: wiederherstellen, endgültig löschen, leeren.
  Nur eigens angelegte VM-Testdateien benutzen, keine geteilten Host-Dateien.
- Firefox: heruntergeladene Testdatei im Ordner anzeigen → Elternordner plus Auswahl.
- Netzwerk: Freigabe öffnen, native Passwortabfrage, Abbrechen, falsches Passwort,
  erfolgreicher Zugriff und Netzwerkausfall. Zugangsdaten nur im Anmeldedialog eingeben.

## 5. Optional Boot, Login und Welcome

- Erst nach erfolgreichem Benutzer-Test einen weiteren VM-Snapshot anlegen.
- Welcome aktivieren, Dauer und Abbruch prüfen. Systemoptik über Hilfe → Boot und
  Anmeldung gesondert installieren, Passwort im normalen Systemdialog eingeben.
- VM regulär neu starten: Bootanzeige, manueller Login und Welcome prüfen.
- Falls Autologin getestet werden soll, diesen separat in der VM konfigurieren und
  seinen ursprünglichen Zustand dokumentieren. Das XP-Paket aktiviert ihn nicht.
- Mit Autologin neu starten: Welcome erscheint und verschwindet zuverlässig.
- Passwort-/Datenträgerentsperrung nur dann als geprüft markieren, wenn sie in
  dieser VM tatsächlich eingerichtet und beim Start sichtbar war.

## 6. Wiederherstellung, Update und Deinstallation

- In der Verwaltung Sicherung erstellen, eine Option ändern und Backup wiederherstellen.
- Erneutes Anwenden/Update prüfen: ursprüngliches Installationsbackup bleibt erhalten.
- Gemeinsame Deinstallation: Administratorabfrage zuerst abbrechen → Benutzerpaket
  bleibt bestehen. Danach bestätigen → Systemoptik und Benutzerpaket zurückgesetzt.
- VM neu starten: ursprüngliche Themes, Panel, Dateimanager und Anmeldung wieder da;
  unabhängige Dateien, Testdokumente und installierte Programme bleiben erhalten.
- Reinstallation nach erfolgreicher Deinstallation prüfen. Original-VM-Snapshot erst
  nach dokumentiertem Abschluss wiederherstellen oder verwerfen.

## Ergebnis sichern

```sh
mint-xp-experience verify
mint-xp-experience diagnose --output mintxp-vm-diagnose.json
```

Die Diagnose ist ein begrenzter lokaler Bericht, kein automatischer Upload.
Screenshots vor dem Teilen auf persönliche Daten prüfen. Bei Fehlern Version,
Testschritt, erwartetes und tatsächliches Verhalten notieren. Nicht als stabile
Freigabe veröffentlichen, solange Neustart- und Deinstallationstests offen sind.

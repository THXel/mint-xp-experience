Hinweis ab Preview 30: Es werden keine Sounds mitgeliefert. Ohne eigenes Pack bleiben die vorhandenen Sounds unverändert. ISO, Ordner und Archive lassen sich später in den Einstellungen importieren. Dort kann zwischen mitgelieferten und importierten Icons gewechselt werden.

# Einführung: Mint XP Experience

Diese Vorabversion bündelt die XP-Anpassungen für Linux Mint 22.3 Cinnamon. Die bisherigen VM-Ergebnisse und die noch offenen Prüfungen stehen in [VM-RESULTS.de.md](VM-RESULTS.de.md).

1. DEB installieren und Mint XP Experience öffnen; alternativ das Quellarchiv entpacken und `python3 -B launch.py` ohne sudo starten.
2. Sprache prüfen. Unter der Sprache eine eigene ISO, einen Ordner oder ein Archiv auswählen – oder ausdrücklich ohne Pack fortfahren. Ohne Soundpack bleiben vorhandene Sounds unverändert.
3. Die Bestandteile auf Willkommen auswählen und „Ausgewählte installieren“ oder „Alles installieren“ anklicken. Gesperrte Installationsbuttons erklären beim Anklicken die noch fehlende Medienentscheidung.
4. Auswahl prüfen und bestätigen. Vor Änderungen werden Sicherungen erstellt. Boot-/Login-Änderungen benötigen die native Administratorfreigabe. Ein Gesamtfortschritt zeigt die Installationsphasen.
5. Nach Abschluss bei Bedarf ab- und wieder anmelden, damit Cinnamon die Applets lädt. Geöffnete Arbeit vorher speichern.
6. Für spätere Medienimporte die Einstellungen öffnen, unter „Icons & XP-ISO“ eine Quelle auswählen und unten „Icons installieren“ oder „Icons und Sounds installieren“ wählen. Nur Sounds lassen sich direkt unter „XP-Sounds“ mit „Sounds installieren“ übernehmen. Dort zwischen mitgelieferten und importierten Icons wechseln. Keine Neuinstallation nötig.

## Was wird gesichert?

Vor der ersten Änderung werden Cinnamon-, GNOME/GTK- und Nemo-Einstellungen exportiert. Zusätzlich werden vorhandene GTK-Konfigurationen, Panelkonfigurationen, aktive Theme-/Icon-/Cursor-Dateien, das lokale XP-Soundtheme, der aktuelle lokale Hintergrund und lesbare LightDM-Konfigurationen als Referenz gesichert. Die Dateien können private Pfade und Favoriten enthalten: **Diese Sicherungen gehören nicht auf GitHub.**

Jede Datei und jeder Einstellungsschlüssel, den dieses Paket verändert, erhält außerdem einen geprüften Originaleintrag. Die Wiederherstellung unterscheidet ausdrücklich gesetzte Werte von Systemstandards. Updates überschreiben diesen Ausgangspunkt nicht. Vorher fehlende Dateien werden bei der Deinstallation wieder entfernt; fremde Dateien bleiben erhalten.

Sicherungsort: `~/.local/state/mint-xp-experience/` oder, falls gesetzt, `$XDG_STATE_HOME/mint-xp-experience/`. Dieser Ordner darf bis nach erfolgreicher Deinstallation nicht gelöscht werden.

## Bestehendes XP-Setup

Wird das Paket auf einem bereits angepassten Rechner installiert, ist **dieser Zustand** sein Ausgangspunkt. Es kann keinen rückwirkenden Originalzustand erfinden. Die früheren XP-Setup-Backups deshalb behalten. Bei dieser Migration zunächst nur die Verwaltung installieren; neue Komponenten später bewusst übernehmen. Frühere Rückrollskripte erst nach Deinstallation der neuen Verwaltung verwenden. Nicht mehrere Generationen gleichzeitig zurückrollen.

## Deinstallation

Unter „Deinstallation“ die Wiederherstellung starten. Vorher werden alle verwalteten Dateien und Einstellungen geprüft. Fremde Dateiänderungen bleiben geschützt. Gültige persönliche Panel-Anordnungen und von Cinnamon erneuerte Applet-IDs werden beim Rückbau berücksichtigt und erhalten. Andere Konflikte werden vor einer Änderung angezeigt. Keine persönlichen Ordner, Spiele-Spielstände oder unabhängigen Programme werden gelöscht. Backups bleiben erhalten.

## Noch nicht Teil der verwalteten Installation

- Boot-/Anmeldeoptik ist eine getrennte, ausdrücklich ausgewählte Systemkomponente mit eigener Sicherung. Die gemeinsame Deinstallation nimmt sie authentifiziert zurück. Unabhängige Änderungen in Mints nativen Anmeldeeinstellungen gehören nicht automatisch zu diesem Backup.
- Eigene Symbole im XP-Stil sind auswählbar und mitgeliefert. Ein ausdrücklich importiertes Symboltheme hat Vorrang. Originale XP-Klänge, Microsoft-Schriften und fremde XP-Icons ohne eindeutige Lizenz werden nicht mitgeliefert. Eigene zulässige Dateien lassen sich lokal ergänzen.
- Community-Spiele werden über ihre offiziellen Projekte separat installiert; vorhandene Spiele können ins XP-Menü integriert werden.
- Die neue Verwaltung ist in 14 Sprachen verfügbar. Die älteren Explorer-/Startmenü-Erweiterungen haben teilweise noch deutsche Texte.

Der normale Benutzer-Installer verändert keine systemweiten Dateien. Die separate, ausdrücklich gewählte Boot-/Anmeldeinstallation benötigt Administratorrechte und führt eigene Sicherungen. Die gemeinsame Deinstallation nimmt diese Systemkomponente zuerst mit Passwortabfrage zurück und danach das Benutzerpaket. Weder Rechner noch LightDM werden neu gestartet. Siehe SESSION.de.md.

## Test in VirtualBox

Vor der Installation `python3 -B tools/vm_check.py` ausführen. Der vollständige
Ablauf steht in [VM-TEST.de.md](VM-TEST.de.md). Die Vorprüfung ändert keine
Systemeinstellungen und ersetzt keinen echten Anmelde-/Neustarttest.

## Applets vor der Installation prüfen (Preview 31)

Vor der Bestätigung werden aktive zusätzliche Menüs und Drittanbieter-Applets
aufgeführt. Das ist eine Kompatibilitätswarnung, kein Beleg für einen Defekt:
eigene Farben oder eigene Tastenkürzel können vom XP-Desktop abweichen.
Alle Einträge sind angehakt. „Trotzdem installieren – alle behalten“ erhält sie;
„Ausgewählte Applets deaktivieren“ entfernt nur die markierten Instanzen aus dem
Panel. Ihre Installation und persönlichen Konfigurationsdateien bleiben erhalten.
Der Rückbau stellt deaktivierte Applets wieder her und erhält später ergänzte
Applet-Instanzen. Änderungen der Panel-Liste nach der Prüfung verlangen eine
erneute Auswahl, bevor der Desktop angewendet wird.

Das XP-Menü verwendet jetzt die eigene Kennung `mintxp-menu@mintxp` und verändert
kein vorhandenes Cinnamenu. Bleibt ein anderes Menü aktiv, wird für das neue
XP-Menü kein konkurrierendes Super-Tastenkürzel vorbelegt. Das normale Mint-Menü
heißt „Menü“ (`menu@cinnamon.org`) und ist unter Systemeinstellungen → Applets
verfügbar. Ein vollständiger Theme-Rückbau bewahrt private Sicherungen und
Spielstände. Unabhängig installierte Programme bleiben erhalten.

Bei der Deinstallation ist das Entfernen der durch diesen Manager installierten
Spiele und Zubehörprogramme vorausgewählt und kann abgewählt werden. Vorab
werden auch deren verwaltete Dateien geprüft. Vorher vorhandene Programme und
Spielstände bleiben erhalten. Bei einer Neuinstallation nach dem Rückbau wird
die aktuelle Konfiguration erneut gesichert; alte Sicherungen bleiben archiviert.

## Übersicht und Nachrüsten ab Preview 33

Nach der ersten Installation wechselt das Fenster automatisch zur Übersicht der
Einstellungen. Dort führen direkte Schaltflächen zu Icons, Sounds, Bestandteilen,
Prüfung, Sicherungen und Deinstallation. Unter „Bestandteile“ können später weitere
Desktop-Komponenten hinzugefügt werden.

Das Auswählen einer ISO, eines Archivs oder Ordners bereitet die Dateien zunächst
nur vor. Erst der Installationsbutton unten auf der jeweiligen Seite übernimmt sie
nach einer Bestätigung und Sicherung. Diese Buttons bleiben auch in kleinen Fenstern
sichtbar. Bei „Sounds unverändert lassen“ sind Sound-Installation und Vorschau
inaktiv; die reine Icon-Installation bleibt möglich. Importierte und mitgelieferte
Icons können unabhängig von den Sounds gewechselt werden.

## Änderungen nachvollziehen (Preview 34)

Die Medienseiten zeigen den gespeicherten Installationsstand und die aktuelle
Auswahl getrennt. „Noch nicht übernommen“ bedeutet, dass erst der Installationsbutton
die Auswahl aktiviert. Die Icon-Vorschau zeigt verfügbare PNG-Beispiele; reine
SVG-Themes können ohne diese Miniaturvorschau verwendet werden. Vor dem Anwenden
wird zusammengefasst, welche Icons und Sounds ausgewählt sind. Die Medienbuttons
installieren keine anderen Desktop-Komponenten.

Sicherungen tragen ein lokales Datum und einen Anlass, etwa Icons/ISO oder Sounds.
Vor dem Wiederherstellen werden die enthaltenen Theme-Bestandteile aufgeführt.
Persönliche Dateizuordnungen bleiben erhalten: Das Paket verwaltet ausschließlich
den Standard für Ordner. Später gewählte andere Dateimanager werden bei Medienupdates
und beim Rückbau bewahrt. Eine erneute bewusste Aktivierung von „Explorer für Ordner“
kann den XP-Explorer wieder als Standard einsetzen. Unabhängige Einträge und Kommentare
in der Zuordnungsdatei bleiben unangetastet. Bei mehrfach vorhandenen Ordner-Defaults
oder beschädigten Dateien blockiert die Sicherheitsprüfung weiterhin.

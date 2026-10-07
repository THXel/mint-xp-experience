# Aktueller Stand: Preview 36 / 37 – 7. Oktober 2026

Preview 36 wurde in der Mint-22.3-VM installiert und nach einem Neustart auf Integrität geprüft. Der vollständige Rückbau einschließlich Boot/Anmeldung und verwalteter Zubehörprogramme gelang; die ursprünglichen verwalteten Werte wurden wiederhergestellt und Nemo blieb installiert. Anschließend wurde der gesicherte Preview-36-Zustand wiederhergestellt und geprüft.

Das Fortsetzen eines VirtualBox-RAM-Snapshots blieb dabei hängen. Ein Kaltstart desselben gespeicherten Plattenzustands funktionierte. Dies ist eine Grenze des durchgeführten VM-Tests.

Preview 37 wurde anschließend mit 15 Explorer-GUI-Prüfungen getestet, darunter sechs Prüfungen für die eingebettete Suche. Kein erneuter Preview-37-VM-Boot- oder Rückbautest wird daraus abgeleitet. Weitere Freigabegrenzen stehen in [RELEASE.md](RELEASE.md).

Die folgenden Abschnitte dokumentieren frühere Versionen.

# VM-Prüfung vom 4. Oktober 2026

Umgebung: frisch installiertes Linux Mint 22.3, Cinnamon 6.6.9, X11,
VirtualBox 7.2.20 mit VMSVGA. Vor der ersten Installation wurde die ausgeschaltete
VM gesichert. Getestet wurde das öffentliche Preview-8-Archiv, anschließend das
Update auf die Korrekturen von Preview 9. Keine privaten Host-Backups, Sounds,
Microsoft-Schriften oder zusätzlichen Programme wurden in den Gast übernommen.

## Bestanden

- Archiv-Prüfsumme und sämtliche Voraussetzungen der Vorprüfung.
- Echter GTK-Erststart: automatisch Deutsch, Wechsel zu Englisch, zurück zur
  Systemsprache und Abbruch der Vorschau ohne Installation.
- Benutzerinstallation aller Komponenten außer Sounds und Spielen; ursprüngliches
  Backup und installierte Dateien/Einstellungen ohne Integritätsabweichungen.
- Zunächst 52 automatisierte Tests mit Preview 8; nach allen Korrekturen erneut
  die komplette Suite aus dem Preview-9-Archiv: **54 Tests bestanden**, einschließlich
  der drei explizit aktivierten GVfs-Papierkorbtests, keine ausgelassenen Tests.
- Tatsächlicher VM-Neustart mit automatischer Anmeldung: XP-Desktop und kurzer
  Welcome-Bildschirm, der anschließend zuverlässig verschwindet.
- Echte Mausbedienung: Startmenü öffnen/Escape, Alle Programme, Tray-Pfeil,
  Symbol zwischen Bereichen ziehen, sichtbare Vorschau und Einfügemarke,
  Speicherung in der Applet-Konfiguration und natives Lautstärkemenü.
- Echte Explorer-Tastatureingaben mit eigenen Testdateien: Strg+C/X/V/Z, F2,
  Entfernen, Wiederherstellung aus dem Papierkorb sowie endgültiges Löschen.
  Ein erster schneller Test sendete Rückgängig vor dem abgeschlossenen
  Dialog-Fokuswechsel; mit normalem Fokuswechsel bestand der gezielte Nachtest.
- Papierkorb- und Arbeitsplatz-Kontextmenü, beide animierten Seitenleisten,
  Dateipfad als Startargument öffnet den Elternordner und markiert die Datei.
- Startmenü bei 800×600: Alle Programme sichtbar und bedienbar, rechte Spalte
  mit echtem Mausrad bis zu Systeminformationen scrollbar; danach 1920×1080.
- Ausschalten-Dialog optisch sichtbar, mit Escape abgebrochen. Neustart-Symbol
  wird auch mit den unveränderten Mint-Icons dargestellt.
- Update erhält das Backup vor der allerersten Installation.
- Zweiter echter Neustart: gespeicherte Tray-Favoriten und Reihenfolge unverändert,
  gewählter Favorit auch im eingeklappten Zustand sichtbar.
- Zusätzliche Sicherung, Schriftgrößenänderung und Restore im installierten Gast.
- Vollständige Benutzer-Deinstallation: alle 17 verwalteten Einstellungen und
  2.623 Dateizustände exakt gegen das Original-Backup geprüft; keine Abweichungen.
  Eine unabhängige Testdatei bleibt erhalten. Nach dem Neustart ist wieder der
  ursprüngliche Mint-Desktop sichtbar; Einstellungen nochmals verglichen.
- Wiederinstallation direkt aus dem öffentlichen Preview-9-Archiv, mit Prüfung
  aller Manifest-Dateien und des nach dem Neustart wiederhergestellten Originalzustands.
- Optionaler Systeminstaller erfolgreich: Backup der Boot-Images und Login-Dateien;
  echter Neustart zeigt den XP-inspirierten Plymouth-Ladebildschirm, anschließend
  automatisch angemeldeten Desktop und Welcome.

- Gemeinsame Deinstallation einschließlich Plymouth und LightDM nach echter
  Administratorauthentifizierung: Systemprüfung meldet „restored“; sämtliche
  Benutzerzustände stimmen exakt mit dem Original-Backup überein. Unabhängige
  Testdatei erhalten.

## Korrekturen aus dieser Prüfung

1. Die Mindesthöhe der rechten Startmenüspalte drückte „Alle Programme“ unter
   das Suchfeld. Sie ist jetzt scrollbar; die Höhe berücksichtigt Inhalt und Monitor.
2. Das optische Testmedium erschien unter internen Festplatten. Explorer übernimmt
   jetzt Wechselmedien-Eigenschaften von übergeordneten Geräten und erkennt CD/DVD.
3. Die Symbolgröße wurde nur für die mittlere Panelzone gesetzt. Jetzt zählt die
   tatsächliche Zone der jeweiligen Taskliste; andere Zonen bleiben erhalten.
4. Das zusätzliche Neustart-Icon fehlte auf einem frischen Mint. Der Dialog nutzt
   verfügbare native Ersatzsymbole. Vorhandene spezielle Icons werden bevorzugt.

Die beiden neuen Logik-Regressionstests für Laufwerkstypen und Panelzonen
bestanden zusätzlich isoliert. Menü, Laufwerksdarstellung und Icon-Fallback
wurden nach dem Update in der laufenden VM überprüft.

## Noch nicht als abgeschlossen freigegeben

Manuelle Anmeldung am Greeter, Abbruch einer echten Administratorabfrage,
Festplattenentsperrung, reale Netzwerk-Anmeldung, Kernel-Updates, Spiele und
importierte XP-Sounds sind durch diese Ergebnisse nicht bestätigt. Keine stabile
Release-Freigabe und kein Nachweis für andere Cinnamon-Versionen.

## VM-Grafik

Bereits vor jeder XP-Installation blieb die grafische Anmeldung nach einem
Neustart schwarz, während die Textkonsole funktionierte. Nach regulärem Shutdown
und Abschalten der 3D-Beschleunigung startete der Desktop. Diese VM-Einstellung
ist getrennt vom Theme dokumentiert; das Paket verändert VirtualBox nicht.

## Preview 10: Hintergrund, Symbole und Dateiaktionen

Erneute Installation in derselben Mint-VM nach vollständig abgeschlossenem
System- und Benutzer-Rückbau und echtem Neustart. Das Original des Systems war
vor der neuen Installation nochmals ohne Abweichungen geprüft.

- Öffentliches Archiv und alle 1.582 Manifest-Einträge geprüft.
- Grafische Installation: 2.854 Dateizustände und 19 Einstellungen, keine
  Integritätsabweichungen. Die Fortschrittsanzeige wurde während Vorbereitung,
  Sicherung, Dateiübertragung und Prüfung beobachtet; Zähler stammen aus den
  tatsächlichen Arbeitsschritten. Abschluss erst nach Integritätsprüfung.
- Gewählte Hügellandschaft aktiv. Nach echtem Neustart ist das mitgelieferte
  Start-Emblem sichtbar; Startmenü mit tatsächlichem Mausklick geöffnet.
- Symbolauflösung im laufenden GTK: Computer, Ordner, Dokumente, Papierkorb,
  Laufwerke, Bilder, PDF und Terminal stammen aus dem neuen Original-Symboltheme.
  Alle 109 Symbolnamen lassen sich in kleinen und großen Größen dekodieren.
- Dialog-Vorschauen für Kopieren, Verschieben, Papierkorb und Papierkorb-Leeren:
  Bewegung, reduzierte Bewegung, Abbruchsignal und Timer-Aufräumen geprüft.
  Die Prozentwerte dieser separaten Animationsvorschauen waren Testdaten.
- Zusätzlich echte Dateiaktionen mit eigenen Testdateien über Tastatur:
  Strg+C/X/V/Z, F2, Entfernen, Wiederherstellen und endgültiges Löschen im
  Papierkorb. Arbeitsplatz-Kontextmenü, animierte Seitenleisten und
  Browser-Dateipfad mit Auswahl im Elternordner weiterhin funktionsfähig.

Die vier neuen automatisierten Tests für Fortschrittswerte, Fehlerrückbau,
Symboldekodierung und Animationsgeometrie bestanden zunächst isoliert. Danach
bestand die vollständige Suite im frisch installierten Gast: **58 Tests, keine
Fehler und keine ausgelassenen Tests**, einschließlich der echten isolierten
GVfs-Papierkorbtests (191 Sekunden).
Die offenen Punkte der vorherigen Testliste bleiben bestehen.

Zusätzlicher realer Komponenten-Rundlauf mit Preview 10: Sicherung erstellt,
Symbole und Hintergrund abgewählt und gegen die ursprünglichen Dateien und
Einstellungen geprüft; anschließend Sicherung erfolgreich wiederhergestellt.
Original-Backup bytegenau unverändert, unabhängige Testdatei erhalten. Die VM
bleibt mit Preview 10 installiert. Am Host-Desktop wurde dabei nichts umgestellt.
Das finale Archiv ergänzt diese Prüfdokumentation; der getestete Funktionscode
ist unverändert.

## Preview 11: optionale Programme und Tray-Automatik

Gezielter Folgetest in derselben Mint-22.3-VM; kein erneuter vollständiger
Boot-/Login-Test. Die vorherigen offenen Punkte gelten außerhalb dieses Umfangs
weiter. Der Hintergrund und vorhandene Desktop-Zuordnungen wurden erhalten.

- 24 gezielte automatisierte Tests bestanden: 15 für Zusatzprogramme, sechs für
  Tray und Inaktivität, drei für Sprachauswahl/Kataloge; keine ausgelassenen Tests.
- Minesweeper XP und Solitaire aus den festgelegten Community-Quellen installiert.
  Im echten Fenster per Maus: Flagge setzen und Feld öffnen sowie Karten vom
  Stapel ziehen. Private Laufzeitumgebungen verändern weder System-Java noch Node.
- JS Paint lokal gestartet; Zeichnen mit Maus, Strg+Z/Strg+Y und Speichern/Öffnen
  über native Dateidialoge. Die wieder geöffnete Zeichnung wurde gegen die
  tatsächlich gezeichneten Bilddaten verglichen. Abbrechen im nativen Speicherdialog
  lässt die Zeichnung ungespeichert; erst der abgeschlossene Download bestätigt
  das Speichern. Dieser Fall wurde zusätzlich mit echtem Dialog geprüft.
- Alle drei lokalen Programme einzeln entfernt und wieder installiert. Eigens
  angelegte Datendateien blieben erhalten; Theme-Status und dessen ursprüngliches
  Backup blieben bytegenau unverändert.
- Space Cadet Flatpak auf einem frischen Benutzerprofil installiert, das echte
  Spielfenster geöffnet, entfernt und wieder installiert. Anwendungsdaten blieben
  erhalten; vorhandene gemeinsame Runtimes wurden nicht entfernt. Kein vollständiger
  Gameplay-Test. Eine leere Flatpak-Quellenliste wurde als realer Fehler gefunden,
  behoben und mit einem zusätzlichen Regressionstest abgesichert.
- Tray in der laufenden Cinnamon-Sitzung: automatisches Einklappen nach etwa
  10,224 Sekunden; Mausbewegungen starten die Frist neu. Geöffnete Menüs und eine
  gehaltene Mausaktion verhindern das Einklappen. „Immer offen“ und Abschalten
  der Automatik funktionieren. Favoriten/Reihenfolge bleiben nach Applet-Neuladen
  gespeichert; für diese Ergänzung wurde kein weiterer Rechnerneustart durchgeführt.

Gefundene und behobene Integrationsfehler: doppelte npm-Konfigurationsdatei beim
Minesweeper-Build, fehlende Audio-Ressource beim Paint-Start, Blob-Downloadpfad
beim nativen Speichern und Leerzeile bei noch fehlenden Flatpak-Benutzerquellen.

Die neuen Installationsrezepte sind optional. Vorhandene persönliche Spiele
werden erkannt und weder übernommen noch deinstalliert. Das öffentliche Archiv
enthält keine heruntergeladenen Spiele, Java/Node-Laufzeiten oder Microsoft-Sounds.
Importierte XP-Sounds wurden weder abgespielt noch neu aktiviert; vollständige
Ereigniszuordnung ist durch diese Prüfung ausdrücklich nicht bestätigt.

Die neue Seite hat vollständige deutsche/englische Erläuterungen; weitere
Sprachen verwenden bei den neuen Fachtexten vorerst Englisch. Online-/Cloud-
Funktionen und Electron-spezifische JS-Paint-Funktionen sind nicht Teil des
geprüften lokalen Adapters. Das Paket bleibt eine Vorschau.

## Preview 12: private XP-Sounds

Gezielte Folgeprüfung: 15 unterschiedliche automatisierte Tests bestanden
(elf Sound-/Explorer-Prüfungen, drei Sprachprüfungen, ein realer Schema-Rundlauf
für die optionalen Komponenten). Kein erneuter kompletter Desktop-/Boot-Test.

In der Mint-22.3-VM wurde ein eigens erzeugtes PCM-WAV-Testpack verwendet:
30 Programmereignisse und 14 Cinnamon-/Lautstärke-/Klingelzuordnungen. Drei
Wiedergabeaufrufe wurden erfolgreich abgeschlossen und die Pfade im laufenden
Cinnamon-Soundmanager geprüft. Im echten Explorer-Fenster löste eine erfolgreiche
Dateioperation auf einer eigens erzeugten Testdatei das `empty-trash`-Ereignis
aus; der persönliche Papierkorb wurde nicht geleert. Fehler-/Abbruch-/Stummfälle
wurden isoliert getestet.

Sound-Undo stellte sämtliche betroffenen GSettings-Werte exakt wieder her. Die
Import-Quelldateien blieben unverändert. Wiederherstellen des aktiven Imports aus
der Sicherung und anschließend Rückkehr zum Ausgangsstand gelangen; bestehende
Desktop-Dateien und ursprüngliche Backup-Einträge blieben erhalten. Die neue
XP-Sound-Seite wurde im laufenden GTK angezeigt und visuell geprüft.

Auf dem persönlichen Host wurden nach separater Sicherung 39 vorhandene
WAV-Dateien einschließlich 16 interner Ereignisverknüpfungen privat übernommen.
Die Originaldateien wurden per Hash unverändert bestätigt. 30 Programmereignisse
und 14 direkte Zuordnungen sind vorhanden; die allgemeine Ereigniswiedergabe ist
aktiv. Vorher absichtlich deaktivierte Einzeltöne und andere Desktop-Einstellungen
blieben erhalten. Drei Wiedergabeaufrufe und der Live-Soundcache waren fehlerfrei.

Das bestätigt die Datei-/Einstellungsintegration und erfolgreiche Abspielaufrufe,
keine unabhängig beobachtete Lautsprecherwiedergabe. Echte Anmeldung/Abmeldung,
Ausschalten und physisches Ein-/Ausstecken wurden in dieser Folgeprüfung nicht
ausgelöst. Nicht von Programmen ausgelöste Windows-Ereignisse lassen sich durch
reine Theme-Zuordnungen nicht erzeugen. Die öffentlichen Archive enthalten weder
das persönliche XP-Soundpack noch das synthetische Testpack.

## Preview 13: Scrollbars und Abschlussanzeige

Die allgemeinen Schaltflächenabstände verbreiterten GTK-Scrollbar-Pfeile von
17 auf 41 Pixel. Das gekachelte Theme-Bild wirkte dadurch wie mehrere Leisten.
Eine gezielte Ausnahme für Scrollbar-Pfeile behebt das; der Assistent reserviert
jetzt Platz für die einzelne Leiste, statt Inhalte mit Overlay-Scrollbars zu
überdecken. Abgeschlossene oder fehlgeschlagene Aktionen blenden ihren
Fortschrittsbereich aus. Ergebnis und Fehlermeldung bleiben im Dialog und Status.
Ohne aktiven Soundimport erklären Prüfung, Testton und Rücknahme zunächst den
notwendigen Import, ohne einen Installationsvorgang zu starten.

Gezielte Prüfung in der laufenden VM: einzelne 17-Pixel-Leiste nach mehreren
Seitenwechseln, echtes Mausrad, Pfeilklick und Ziehen, Erreichbarkeit des unteren
Inhalts sowie Fortschrittsende bei Erfolg, Fehler und erneutem Versuch. Die
Job-Ergebnisse waren bewusst simuliert; die GTK-Widgets und Mausereignisse waren
real. Die drei Soundaktionen ohne Import starteten keinen Job. Dateizustand und
Einstellungen blieben im Bedienungstest unverändert. Drei Sprachkatalogtests
bestanden zusätzlich. Kein erneuter vollständiger Boot-/Desktop-Test.

## Aktueller Freigabestand nach Preview 13

Der vereinbarte Funktionsumfang ist weitgehend implementiert. Die vorstehenden
Abschnitte dokumentieren unterschiedliche Prüfstände: insbesondere Spiele und
Soundimport wurden nach der ursprünglichen Liste inzwischen gezielt geprüft.
Das Paket bleibt eine Vorschau. Für eine stabile Freigabe fehlen insbesondere:

- Manuelle Greeter-Anmeldung, Abbruch einer echten Administratorabfrage,
  Festplattenentsperrung und Verhalten bei Kernel-Updates.
- Reale Anmeldung an einer Netzwerkfreigabe.
- Weitere Neustartprüfung der zuletzt ergänzten Tray-Automatik.
- Echte Login-/Logout- und Geräteereignisse mit unabhängig bestätigter
  hörbarer Wiedergabe; Soundaufrufe und Zuordnungen sind bereits geprüft.
- Sprachliche Prüfung und Ergänzung der englischen Rückfalltexte in den
  weiteren Sprachen; keine Behauptung vollständiger Übersetzung.
- Abschließender Quellen-/Lizenzabgleich für die Veröffentlichung gemäß
  `docs/PUBLISH.de.md` und `docs/SOURCES.md`.

Ein GitHub-Repository wurde noch nicht angelegt oder öffentlich hochgeladen.

## Preview 14: Spiele-Untergruppe und Paint-Zubehör

Die bisher fehlenden öffentlichen Menüdateien sind jetzt Bestandteil der
Menükomponente. „Spiele → Windows-XP-Klassiker“ berücksichtigt vorhandene
Community-Starter, die optionalen Paket-Starter und die von Cinnamon verwendete
Flatpak-ID für Space Cadet. JS Paint wird „Zubehör“ zugeordnet und erhält ein
eigenes CC0-Symbol mit Palette und Pinsel im klassischen Desktop-Stil.
Es handelt sich nicht um eine mitgelieferte Microsoft-Originalgrafik.
Das Symbol wird auch vom nativen Paint-Fenster verwendet.

Im laufenden VM-Startmenü wurden alle drei Klassiker, Paint unter Zubehör und
seine Entfernung aus der Grafik-Kategorie geprüft. Beim Test gefundene doppelte
Elterneinträge wurden behoben: ausgeschlossene Einträge und bereits in einer
Untergruppe enthaltene Programme werden passend gefiltert.
Space Cadet und JS Paint wurden über echte Mausklicks durch die Menü-Untergruppen
gestartet, ihre neuen Fenster erkannt und anschließend wieder geschlossen.
Die vorherige Liste zuletzt verwendeter Programme wurde wiederhergestellt.

Zehn gezielte Add-on-Tests bestanden, einschließlich Symbol-/Starter-Installation
und Schutz vorhandener Flatpaks und Spielstände. Der optionale
Menükomponenten-Rundlauf mit realen GSettings-Schemas und Speicher-Backend
bestand ebenfalls. Das SVG lässt sich mit 22, 32, 48 und 128 Pixeln dekodieren.
Die Änderungen erfordern keinen weiteren vollständigen Boot-/Desktop-Test;
die übrigen offenen Freigabeprüfungen bleiben bestehen.

Zusätzlich bestand in der VM der exakte Rückbau von Menü und Paint gegen die
vorher angelegten Snapshots, gefolgt vom erneuten Anwenden des geprüften Patches.
Die ursprünglichen Backup-Einträge blieben dabei unverändert. Auf dem Host
wurden die Live-Kategorien und die Integrität des bestehenden Soundimports
mit 39 WAV-Dateien geprüft. Separate Theme- und Paint-Snapshots erlauben den
gemeinsamen Rückbau dieser Änderung.

## Preview 15: freie Sounds, Archivimport und Menünamen

Gezielt auf Linux Mint 22.3 / Cinnamon 6.6.9 geprüft:

- 43 automatisierte Prüfungen erfolgreich: Ordner, ZIP, TAR mit gzip/bzip2/xz,
  7z sowie eine selbst erzeugte unkomprimierte RAR5-Testdatei; originale WAVs
  des freien Luna-Pakets. Verschlüsselte Archive, Pfadausbrüche und Links werden
  abgelehnt. Unterschiedliche Treffer benötigen eine Auswahl; identische Kopien
  werden zusammengefasst. Deutsche Namen und Start/Startup bleiben unterscheidbar.
- Native GTK-VM-Prüfung: Archiv auswählen, Mehrdeutigkeiten abbrechen/auswählen,
  aus dem Archiv importieren, Sound-Undo, exaktes Snapshot-Restore und Aktivierung
  des freien Standardpakets. Quellen blieben unverändert. Importberichte zeigen
  30 Programmereignisse und 14 direkte Cinnamon-/Lautstärke-/Klingel-Zuordnungen.
- Drei erfolgreiche Testton-Aufrufe (Klingel, Information, Warnung). Kein Nachweis
  tatsächlicher Hörbarkeit und kein neuer echter Login-/Logout-Soundtest.
- Laufendes Cinnamon-Menü: Paint - JS Paint mit Palette unter Zubehör und Grafik;
  bestehendes Space-Cadet-Flatpak unter dem Anzeigenamen 3D Pinball. App-ID und
  Installationsart bleiben erhalten. Programmstarts waren in Preview 14 geprüft;
  dieser Patch änderte ausschließlich Anzeigenamen/Kategorien.
- Sichtprüfung der Soundseite: eine vertikale Bildlaufleiste, Fortschritt nach
  Abschluss ausgeblendet, Lizenzhinweis und getrennte Auswahl für Luna/Import.
- Der Generator reproduziert alle 22 WAV-Dateien bytegenau. Der Release-Build
  akzeptiert nur diese manifestgeprüften Audiodateien, keine privaten XP-Imports.

Dies ist ein gezielter Patchtest. Die zuvor dokumentierten offenen Freigabepunkte,
Sprachprüfung und vollständigen Sitzungs-/Systemtests bleiben davon unberührt.

## Preview 16: DEB und Abschlussprüfung (2026-10-05)

- Das DEB wurde in der Mint-VM regulär über apt und eine echte Administrator-
  freigabe installiert. Es kopiert die Anwendung, aktiviert aber kein Theme.
  Paketmetadaten, Desktop-Starter und sämtliche DEB-Dateiprüfsummen wurden geprüft;
  es enthält keine maintainer scripts und schreibt keine Benutzerkonfiguration.
- Der Assistent bietet Abhören einzelner Kandidaten und beendet die Wiedergabe
  beim Abbrechen. Die Abschlussseite nutzt eine abgeschlossene Transaktion und
  nennt Bestandteile, Sicherungsort und erneute Anmeldung. Geänderte Applet-/Theme-
  Dateien lösen diesen Hinweis auch ohne Änderung der GSettings-Werte aus.
- Native GTK-Prüfung bei 100 %, 125/150 % Schriftvergrößerung sowie 200 % Skalierung:
  Seitenenden erreichbar, keine horizontale Überbreite im geprüften Arbeitsbereich,
  Tab-Navigation, Abhören/Abbruch und Abschlussdarstellung erfolgreich. Das ist
  keine Prüfung jeder Kombination aus Monitorauflösung und Skalierung.
- Benutzerinstallation aus dem DEB-Payload, Update, Benutzer-Deinstallation und
  erneute Installation auf der VM bestanden. Originalwerte und eine zusätzliche
  Testdatei blieben erhalten. Der lokale Starter nutzt bei installiertem DEB die
  aktuelle Paketversion. Der systemweite Paketabbau per apt wurde nicht live geprüft.
- Die drei zuerst übersprungenen GVfs-Papierkorbtests wurden anschließend in der
  VM erfolgreich mit eigenen Dateien ausgeführt. Eine echte Administratorabfrage
  wurde mit Escape abgebrochen (Rückgabecode 126).
- Tray-Reihenfolge, Favoriten und Zehn-Sekunden-Automatik bestanden die Prüfung
  nach tatsächlichem Neustart des Gasts. **Der reguläre Shutdown davor hing mit
  einer Kernel-RCU-/CPU-Stall-Meldung (7.0.0-38, acht virtuelle CPUs).** Zur Erholung
  war ein VirtualBox-Reset nötig. Ursache nicht eingegrenzt; deshalb ist ein
  störungsfreier vollständiger Neustart weiterhin kein bestandenes Kriterium.
- Lesender Zugriff auf eine bestehende, bereits authentifizierte SMB-Freigabe
  funktionierte. Das ersetzt keinen Test einer neuen Anmeldung mit Passwort.
- GitHub-Fehlervorlage, DEB-Anleitung, neuer Screenshot und Veröffentlichungsstand
  wurden aktualisiert. Herkunftslücken übernommener Grafiken bleiben dokumentiert;
  Originalsounds und heruntergeladene Spielinhalte sind nicht im Paket enthalten.

Vor stabiler Veröffentlichung weiterhin offen: Shutdown-/Kernelproblem isolieren,
manuelle Greeter-Anmeldung, verschlüsselte Datenträger und Kernel-Updates, neue
Netzwerkanmeldung, unabhängig bestätigte hörbare Login-/Logout-Gerätesounds sowie
sprachliche und vollständige Herkunftsprüfung. Der bereitgestellte Build ist ein
Test-Preview. Die separate Systemoptik ist optional und unverändert.

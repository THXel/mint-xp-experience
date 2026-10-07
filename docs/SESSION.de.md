# Boot, Anmeldung und Welcome

Linux Mint 22.3 verwendet hier Plymouth für die frühe Bootanzeige und LightDM/Slick Greeter für die Anmeldung. Die neue Optik verwendet eigene XP-inspirierte Grafiken mit Mint-XP-Experience-Schriftzug. Originale Microsoft-Logos oder Windows-Dateien sind nicht enthalten.

## Drei getrennte Komponenten

- **Boot:** schwarzer Hintergrund, blaue bewegte Balken. Der native Plymouth-Renderer `two-step` behält Passwort-, Tastatur- und Systemmeldungen. Bootgrafiken können erst angezeigt werden, nachdem Firmware/Bootloader die Kontrolle an Linux übergeben haben; Firmwarelogos werden nicht verändert.
- **Anmeldung:** blauer Hintergrund mit XP-Farbbändern, Markenbereich links, native Benutzer- und Passwortauswahl rechts. Tastatur, Bedienungshilfen und Ausschalten bleiben erreichbar. Slick Greeter behält seine eigene Benutzerkachel; dies ist keine pixelgenaue Kopie von Microsofts Anmeldeprogramm.
- **Welcome:** optionaler kurzer Bildschirm nach erfolgreicher Anmeldung, auch bei Autologin. Systemsprache automatisch, 14 Begrüßungen. Auf dem Hauptmonitor erscheint der Text, auf weiteren Monitoren die passende Fläche. Nach 2,6 Sekunden blendet er sich aus; Anklicken beendet ihn sofort. Ein unabhängiges Zeitlimit beendet den Prozess spätestens nach zwölf Sekunden. Er ist keine Sperre und fragt niemals nach Passwörtern.

Bei automatischer Anmeldung überspringt LightDM die Benutzerauswahl. Autologin wird durch das Paket nicht deaktiviert. Welcome erscheint innerhalb der gestarteten Sitzung; eine kurze vorher sichtbare Desktopansicht ist je nach Startreihenfolge möglich.

## Installation

Welcome unter **Komponenten** in der Theme-Verwaltung aktivieren. Unter **Hilfe → Boot und Anmeldung im XP-Stil** öffnet sich die separate Systeminstallation. Sie erfordert das Administratorpasswort im normalen Systemdialog. Root-Rechte betreffen ausschließlich diese ausdrücklich ausgewählten Systemkomponenten.

Alternativ aus dem entpackten Paket:

```sh
pkexec /usr/bin/python3 -I -B system/appearance.py apply --boot --login
```

Die Installation sichert zuerst die betroffenen Dateien und die Boot-Images des laufenden bzw. aktuell verlinkten Kernels. Danach installiert sie Theme-Dateien, stellt die Plymouth-Auswahl um und erzeugt ein neues Boot-Image mit `mkinitramfs`. Erst wenn das Image vollständig erzeugt und auf Theme/Renderer/Passwortsymbole geprüft ist, ersetzt es atomar das gesicherte Image. Andere installierte Kernel behalten ihre bisherige Bootanzeige. Künftige reguläre Kernelupdates verwenden die gewählte Plymouth-Alternative.

Es werden keine GRUB-Parameter, Autologin-, PAM-, Passwort- oder Benutzerkonten-Einstellungen geändert und weder LightDM noch der Rechner neu gestartet.

## Prüfung und Rücknahme

```sh
sudo /usr/bin/python3 -I -B /var/lib/mint-xp-experience-system/appearance.py verify
sudo /usr/bin/python3 -I -B /var/lib/mint-xp-experience-system/appearance.py undo
```

Das rootgeschützte Journal liegt unter `/var/lib/mint-xp-experience-system`. Dort sind exakte Originale, Dateirechte, Prüfsummen und die vorherige Plymouth-Auswahl enthalten. Bei später veränderten betroffenen Dateien/Boot-Images stoppt die Rücknahme vor Schreibzugriffen. Ein Kernelupdate kann einen solchen Schutzkonflikt auslösen; dann den Systemstand prüfen und keine alte Bootdatei erzwingen.

**Die gemeinsame Paket-Deinstallation nimmt Boot/Anmeldung zuerst mit Administratorabfrage zurück und danach das Benutzerpaket.** Eine separate Rücknahme nur der Systemoptik ist weiterhin über den Systemdialog möglich. Wird die Administratorabfrage abgebrochen, bleibt das Benutzerpaket unverändert. Welcome ist hingegen Bestandteil des normalen Benutzer-Backups und wird beim Abwählen oder Deinstallieren zurückgenommen. Ältere XP-Backup-Pakete erst nach dem jüngsten Patch zurücknehmen.

## Prüfgrenzen

Grafiken und Welcome wurden gerendert; der echte Slick Greeter wurde in isolierter Konfiguration mit Testbenutzern geöffnet. Das prüft Darstellung, nicht eine reale Anmeldung. Die Bootgrafik-Vorschau ist eine Wiedergabe der erzeugten Bilder, kein Neustarttest des Grafiktreibers. Ein tatsächlicher Boot-/Autologin-Durchlauf muss beim nächsten regulären Neustart bestätigt werden. Es gibt keinen automatischen Neustart zu Testzwecken.

Quellen: [Slick-Greeter-Konfiguration](https://github.com/linuxmint/slick-greeter/blob/master/README.md), [Plymouth-Projekt](https://wiki.freedesktop.org/www/Software/Plymouth/), dazu der tatsächlich installierte Mint-Initramfs-Hook `/usr/share/initramfs-tools/hooks/plymouth`.

## Welcome-Einstellungen ab Preview 4

Unter Mint XP Experience → Optionen lassen sich Dauer (0,5 bis 8 Sekunden),
sanftes Ausblenden und Hauptmonitor/alle Monitore auswählen. Die Vorschau zeigt
die gewählten Werte sofort in einem einzelnen Fenster. „Änderungen prüfen“ und
„Anwenden“ speichern die Konfiguration. Der Welcome-Bildschirm folgt der gemeinsamen
Sprachwahl, bleibt mit Escape/Klick abbrechbar und besitzt weiterhin einen
unabhängigen Zeitwächter. Er ist eine Dekoration nach der Anmeldung, keine
Passwortabfrage und kein Ersatz für einen Sperrbildschirm.

Die gemeinsame Deinstallation nimmt Boot/Login zuerst authentifiziert zurück und
danach das Benutzerpaket. Bereits unabhängig installierte XP-Anpassungen gehören
zum gesicherten Ausgangszustand; ihre früheren privaten Rückrollpakete bleiben
separat. Echten Kaltstart, automatische Anmeldung und Wiederherstellung bitte in
der frischen Mint-VM durchspielen, bevor diese Vorschau als stabil veröffentlicht wird.

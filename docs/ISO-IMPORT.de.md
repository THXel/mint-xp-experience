Hinweis ab Preview 30: Es werden keine Sounds mitgeliefert. Ohne eigenes Pack bleiben die vorhandenen Sounds unverändert. ISO, Ordner und Archive lassen sich später in den Einstellungen importieren. Dort kann zwischen mitgelieferten und importierten Icons gewechselt werden.

# Windows-XP-ISO lokal importieren

Auf **Willkommen**, direkt unter der Sprache, die Nutzungsrechte bestätigen und **ISO oder Archiv wählen** anklicken. Eine eigene XP-ISO wird eingelesen und ihre Icons und Sounds werden automatisch ausgewählt. Die Bestätigung erteilt keine Lizenz. Der Importer lädt keine ISO aus dem Internet herunter.

Der Import liest die ISO ohne Mounten und ohne Administratorrechte. In klassischen Installationsmedien sucht er in I386 oder AMD64 nach den XP-WAV-Ressourcen und SHELL32.DLL bzw. deren CAB-komprimierten Varianten. Er führt keine Windows-Datei aus. Recovery-Datenträger, verschlüsselte Images und abweichende Herstellerformate sind nicht zugesichert.

Die geprüfte XP-Professional-x64-Installationsstruktur enthält 26 Sounds. Die Kurzbezeichnungen XPSTARTU, XPCRTSTP usw. werden den Ereignisnamen zugeordnet. 33 gängige Symbolnamen werden aus den geprüften Shell-Ressourcen bereitgestellt, unter anderem Ordner, Arbeitsplatz, Netzwerk und Papierkorb. Fehlende Symbole erben die freien Ersatzicons; es wird nicht behauptet, sämtliche Windows-Anwendungssymbole zu importieren.

Private Ablage: `${XDG_STATE_HOME:-$HOME/.local/state}/mint-xp-experience/imports/`. Der Import allein ändert keine Desktop-Einstellungen. Erst „Ausgewählte installieren“ oder „Alles installieren“ aktiviert die Auswahl nach Prüfung und Sicherung. Die Installation legt eigene Kopien an. Die ISO darf anschließend offline sein; die aktivierte Kopie bleibt verfügbar. Die Importablage und Sicherungen werden bei einer Deinstallation nicht ungefragt gelöscht.

Unter **XP-Sounds** lässt sich die ausgewählte Quelle vorhören, auch vor der Installation. Das Importergebnis zeigt fehlende oder mehrdeutige Zuordnungen. Die Auswahl bleibt beim Sprachwechsel erhalten.

## Grenzen und Sicherheit

ISO maximal 5 GiB, einzelne Ressource maximal 40 MiB, ausgewählte Rohdaten maximal 128 MiB. Der isolierte Prozess hat Speicher-, Zeit- und Dateigrößenlimits. Archivpfade werden nie direkt auf die Festplatte extrahiert. PE-Ressourcen werden mit Bereichs- und Zyklusprüfung gelesen. Fehler hinterlassen keine teilweise ausgewählte Installation.

## Rechte und freie Alternativen

Der Besitz einer Windows-ISO allein erlaubt nicht automatisch jede Nutzung außerhalb von Windows oder die Weitergabe extrahierter Grafiken und Aufnahmen. Bitte die zutreffende Lizenz prüfen. Weder das DEB noch das öffentliche Quellarchiv enthalten importierte Dateien.

Microsoft: https://www.microsoft.com/en-us/legal/intellectualproperty/copyright/permissions


Hintergrund zu Komposition und Aufnahme: https://www.copyright.gov/register/pa-sr.html

Formatreferenzen:
- https://learn.microsoft.com/en-us/windows/win32/debug/pe-format
- https://learn.microsoft.com/en-us/windows/win32/menurc/resource-file-formats
- https://github.com/libarchive/libarchive/wiki/LibarchiveFormats

# Vorbereitung des GitHub-Previews

Veröffentlicht wird ausschließlich der Ordner `mint-xp-experience` bzw. das mit
`tools/build_release.py` erstellte Quellarchiv und das daraus gebaute DEB. Private XP-Setup-Ordner, Backups,
VM-Berichte, Spielstände, Download-Caches und die heruntergeladenen Programme
gehören nicht in das Repository. Das Werkzeug verwendet dafür eine Positivliste
und prüft auf persönliche Pfade und lokale Netzwerkadressen.

Vor dem Anlegen des Repositories:

1. Den aktuellen Kandidaten mit den gezielten Ergebnissen in
   `docs/VM-RESULTS.de.md` abgleichen. Den kompletten früheren Desktop-Test muss
   eine reine Korrektur nicht wiederholen; betroffene Funktionen werden geprüft.
2. Herkunftshinweise in `docs/SOURCES.md` und `docs/GAMES.md` lesen. Das Paket
   enthält keinen pauschalen Freigabenachweis für Microsoft-Grafiken, Sounds oder
   fremde Marken. Die heruntergeladenen optionalen Programme behalten ihre
   eigenen Hinweise. Offene Herkunftsfragen bleiben vor einer stabilen
   Veröffentlichung zu klären.
3. README, Lizenz, unterstützte Mint-/Cinnamon-Version, optionale Downloads,
   Backup-Grenzen und Deinstallation sichtbar lassen. Die neuen Spezialtexte zu
   Downloads/Lizenzen sind Deutsch/Englisch; weitere Sprachen benötigen Review.
4. `python3 -B tools/build_deb.py` ausführen. SHA256SUMS und das enthaltene
   MANIFEST.sha256 prüfen und als Preview-Version veröffentlichen.
5. Erst danach den gewünschten GitHub-Namen und die Sichtbarkeit festlegen,
   Repository anlegen und nur den geprüften Quellstand hochladen.

Das öffentliche Repository ist [THXel/mint-xp-experience](https://github.com/THXel/mint-xp-experience). Veröffentlichte Downloads stehen unter Releases; deren Versionsstand und Prüfsummen sind maßgeblich.

Für das erste GitHub-Release **Pre-release** verwenden. Die Maintainer-Platzhalteradresse `noreply@example.invalid` im DEB ist kein Supportkontakt.
Fehlerberichte gehören in die [GitHub-Issues](https://github.com/THXel/mint-xp-experience/issues); vor einer stabilen Debian-Veröffentlichung ist ein freigegebener Maintainerkontakt einzutragen. Es wird keine Adresse
aus dem privaten Benutzerkonto übernommen. Die Fehlerbericht-Vorlage fordert
ausschließlich Versionsangaben, Reproduktionsschritte und optional den gezielt
begrenzten Diagnoseexport. Private Backups gehören auch nicht in GitHub-Issues.

Das DEB enthält ausschließlich die Anwendung unter `/usr/share`, einen Starter
und Dokumentation sowie einen einmaligen Cinnamon-Erststart. Der postinst-Helfer bittet nur den bestehenden systemd-Benutzerdienst aktiver lokaler grafischer Sitzungen, den Assistenten zu öffnen; keine Root-GUI und keine automatische Theme-Anwendung.
Optionale Spiele/Downloads und Systemoptik bleiben separate Benutzerschritte.

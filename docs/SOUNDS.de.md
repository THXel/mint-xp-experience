# Sounds: unverändert lassen oder eigene Medien importieren

Es werden keine Sounds mitgeliefert. Ohne ausgewähltes Soundpack bleiben die
vorhandenen Sounddateien und Einstellungen unverändert. Das frühere Luna-Pack
ist entfernt; beim Wechsel von diesem Pack wird dessen gesicherter Ausgangszustand
wiederhergestellt. Persönliche Windows-XP-Packs und Sicherungen bleiben erhalten.

Originale Windows-XP-Sounds sind aus Lizenzgründen nicht enthalten und werden
nicht automatisch heruntergeladen. Für eigene Dateien musst du die nötigen
Nutzungsrechte besitzen; ein lokaler Import ersetzt keine Lizenz.

Wähle **Eigener Ordner oder Archiv**, dann einen Ordner oder eine ZIP-, RAR-, 7z-
oder TAR-Datei (auch tar.gz, tar.bz2, tar.xz). **Dateien und Zuordnungen prüfen**
zeigt erkannte Ereignisse, fehlende Zuordnungen und ungenutzte Dateien. Unterordner
werden durchsucht. Übliche englische/deutsche Namen, etwa `Windows XP Ding.wav`,
`Gerät angeschlossen.wav` oder `Papierkorb leeren.wav`, werden zugeordnet. Explizite
Ereignisnamen wie `dialog-error.wav` haben Vorrang. Verschiedene passende Dateien
werden zur Auswahl angezeigt; mit **Anhören** lassen sich die Kandidaten vergleichen. Beim Schließen endet die Vorschau; deine Sound-Einstellungen bleiben dabei unverändert. Identische Kopien werden automatisch zusammengefasst.
Anschließend **Sichern, importieren und aktivieren** wählen.

PCM-WAV in mono/stereo wird unterstützt: maximal 512 WAV-Dateien, 4096 Einträge,
16 MiB je Datei und 128 MiB insgesamt. Archive werden durch Mints libarchive in
einem separaten begrenzten Prozess gelesen; Eingabepfade werden nie direkt
entpackt. Links und unsichere Pfade in Archiven werden zurückgewiesen. In Ordnern
sind interne Dateiverknüpfungen erlaubt. Verschlüsselte, mehrteilige oder ineinander
verschachtelte Archive vorher selbst entpacken; OGG und MP3 vorher in PCM-WAV
umwandeln. Für Windows-XP-ISOs den eigenen ISO-Import auf der Medien-Seite
verwenden, siehe [ISO-Import](ISO-IMPORT.de.md).

Die Originale bleiben unverändert. Die verwaltete Kopie liegt unter
`~/.local/share/sounds/Mint-XP-Experience-Sounds/`; `originals/` enthält auch nicht
zugeordnete Sounds. `mapping.json` dokumentiert die erkannten Ereignisse und
Lücken. Bestehende `stereo/*.wav`-Zuordnungen und leere `.disabled`-Marker werden
berücksichtigt. Fehlende bekannte XP-Dateien werden angezeigt; das Programm
behauptet bei Teilpaketen keine vollständige Zuordnung.

Zuordnungen umfassen zwölf Cinnamon-Ereignisse (An-/Abmeldung, Arbeitsflächen,
Fensteraktionen, Geräte, Benachrichtigungen), Lautstärketon und Klingeldatei.
Hinzu kommen bis zu 30 benannte Programmereignisse, unter anderem Fehler,
Warnung, Informationen, Akkuwarnungen und Papierkorb. Der eigene XP-Explorer
löst `trash-empty` nach erfolgreich abgeschlossenem Leeren aus; bei Abbruch,
Fehler, übersprungenen Objekten oder ausgeschalteten Ereignissounds bleibt er still.
Eine Zuordnung allein erzeugt kein Ereignis in Programmen, die keine passenden
Sounds auslösen. Alte Internet-Explorer- oder Telefonie-Klänge bleiben als Dateien
verfügbar; passende Linux-Ereignisse sind nicht überall vorhanden.

Die allgemeinen Cinnamon-/GTK-Ereignissounds werden eingeschaltet. Bei aktivierter
Übernahme bleiben persönliche Dateizuordnungen und Ein-/Aus-Schalter erhalten,
sofern ihre Datei im ausgewählten Pack liegt. Die vorhandene Lautstärke,
Tasten-/Mausrückmeldungen und der separate Schalter für die hörbare Systemklingel
werden nicht verändert. Bei neuen Zuordnungen bleibt der Fensterschließton
standardmäßig aus. Nach dem Import kann der Quellordner entfernt werden; spätere
unveränderte Theme-Anwendungen verwenden die gespeicherte private Kopie.

## Originale Mint-Sounds

Unter **XP-Sounds** ist zusätzlich **Originale Linux-Mint-Sounds** auswählbar.
Die Vorschau spielt die auf diesem Rechner installierten Mint-Dateien ab. Die
Übernahme verwendet das Soundtheme LinuxMint und die originalen Cinnamon-
Sounddateien mit den Standardschaltern des Systems. Lautstärke und Eingabe-
Feedback werden nicht verändert. Ein Backup wird wie bei anderen Soundwechseln
angelegt; Rückgängig stellt den Ausgangszustand wieder her. Mint-Dateien werden
weder heruntergeladen noch in das öffentliche Paket kopiert.

## Auswahl und späteres Nachrüsten

Auf Willkommen zunächst eine ISO, einen Ordner oder ein Archiv auswählen oder
**Ohne Pack fortfahren** wählen. Letzteres verwendet mitgelieferte Icons und
verändert keine Sounds. Bei einem reinen Icon-Paket bleiben die Sounds ebenfalls
unverändert. Bei einem reinen Soundpaket werden die mitgelieferten Icons verwendet,
sofern keine eigenen Icons ausgewählt sind.

Auch nach der Installation lassen sich unter **Icons & XP-ISO** weitere Medien
importieren. **Medienauswahl übernehmen** aktiviert nur Icons und explizit
gewählte Sounds; Bootoptik, Spiele und andere Komponenten bleiben unverändert.
Zwischen mitgelieferten und importierten Icons kann gewechselt werden, ohne
bereits importierte Dateien zu verlieren. **Vorhandene Sounds unverändert lassen**
bewahrt auch ein zuvor importiertes persönliches Soundpack.

## Rückgängig und Prüfen

Vor Import und Sound-Undo wird ein Backup angelegt. **Sound-Import rückgängig
machen** stellt die ursprünglichen Sound-Einstellungen wieder her und entfernt
die verwalteten Dateien. Andere Theme-Bestandteile bleiben erhalten. Geänderte
verwaltete Dateien/Einstellungen blockieren ein Überschreiben; Originale,
Backups und private Spielstände werden nicht gelöscht. Die normale
Deinstallation stellt ebenfalls die ursprünglichen Einstellungen wieder her. Die Sicherungsseite kann einen späteren Zwischenstand
wiederherstellen.

```sh
mint-xp-experience sound-plan --source "$HOME/.local/share/sounds/Windows-XP"
mint-xp-experience sound-import --source "$HOME/.local/share/sounds/Windows-XP" --yes
mint-xp-experience sound-verify
mint-xp-experience sound-test --event bell
mint-xp-experience sound-remove --yes
mint-xp-experience verify
```

Tests spielen einzelne Klänge ab, ohne Abmelden, Ausschalten oder Geräteentfernung
auszulösen. Erfolgreiche Wiedergabeaufrufe sind kein Nachweis dafür, dass ein
Lautsprecher hörbar war. Anmeldung/Abmeldung beim echten Sitzungswechsel müssen
separat beobachtet werden. Die Medienauswahl ist in den 14 unterstützten Sprachen verfügbar.

Technische Grundlagen: [freedesktop Sound Theme Specification](https://specifications.freedesktop.org/sound-theme/latest-single/)
und die auf Mint 22.3 installierten Cinnamon-Dateien `js/ui/soundManager.js`,
`cinnamon-settings/modules/cs_sound.py` sowie die `org.cinnamon.sounds`-Schemas.

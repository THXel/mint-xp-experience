# Optional XP games and JS Paint (preview 11)

Choose **Games and accessories / Spiele und Zubehör** in the assistant. Nothing
is selected or downloaded automatically. Each application has its source/licence
link, a confirmation with provenance limitations, progress, an Open button and,
only if installed by this manager, a separate Remove button.

## Applications

- **Minesweeper XP 0.3.0**, [Akshay Kalose](https://github.com/AkshayKalose/Minesweeper-XP),
  MIT upstream. It is a Go/Wails and React project, not a Python recreation.
  Its Linux binary expects old WebKit 4.0. This installer downloads the pinned
  source and a pinned temporary Node 22 runtime, uses the upstream npm lockfile
  with lifecycle scripts disabled, then builds the frontend. Small, reviewable
  source patches preserve the existing 150% layout. A local Python host uses
  Mint's WebKit 4.1; temporary build tools are removed afterwards.
- **Solitaire 1.1**, [Daniel Ricci](https://github.com/danielricci/solitaire), MIT upstream.
  Downloads the JAR and its licence plus private Eclipse Temurin Java 8u504-b01
  (latest upstream release checked on 2026-10-04). System Java is unchanged.
- **JS Paint**, [Isaiah Odhner](https://jspaint.app/about), source commit
  `53be67ab8c47cc0d2168899e7481bc04839c4c81`. Downloads static application files
  and their notices; runs offline with Mint's WebKit 4.1. Native Open/Save dialogs
  are provided by WebKit and the local host. Electron is not downloaded. This is
  a local web adaptation, not a claim of parity with every Electron-only feature.
  Cloud collaboration, speech/head tracking and wallpaper integration are not
  part of the supported baseline.
- **Space Cadet**, [k4zmu2a's engine](https://github.com/k4zmu2a/SpaceCadetPinball),
  uses the preferred Flatpak `com.github.k4zmu2a.spacecadetpinball`. Existing user
  and system installations are reused, never replaced or removed by this manager.
  New installations use user scope and the official Flathub remote. Flatpak
  verifies signed OSTree content; its dependency download totals pulse in the UI.

## Licences are not a blanket artwork clearance

Code licences do not automatically clear inherited graphics, fonts, sounds or
trademarks. JS Paint itself mentions third-party resources; its MIT code licence
is not proof that all those resources can be redistributed. The Space Cadet
Flatpak downloads original Pinball data from Archive.org as extra-data; the MIT
engine licence does not cover those original files. Appropriate usage rights are
required. A checkbox or warning cannot supply missing permission. The public
theme archive contains download recipes and our adapters, **not these downloaded
application payloads**, original XP icon packs, Microsoft sounds or Microsoft fonts. This
separation does not amount to a legal clearance for any particular download.

The B00merang XP icon repository **does contain GPL-2.0**, contrary to an earlier
documentation statement. Its inherited artwork provenance remains a separate
question. The package defaults to its own icons; local icon import remains
available without a download of original Microsoft icons.

## Requirements, storage and removal

Linux Mint 22.3 x86_64, Python GI/GTK3, `gir1.2-webkit2-4.1`, internet and at least
1.2 GiB temporary free space for a build. No password or system Java changes for
local application installs. Minesweeper's npm lockfile retains dependency
integrity digests; top-level archive sizes/SHA-256 values are pinned in
`assets/addons/downloads.json`. Changed downloads fail closed. Installed copies
retain notices and sources.json. Private runtimes are pinned, not automatically
updated; refresh their tested versions before future public releases.

Programs: `~/.local/share/mintxp-addons/APP/`. Saved preferences, games and Paint
autosaves: `${XDG_DATA_HOME:-~/.local/share}/mintxp-addon-data/APP/`. Chosen drawing
files are stored at the location selected by the user. A cancelled native Save
dialog keeps the drawing unsaved; completion is acknowledged only after WebKit
finishes writing the download. Local application HTTP
servers bind loopback only, expose only application assets and use a private
persistent token/origin. Complete uninstall removes manager-installed accessories by default;
independently installed applications and saved data remain. The CLI option
`uninstall --yes --keep-addons` retains manager-installed accessories as well.
Individual accessories can also be removed on this page. Their
backup journals remain under the theme state directory's `addons/APP/` tree.
Removal keeps application data and stops on edited program files.

The `xp-community-minesweeper.desktop` and `xp-community-solitaire.desktop`
launchers from previous personal installations are detected without importing
their files into the public package. Shared Flatpak runtimes and its remote
remain on uninstall. An interrupted Flatpak operation with uncertain ownership
can be reconciled as external/protected; it is never deleted by guessing.

```sh
./install.sh                          # open the assistant
python3 -B launch.py addons           # inspect detected/managed applications
python3 -B launch.py addon-install --addon jspaint --yes
python3 -B launch.py addon-verify --addon jspaint
python3 -B launch.py addon-open --addon jspaint
python3 -B launch.py addon-remove --addon jspaint --yes
python3 -B launch.py addon-recover --addon jspaint --yes
python3 -B -m unittest discover -s tests -p test_addons.py -v
```

Other IDs: `minesweeper`, `solitaire`, `space-cadet`. For Flatpak recovery use the
same command with its ID. Restore/removal is independent of the desktop theme.

The new specialist licence/build explanations currently have German and English
text; other manager languages display the English fallback for this new page.
The existing translated manager pages are unchanged.

Preview 15 labels the existing Space Cadet Flatpak **3D Pinball** in the XP
Start menu. **Paint - JS Paint** appears under both Accessories and Graphics,
using the bundled original palette icon. These menu changes do not replace
or modify the system Flatpak application.

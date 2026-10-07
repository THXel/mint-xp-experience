# Mint XP Experience

A reversible XP-inspired desktop package for **Linux Mint 22.3 Cinnamon / Cinnamon 6.6.x**.

**Preview 0.1.0-preview.38:** test in a spare user account or VM before distributing as a stable release. No Microsoft affiliation. No Windows binaries, fonts, original wallpaper or Microsoft sound recordings are bundled. No soundpack is bundled. Without an explicitly selected sound source, existing sounds remain unchanged.

The first GitHub release is a **pre-release**, not a stable release. See [verified results and remaining limits](docs/RELEASE.md) and the [post-release roadmap](docs/ROADMAP.md).

## Start

Download the DEB from [Releases](https://github.com/THXel/mint-xp-experience/releases), install it with Linux Mint’s package installer, then follow the setup assistant. Original Microsoft assets are optional private imports; the included icons work without an ISO and existing sounds stay unchanged.

For the source archive:

Extract the release, open a terminal in this directory, then run:

```sh
python3 -B launch.py
```

The DEB opens the first-run assistant in an active local graphical user session, with a one-time Cinnamon login fallback. The Welcome page lists components below Install everything / Install selected. The assistant and later theme settings have separate navigation; language changes preserve the current selection. The first-run assistant lets you choose components and review the changes. It saves an immutable preinstallation baseline before applying anything. Run as your desktop user, **without sudo**. After installation, open **Mint XP Experience** from the application menu or the XP Control Panel. Sign out/in later to load changed applets; the installer never closes your applications.

Required (normally already installed on Mint): Python 3, python3-gi, gir1.2-gtk-3.0, dconf-cli, desktop-file-utils, fonts-liberation. Explorer preview formats depend on installed system thumbnail/preview tools. Selected accessories are downloaded only after the installation review; there is no telemetry or background updater.

## Included

- Locally customised B00merang GTK/window theme, Cinnamon panel/dialog theme and CinnXP cursors.
- XP Explorer with folder tree, file actions, MIME-dependent menus, previews, storage capacity bars and file-reveal support. The XP-style Search Companion opens inside the same Explorer, with categories, filters and results beside it.
- Optional brief Welcome screen after login, plus separately authenticated boot/login theming with root-protected rollback. See [Boot and login](docs/SESSION.de.md).
- XP Control Panel with categories, search, favourites and the new theme manager.
- Optional patched Cinnamenu and grouped window list: XP home/flyout structure, orange attention indication, window actions at the bottom and Close last.
- Optional generated landscape wallpaper, readable Liberation fonts, taskbar size, existing sound-theme integration and existing classic-game integration.
- First-run selection, per-component uninstall, backup/restore, integrity checks, interrupted-operation recovery and preserved preinstallation values across updates.
- Manager/assistant UI in **14 languages**, chosen from the OS locale or manually. See the honest coverage statement in [TRANSLATING.md](docs/TRANSLATING.md); older Explorer and Start menu text is not yet fully translated.

## Safety and recovery

Backups are private under `${XDG_STATE_HOME:-$HOME/.local/state}/mint-xp-experience/`. Before the first change, reference copies of Cinnamon/GTK/Nemo settings, active local themes, icons/cursors, sounds, panel configuration, wallpaper and readable LightDM settings are saved. Every modified file and setting additionally has an exact per-item original in the transaction journal. Explicit/default GSettings values are distinguished. A reference copy is not a whole-system backup.

Uninstall restores only items managed by the package. It preflights **all** items before writing, blocks on later edits, keeps unrelated files, and retains backups. Existing XP tweaks are the baseline when installed on an already customised desktop; the package cannot invent a pre-XP snapshot. Earlier standalone backup folders must be kept.

```sh
python3 -B launch.py status
python3 -B launch.py verify
python3 -B launch.py backup
python3 -B launch.py uninstall --yes
python3 -B launch.py recover
```

Explorer keyboard shortcuts, networking and tested limits: [Explorer guide](docs/EXPLORER.de.md).

See [German introduction](docs/INSTALL.de.md), [Recovery](docs/RECOVERY.md), [Games](docs/GAMES.md), [Licenses and sources](docs/SOURCES.md), [Release checklist](docs/RELEASE.md).

## Deliberate preview boundaries

Boot/login theming is an explicit, separate administrator operation with its own backup and undo. The uninstall action now restores that system component with an administrator prompt before removing the user package; user installation itself stays unprivileged. See [Boot and login](docs/SESSION.de.md). Original XP sound files and the B00merang XP icons are optional local imports, not distributed here (the icon repository carries GPL-2.0; inherited artwork provenance still requires review). Games and JS Paint are optional, separately managed upstream downloads; existing games and the preferred Space Cadet Flatpak are detected and protected. See [Games and accessories](docs/GAMES.md). Existing panel positions, pins and other applets are preserved. Applet replacement is opt-in and restricted to Cinnamon 6.6.x.

## Update

Download and review a new release, open its `launch.py`, and apply the desired selection. Existing originals remain the baseline. Locally edited managed files cause a conflict rather than being silently overwritten. There is intentionally no unverified automatic download/update channel before a public repository and signed releases exist.

## Development

```sh
python3 -B -m unittest discover -s tests -v
```

Project code: GPL-3.0-or-later. Upstream code keeps its own compatible notices; see `licenses/` and `docs/SOURCES.md`. Feedback and translation reviews are welcome. This is a community recreation, not a Windows compatibility layer.

## Preview 4

Adds coordinated system/user uninstall, component status, configurable Welcome
with preview, shared language selection, an allowlisted local diagnostic export,
and a retained text-console rescue command. See [recovery](docs/RECOVERY.md),
[language coverage](docs/TRANSLATING.md), and [boot/login](docs/SESSION.de.md).
See the later [VM acceptance results](docs/VM-RESULTS.de.md) for actual reboot
and rollback coverage; unit tests alone do not establish these results.

## Preview 5

Refines the Luna Start button with the existing theme artwork, stronger italic text,
a darker text shadow and distinct normal, hover and pressed states. Uses Trebuchet
MS when available, with the system font fallback otherwise; no font files are bundled.

## Preview 6

Adds an optional XP notification-area chevron. Expand/collapse icons inline, keep
favorites visible, or show all icons permanently. Right-click the chevron and choose
Customize icons to drag entries between the two areas. Clock and Show Desktop remain
visible. The original tray actors keep their normal application actions. Installation
backs up panel settings; deselecting the component restores the prior configuration.
See [notification-area guide](docs/TRAY.md) for details and limitations.

## Preview 7

Refines the XP chevron and adds a subtle separator between expandable icons and
favorites. Drag icons directly in the panel or in customization: a visible ghost
and insertion marker show the destination. Favorites and ordering persist across
applet/session restarts. Native actor ownership is preserved, and temporary visual
positions are restored on removal. The Start button has eight more pixels of
space to the right of its label. See the current VM acceptance report for reboot coverage.

## Preview 8

Replaces the tray text glyph with original scalable chevron artwork and removes
the inherited full-height applet background in normal, hover and focus states.
A read-only VM preflight and [clean-Mint test guide](docs/VM-TEST.de.md) prepare
installation, reboot and uninstall acceptance. No VM reboot or clean-VM acceptance
is implied by the existing host tests.

## Preview 9

Fixes issues found in a fresh Mint VM: clipped Start-menu entries, optical/removable
media classification, task-list icon sizes outside the centre panel zone, and the
restart-icon fallback. The menu also remains usable at 800×600.
See [the dated VM report](docs/VM-RESULTS.de.md) for verified results and remaining
limits; this is still a preview release.

## Preview 10: first-install polish

Includes the selected AI-assisted landscape, 109 original glossy icon names and a bundled four-petal Start emblem. The optional icon component inherits existing application logos from Mint. The manager displays actual counts for the current preparation/backup/write/verification phase; unknown work pulses and completion is shown only after verification. Explorer has action-specific paper animations for copying, moving, trashing, permanent deletion and restoration, with reduced-motion support.

## Preview 11: optional games and JS Paint

The assistant adds a Games and accessories page for Minesweeper XP, Solitaire,
JS Paint and the Space Cadet Flatpak. Existing installations are protected.
New local installs have separate backup journals and removal; saved data stays.
Minesweeper builds its pinned frontend for Mint WebKit 4.1, Solitaire uses private
Temurin Java 8, and JS Paint uses local static files with Mint WebKit instead of
bundled Electron. Downloads are explicit and include source/licence notices.
Third-party application payloads are not included in the public source archive.
See [details and targeted checks](docs/GAMES.md).

### Preview 12: lokale XP-Sounds

Die Seite **XP-Sounds** importiert ein eigenes WAV-Soundpack privat, übernimmt
Cinnamon-Ereignisse und bietet Vorschau, Testton, Integritätsprüfung und Sound-Undo.
Original-Sounddateien werden nicht mitgeliefert. [Anleitung und Grenzen](docs/SOUNDS.de.md).

## Preview 13: assistant polish

Single-width XP scrollbars with reserved space, progress visible only while a job is running, and a clear preflight notice before testing or undoing sounds without an active import. Targeted native GTK checks passed in the Mint VM; see [current verification and remaining release work](docs/VM-RESULTS.de.md#aktueller-freigabestand-nach-preview-13).

## Preview 14: classic games and Paint in the Start menu

The XP menu now includes installed Minesweeper, Solitaire and Space Cadet under
Games → Windows XP Classics, including Cinnamon Flatpak desktop IDs. JS Paint
is under Accessories and uses an original CC0 palette-and-brush icon in the
classic desktop style. Menu files are included with the XP menu component, so
installing the optional applications later also populates the groups. Duplicate
parent entries are filtered without hiding their submenu entries.

## Preview 15: local archive import

Personal PCM WAV soundpacks can be imported from folders and supported archives. The formerly bundled soundpack was removed in Preview 30.

## Preview 16: DEB, sound audition and completion page

Install the DEB with Mint's package installer, then launch **Mint XP Experience**
from the menu. Installing the DEB itself does not change desktop settings. The
assistant selects components and backs up the current desktop before applying
them. **Completion** shows enabled/unselected components, the backup location,
transaction ID and whether logging in again is recommended. Ambiguous sound
candidates have a **Listen** button and previews stop when the dialog closes.

Updates to the DEB supply a newer assistant. Open it and apply your selections
to update the user installation; an existing managed local launcher delegates
to the installed DEB. Restore the desktop under **Uninstall** before removing
the DEB. Backups and the independent recovery copy are retained.

[DEB installation and manual test](docs/DEB.de.md). Supported target: Mint 22.3,
Cinnamon 6.6.x, X11. This remains a preview; see the outstanding acceptance and
asset-provenance items before wider distribution.

## Preview 18 setup

Install everything selects desktop components, Minesweeper, Solitaire, 3D Pinball, Paint - JS Paint, boot and login appearance. Downloads and their upstream notices appear in the review; system appearance uses the native administrator prompt and its own backup. Failed or cancelled extra stages are listed as incomplete, while successful desktop changes remain recoverable. Existing games are protected.

The Explorer creates My Computer on an existing user desktop directory and becomes the first pinned application without rearranging other favourites. Pin backup/restore manages only that field, preserving other applet settings. Sound-test success uses the status bar, with errors still reported. Session dialogs use blue XP-inspired styling and original project action tiles; native cancellation and unsaved-work handling remain intact.

Existing local XP icon packs are preferred, with project icons as fallback. Microsoft original icons and sounds are not bundled or automatically downloaded; see [source and rights notes](docs/SOUND-SOURCES.de.md).

### Preview 19 — early authentication and overall progress

When boot/login is selected, its backed-up system installation runs first. Cancelling authentication stops the workflow before desktop changes or downloads. One overall progress bar counts completed stages, with current operation/download size beneath it; failed optional stages remain explicitly incomplete. No password is stored and no privilege keepalive is used.

### Preview 20 — compact setup and private XP media import

A grouped three-column overview replaces the long component list. Icons/ISO, sounds and options have separate compact pages; technical details remain available on demand. Sound selections can be previewed before installation without a success popup.

A local Windows XP installation ISO can supply sounds and common shell icons, subject to the user having the necessary rights. The importer reads I386/AMD64 resources as data in a bounded worker; it neither mounts media nor executes Windows programs. Extracted files stay in private user state and never enter this distribution. See [ISO import](docs/ISO-IMPORT.de.md).

The included alternatives use original perspective vector artwork, native 16/24/32/48-pixel exports. No transcribed Windows melodies or Microsoft artwork are included.

## Preview 22: guided media selection and original Mint sounds

Welcome now starts with language and media selection. Choose the included icons and unchanged existing sounds, a local XP ISO, or a folder/archive. Setup controls remain
locked until that decision is complete. A supported ISO selects both imported
icons and sounds automatically. Packs are inspected before selection; if only
one type is found, a Yes/No question offers the missing pack or the included
alternative. Cancelling the second picker keeps the decision pending.

Native icon themes and loose PNG/SVG/ICO/XPM collections are supported. Common
Windows icon names receive Linux aliases; names that cannot be mapped may not
appear in applications. Multiple themes/ambiguous variants require choosing a
specific folder. Archives with links, encrypted/multipart archives and external
SVG references are rejected. Imports run with resource limits and remain private.

XP-Sounds also offers original Linux Mint sounds from the installed system.
Switching uses the same backup/undo transaction as other sound choices, without
bundling distribution audio. ISO/pack import grants no additional usage rights.

## Preview 30: media switching and safe panel rollback

No sounds are bundled. Without a selected soundpack, existing sounds remain unchanged.
Media can be imported after installation; bundled/imported icons can be switched independently.
Valid Cinnamon panel reindexing and personal placement changes no longer block rollback;
unrelated file edits remain protected. Setup explains clicks on disabled install buttons.

## Preview 31: applet review and isolated XP Start menu

The installer lists additional menus and unverified third-party applets before
changes. All are checked for the explicit disable action; a separate Keep all
button preserves every applet. No applet is uninstalled. The XP menu uses its
own UUID and settings, leaving the user's Cinnamenu intact. Panel changes after
review require reviewing again. Rollback restores disabled applets and preserves
later user additions. The setup header uses the project's existing Mint XP logo.

## Preview 32: media import after applet review

Applying ISO/folder/archive media uses only media-related inputs. Saved applet
disable choices no longer enter the icon plan or block later media imports.
Panel choices remain recorded for rollback; media switching leaves them intact.

## Preview 33

After the first installation the assistant immediately changes to the settings
overview. Icons, sounds, components and recovery have separate entry points.
The Icons & XP ISO page has fixed **Install icons** and **Install icons and sounds**
buttons; XP Sounds has its own **Install sounds** button. Selecting media prepares
it for review, without applying it. Existing sounds stay unchanged when selected.
Language switches preserve the selection. No repeat desktop installation is needed.

## Preview 34

Folder-default management now merges only `Default Applications/inode/directory`
inside `mimeapps.list`. Later personal associations and explicit alternate file
managers survive media updates and uninstall. Ambiguous folder defaults, linked
paths, damaged backups and concurrent edits remain protected. No unrelated
application associations are normalised or removed.

Media pages show installed and selected choices, pending changes and PNG icon
previews. Media confirmations state their scope. Backups show local dates and
reasons; restore reviews the selected theme components. All new manager labels
are translated into the 14 supported languages. See [Preview 34](docs/PREVIEW34.md)
for validation scope and remaining live-VM acceptance work.

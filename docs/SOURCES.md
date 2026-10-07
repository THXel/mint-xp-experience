# Sources, licences and changes

This package is an aggregation. Upstream assets and modules retain their licences and attribution. Newly written manager/installer and XP Explorer/Control Panel code is offered under GPL-3.0-or-later. No ownership of Windows branding or third-party logos is claimed.

| Component | Source | Licence / provenance |
|---|---|---|
| GTK/window theme and base Cinnamon art | [B00merang Project Windows-XP](https://github.com/B00merang-Project/Windows-XP) at `7637830906823af40a3cd7e7079be753d8b7d679` | GPL-3.0; original licence in `licenses/`. Locally changed geometry, buttons, menus, dialogs and sidebar styling. |
| Cursor binaries and sources | [ndwarshuis/CinnXP](https://github.com/ndwarshuis/CinnXP) at `b24e8a68de394d65cfa6fcb6aaa577f68207908b` | GPL-3.0; corresponding cursor PNG/config sources under `sources/cursors/`. Cursor aliases materialised; upstream scripts retained. |
| Start menu | [Cinnamenu](https://github.com/linuxmint/cinnamon-spices-applets/tree/master/Cinnamenu%40json), installed version 5.4.14, 5.8 compatibility directory | Derived from Cinnamenu/Gnomenu/Mint Menu; GPL notices retained, GPL-2 text included. Original authors and other contributors are credited in `assets/menu/5.8/CREDITS`. Local XP home, flyouts, session dialog and navigation changes are marked. Snapshot files are pinned by the release manifest. |
| Taskbar | [Linux Mint Cinnamon](https://github.com/linuxmint/cinnamon/tree/master/files/usr/share/cinnamon/applets/grouped-window-list%40cinnamon.org), installed Cinnamon 6.6.9 | GPL-2.0; source included. Local attention styling/integration and native window menu ordering modifications. |
| Emoji keywords in Cinnamenu | [muan/emojilib](https://github.com/muan/emojilib) | MIT; notice in `licenses/emojilib-MIT.txt`. |
| Generated landscape wallpapers | Mint XP Experience | CC0-1.0; original SVGs plus the selected AI-assisted PNG. Provenance and fingerprint in `assets/wallpapers/LICENSE.txt`. These are not Microsoft's original Bliss photograph. |
| Fonts | System Liberation fonts | Used from the installed OS, not redistributed in this archive. |

The pinned theme and cursor revisions are recorded in the table above. The complete release source/assets have a generated `MANIFEST.sha256`; no installed settings/backups are included.

The [B00merang-Artwork Windows-XP icon repository](https://github.com/B00merang-Artwork/Windows-XP/blob/master/LICENSE), including reviewed commit `24e95ad2b12c55dd11883ee7066525527d944039`, contains a GPL-2.0 licence. Earlier preview documentation incorrectly said it had no clear licence. The provenance of inherited artwork still needs separate review; a repository licence cannot grant rights its contributors do not hold. It is **not bundled**. A user's own icon theme can be imported locally and never enters the release source. Original XP sounds and Microsoft fonts are also excluded. Game source licences do not automatically license separately required game data; optional game/application payloads are downloaded separately with their upstream notices; see [Games and accessories](GAMES.md).

Some upstream Cinnamenu icons identify third-party search providers. Their original credits are retained. Before a stable public release, review the inherited upstream artwork/branding and complete per-file licence provenance where upstream notices are ambiguous. The archive is a reviewable preview, not a claim that every third-party trademark is owned by this project.

Preview 10 adds original CC0-1.0 vector icons and a four-petal Start emblem. Editable, reproducible source: `tools/build_icons.py`; licensing: `assets/icons/LICENSE.txt`. These do not use Microsoft icon binaries or the Windows flag. Application logos not provided by this theme come from the existing installed icon themes.

## Sound imports

No sound recordings are distributed. Users can import their own licensed local media.
The importer reads archives with the system libarchive library.

## Preview 16 review boundary

The pinned JS Paint source licence was rechecked against its MIT notice; the
SpaceCadetPinball engine remains MIT, while the Flathub recipe still fetches
original game data as extra-data. Neither result grants blanket artwork rights.
Bundled GTK/Cinnamon/cursor licences and Cinnamenu/taskbar notices are retained.
Per-file provenance of inherited art cannot be independently established from
these repository licences alone. This remains a documented publication review
item; the DEB is a test preview, not legal clearance. Original Microsoft sounds
and optional downloaded application payloads remain absent from the release.

The Debian package uses no maintainer scripts to touch users' home directories
or activate themes. See [Debian maintainer-script policy](https://www.debian.org/doc/debian-policy/ch-maintainerscripts.html).

Preview 18: `assets/menu/5.8/session-icons/*.svg` are original geometric action tiles created for this project under CC0-1.0. No Microsoft icon bitmaps are included. Existing local packs remain private imports.


## Search Companion (Preview 35)

The penguin is original procedural Cairo artwork implemented in
`assets/xp-explorer/search_companion.py`, under the project's GPL-3.0-or-later
licence. No third-party mascot frames are distributed.

`mintxp/agent_character.py` is an original bounded ACS2 decoder based on
[Remy Lebeau's MSAgent Character Data Specification](https://uploads.s.zeid.me/ms-agent-format-spec.html).
Microsoft's [Agent animation documentation](https://learn.microsoft.com/en-us/windows/win32/lwef/creating-animations)
describes the character/animation model. No third-party decoder source was copied.
Rover can be read from a user's own supported XP ISO into private local state.
His images, sounds and ACS binary are excluded from the source and DEB releases;
importing does not grant a redistribution licence. Only linear image-frame
sequences are played; Microsoft Agent branching, scripts and speech are not run.

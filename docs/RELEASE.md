# Preview release validation

## Current candidate: Preview 38 (7 October 2026)

- Preview 36 was installed in the Mint 22.3 VM, rebooted, checked for integrity, completely removed, and checked against the original baseline. Nemo remained installed. The tested Preview 36 state was restored afterwards.
- Resuming the VirtualBox RAM snapshot stalled the guest; cold-booting the same saved disk state succeeded. This is recorded as a test-environment limitation.
- Preview 37 embeds the Search Companion in the Explorer. Its general suite recorded 236 tests: 210 passed and 26 skipped; 15 targeted Explorer GUI tests passed separately, including six for the embedded search.
- These counts do not establish a new Preview 37 boot/uninstall test. Networking needs a reachable server and credentials; sound playback still needs audible confirmation.
- The package manifest and Python payload were checked. Original sounds and privately imported character frames are absent from the public package.
- Preview 38: 237 tests ran, 234 passed and three opt-in GVfs trash tests were skipped. Shared GTK application registration emitted warnings in the combined run; all 23 GUI checks passed again in separate processes (eight installer and 15 Explorer checks), without those registration errors.
- Preview 38 adds an update/update/uninstall regression for absent native menus, explicitly disabled applets and later user-added applets. It retains the intended panel separately from merged personal additions, preserving them across repeated updates and uninstall.
- First publication should be marked **pre-release**. CI is prepared; a GitHub run is not implied by local tests.

Earlier entries below describe their historical scope, not the current test status.

Before a stable release:

1. Install selected combinations in a clean Linux Mint 22.3 Cinnamon VM, including opt-in menu/taskbar replacements. Confirm applet reload on a fresh login.
2. Verify visual behavior and original-state uninstall in that fresh session. The automated temporary-home test validates real installed schemas with the in-memory GSettings backend; it does not prove a clean-machine live desktop.
3. Complete legacy Explorer/Start-menu localisation and native-speaker review of new manager catalogues.
4. Complete licence provenance review of inherited applet art and search-provider branding.
5. Test the explicit system boot/login installer and its private rollback on a clean Mint VM, including actual boot, autologin, disk-unlock prompts and post-kernel-update conflict handling; nested UI previews cannot establish those results.
6. Pin the source revision, create release hashes and publish from the reviewed tree only. Never add local state, backups, screenshots of personal data, or old XP-Setup work directories.

`tools/build_release.py` uses an explicit allowlist, rejects symlinks and personal absolute paths, builds a source archive plus SHA-256 file, and includes corresponding sources. CI unit checks complement the manual VM test; they cannot replace it.

## Earlier manager-only validation on 2026-10-04

- 21 automated tests passed, including complete package install/update/uninstall/reinstall in a temporary home with real GSettings schemas and the memory backend.
- Optional menu, taskbar, wallpaper, sounds and default-folder integration passed isolated rollback checks.
- Interrupted writes, corrupt backup objects, later file edits, linked paths, concurrent operations and failed updates were exercised.
- Every manager page rendered in all 14 catalogues (84 page/locale combinations); German and installed English screenshots were visually inspected; a Japanese screenshot was also captured. This does not constitute native-speaker translation review.
- The manager-only installation was verified on the existing Mint 22.3/Cinnamon 6.6.9 desktop. The real Control Panel entry, keyboard launch and temporary desktop shortcut worked.
- Existing desktop theme, Explorer, Start menu/taskbar, panel configurations, sounds and Cinnamon settings were fingerprint-checked before/after integration; no changes were made to those components.
- The CI workflow is prepared but has not yet run on GitHub. A clean-VM live install/uninstall is still outstanding.

## Explorer update in preview.2

Explorer 1.6 adds confirmed permanent deletion and empty-trash actions, grouped session undo, standard keyboard shortcuts and native GVfs server authentication. See [the detailed test matrix and limits](EXPLORER.de.md). The earlier manager-only preservation statement describes preview.1; preview.2 deliberately updates Explorer. The public test suite adds ten regression cases, three requiring an explicitly enabled desktop trash session.

## Session appearance in preview.3

Optional user-local Welcome, generated original boot/login art, and an explicitly authenticated system installer with exact backups. The user installer does not run root operations. Validate a real reboot before calling hardware boot behavior verified. System UI is currently German/English; Welcome greetings and component labels support the 14 manager locales.

## Preview 9 VM acceptance

Fresh-VM findings, fixes and exact verification limits are recorded in [VM-RESULTS.de.md](VM-RESULTS.de.md). Earlier manager-only results above describe that earlier scope.

## Preview 38

Fixes an upgrade case found on the existing Mint desktop: an old baseline menu absent from both the last managed panel and the current panel must not reappear. Explicitly disabled applets can still be restored through applet review, and uninstall retains its original baseline semantics.

# Preview 34 – media clarity and reversible defaults

## Acceptance matrix

The final test counts and hashes are recorded alongside the local build output.
Automated profile tests use temporary home directories and an in-memory GSettings
backend. They do not demonstrate real login, boot, restart, or audible playback.

- Fresh profile installation without media: preserves existing sounds.
- Add a real user-provided XP ISO later: extract icons and sounds, then apply.
- Switch bundled/imported icons independently of sounds.
- Restore a dated media backup, update, then uninstall the desktop components.
- Preserve later personal file associations throughout that sequence.
- Reproduce current-host media upgrade using a private clone of its state.
- Cancel GUI changes, retain pending choices across language switches, and show
  restore scope and dated backup reasons.
- Check light/dark windows at 1080×720 and narrow windows at 800×600; action bars
  stay outside the scroll area. Small screens may scroll page content.
- Reject ambiguous folder defaults, linked paths, corrupt objects and concurrent
  MIME changes before the transaction writes managed data.

## Still required before a public stable release

Run the real VM checklist in VM-TEST.de.md using the built DEB, including administrator
authentication, boot/login appearance, an actual restart and desktop rollback.
The Mint VM was powered off while this preview was prepared; no VM snapshot was
reset. Three explicitly enabled live-GVfs trash tests are excluded from routine
unit tests. No claim of complete hardware or third-party applet compatibility is made.

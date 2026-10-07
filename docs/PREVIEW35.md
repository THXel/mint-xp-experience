# Preview 35 – Explorer and Search Companion

This release focuses on file-manager comfort and the XP-style search sidebar.
See EXPLORER-COMFORT.md for controls, limitations and private ISO import details.

Validation uses temporary files/profiles and an in-memory settings backend:

- Filename/category/date/size search, symlink avoidance and cancellation.
- Selection/scroll retention, duplicate-favorite tree routing and folder zoom.
- Batch rename preview and undo; favorites reorder and concurrent-write checks.
- Copy/move replacement, rollback on failure, changed-file protection and
  recovery after restarting the history object.
- Retry only failed files; search restart discards stale worker results.
- Actual local XP ISO: 26 sounds, 109 icon aliases, 29 Rover animations,
  703 rendered PNG frames plus manifest; private installation, switching and undo.
- Rendered GTK windows with the original penguin and privately imported Rover.
- Existing installer/media GUI workflow and package regression tests.

No host theme installation, boot/login change, VM reset or guest reboot is part
of this release's tests. Existing explicitly enabled live-GVfs trash checks remain
excluded. This is a preview for user testing, not a stable-release certification.
The new DEB updates the manager payload; use its component settings to update the
installed Explorer, and repeat the ISO import to add Rover to older imports.

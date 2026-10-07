# Backup, restore and interrupted operations

The engine writes a durable pending journal **before** changing any managed file or GSettings value. It holds an exclusive per-user lock. Files are atomically replaced, with mode preserved for restoration. Backups are content-addressed with SHA-256 and verified before restoration. The baseline records every target at its first managed change, including targets introduced in later updates. Deselecting a component restores its original targets. Explicit GSettings defaults are reset, not replaced by an approximate hard-coded value.

The `reference/` directory holds broad configuration snapshots for inspection/manual recovery, including readable LightDM files. They are not blindly loaded over a later user session. `baseline.json` plus `objects/` are the authoritative originals of package-managed files/settings. `current.json` describes expected installed state. `snapshots/` contains user-created checkpoints. `history/` retains completed transactions. Files are private to the user.

```sh
python3 -B launch.py verify
python3 -B launch.py backup
python3 -B launch.py restore --snapshot BACKUP_ID --yes
python3 -B launch.py uninstall --yes
```

When a process dies mid-operation, reopen the assistant and choose **Recover interrupted operation**, or run `python3 -B launch.py recover` from an extracted release. Recovery accepts each managed target only in the recorded before or after state. Unexpected third-party changes stop the entire recovery before writing anything. On recoverable runtime errors, rollback is attempted automatically; a failed rollback keeps the journal for recovery.

Do not delete the state folder. Do not modify JSON journals to bypass a conflict. Save external changes separately and reconcile them with the expected state shown in `current.json`; an administrator can inspect backups without running an uninstall. If an object is corrupt or missing, restore it from a separate copy before retrying.

Backups cover appearance and files changed by this package. They do not back up personal documents, full disks, installed packages, or a live filesystem atomically. Configuration snapshots may contain bookmarks and local names; never include them in public issues or release archives without review. A separate system backup remains independent.

The manager is removed during uninstall but its backup remains. To reinstall afterwards, run a release's `launch.py`: a new baseline is created for the new installation cycle; the preceding baseline is retained under `retired/`. An uninstall does not remove independently installed game Flatpaks or delete personal documents.

## Optional boot/login system installation

The manager and `launch.py uninstall --yes` now coordinate both scopes: check the user installation and backup objects first, authenticate and restore the system component second, and only then restore user files/settings. Cancelling authentication or failing the system step leaves the user installation in place. A per-user lock covers the complete operation. A system rollback followed by a user rollback failure can be retried; the system helper is idempotent. Its exact originals and rollback helper live in `/var/lib/mint-xp-experience-system`. Run `sudo python3 -I -B /var/lib/mint-xp-experience-system/appearance.py undo`. Later modified boot images or configuration files block rollback before mutation. Welcome is user-local and is handled by the ordinary package journal. See [session documentation](SESSION.de.md).

## Independent text-console rescue

Installation retains a small recovery copy beside the private backups, independent
of the GUI runtime. From a text console, sign in as the same desktop user and run:

```sh
~/.local/bin/mint-xp-rescue check
~/.local/bin/mint-xp-rescue recover --yes
~/.local/bin/mint-xp-rescue restore --snapshot BACKUP_ID --yes
~/.local/bin/mint-xp-rescue uninstall --yes
```

Choose the needed action; do not run every command blindly. Save work first.
Do not invoke the rescue command as root. Only the system step requests elevated
rights (polkit on the desktop, sudo in a text console). If the launcher is missing:

```sh
python3 -B "${XDG_STATE_HOME:-$HOME/.local/state}/mint-xp-experience/rescue/rescue.py" check
```

The recovery copy and journals are intentionally retained after uninstall. They
still depend on system Python/Gio and intact backup objects. `check` verifies
managed user state and backup objects; it does not authenticate a fresh boot/login
verification or prove that a real boot succeeds.

## Local diagnostics

The status page exports a new JSON file with version/platform, component states,
change counts and backup times. It contains no private paths, filenames, raw logs,
credentials or option values. Nothing is uploaded. An existing file or symlink is
never overwritten. CLI equivalent:

```sh
mint-xp-experience diagnose --output ./mint-xp-diagnostic.json
```

A system component without a fresh privileged verification is explicitly marked
unverified. Earlier baseline journals without creation timestamps show “not recorded”;
the UI never invents an original backup date.

# Session ending and folder launcher (Preview 25)

The pinned XP Explorer uses a folder icon and opens the personal folder with the tree sidebar. Explicit file/URI arguments still win over this default. The separate desktop Computer shortcut retains the Computer overview; Nemo remains installed and searchable.

Cinnamon retains shutdown confirmation, countdown, inhibitors, cancellation and the configured logout sound. A dismissible, time-limited blue decoration follows confirmation; inhibitors cancel it. The decoration does not initiate logout, change sound settings or force power-off. Native sound timing remains controlled by cinnamon-session; no duplicate recording is played.

When boot appearance is enabled, the system helper also installs a separate blue shutdown theme using Plymouth’s native two-step renderer. Poweroff/reboot service drop-ins select it only for the shutdown daemon, preserving the real kernel command line apart from this daemon’s theme choice. The startup theme, initramfs and bootloader are unchanged by this addition. The normal native password/text fallback remains available. Splash visibility depends on the normal splash kernel option and available graphics driver.

System additions have their own write-ahead journal under /var/lib/mint-xp-experience-system/shutdown. Later edits are protected. The existing system restore also removes these additions; original backups remain intact. Existing third-party Plymouth service overrides require review rather than replacement.

Preview without ending the session:

```sh
python3 -B ~/.local/share/mint-xp-experience/assets/session/shutdown.py --preview
```

Verify system installation:

```sh
pkexec /usr/bin/python3 -I -B /usr/share/mint-xp-experience/system/appearance.py verify
```

Native timing reference: https://github.com/linuxmint/cinnamon-session/blob/master/cinnamon-session/csm-manager.c (maybe_play_logout_sound). The design intentionally retains this behavior.

Plymouth native parameter and renderer verified against Ubuntu 24.004.60 source: https://archive.ubuntu.com/ubuntu/pool/main/p/plymouth/plymouth_24.004.60.orig.tar.xz (src/main.c find_override_splash; two-step ScaleBackgroundImage, per-mode Title and UseAnimation).

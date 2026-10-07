# XP notification area / XP-Infobereich

The optional **Collapsible XP notification area with favorites** component supports
Linux Mint 22.3 / Cinnamon 6.6 horizontal panels. It requires one panel containing
a native XApp or legacy tray on the right. Ambiguous multiple-panel installations
are left unchanged with an explanation. No Cinnamon system files are patched.

- Click the blue chevron to expand/collapse icons inline (150–170 ms animation).
- Right-click it and select **Customize icons…**.
- Drag icons directly in the expanded panel across the separator, or open customization.
- A ghost icon follows the pointer; a gold insertion line previews the drop position.
- Drag an entry to **Always visible** to keep it visible when collapsed. Drag it
  back to **Only when expanded** to hide it with the other icons.
- Clicking a row also switches its category. Native tray clicks still perform
  the application's actions; dragging works both in the panel and in the customization dialog.
- **Always show all icons** leaves the tray expanded permanently. In this mode,
  a left click on the chevron opens customization.
- The clock and Show Desktop stay visible. Network, sound, keyboard and power
  start as favorites. Inactive native indicators stay inactive.
- Favorites and ordering persist in Cinnamon's applet settings file (the UUID-named file for this single-instance applet). Favorite identities are retained
  when an application exits; the preference applies when it returns.
- New applications appear in the expandable area. Favorites are matched by app
  identity, not process ID. Multiple instances of the same application share a
  choice. Unidentifiable status-notifier processes may share a fallback identity.

The dialog follows the package language preference, otherwise the session language
(14 built-in languages, English fallback). Reload the applet or log in again after
changing the language. Application names come from the applications themselves.

## Deutsch

**Pfeil anklicken:** ein-/ausklappen. **Rechtsklick → Symbole anpassen:** Symbole
zwischen „Immer sichtbar“ und „Nur ausgeklappt“ ziehen oder durch Anklicken
verschieben. Direktes Ziehen in der aufgeklappten Taskleiste geht ebenfalls: links
der Trennlinie liegen die einklappbaren Symbole, rechts die Favoriten. Die
goldene Einfügelinie zeigt die neue Position; Escape bricht den Vorgang ab. „Immer alle Symbole anzeigen“ lässt den Infobereich dauerhaft offen.
Uhr und „Desktop anzeigen“ bleiben sichtbar. Favoriten werden gespeichert.

Die Theme-Verwaltung sichert die Panelkonfiguration vor dem Aktivieren. Die
Komponente lässt sich dort wieder abwählen; Sicherung/Wiederherstellung und
Deinstallation benutzen dieselbe geprüfte Rückrollfunktion. Spätere Änderungen
an verwalteten Einstellungen werden vor einem Überschreiben gemeldet. Die
persönliche Cinnamon-Appletkonfiguration bleibt beim Entfernen erhalten.

## Compatibility and checks

Native XApp, XEmbed/legacy and right-side Cinnamon applets retain their own actors,
menus and visibility signals. The component only folds their geometry/opacity;
removing/reloading it restores those properties. Original client actors retain their parents; temporary translations group the visible icons and are reset on removal. Panel edit mode unfolds icons.
Cinnamon internals can change; compatibility with other releases is not claimed.

Run `python3 -B -m unittest discover -s tests` from the source folder. Package
roundtrip tests use temporary homes and the memory settings backend. Desktop
acceptance must additionally exercise arrow clicks, native menus, dragging in
both directions, persistence after reload, and removal with original geometry.
No session restart or machine reboot is needed for this feature.

## Automatic collapse (preview 11)

When expanded, the tray collapses after 10 seconds without interaction in the
notification area (within one 250 ms timer tick). Pointer motion, clicks, scroll
and keyboard/touch activity in the tray reset the clock. Dragging, panel editing
and open Cinnamon/XApp/legacy popup menus postpone collapse and start a fresh
interval on close. “Always show all icons” takes precedence. The new auto-collapse
switch defaults on and can be disabled in the chevron menu; favorites and ordering
are unchanged. The timer uses monotonic time and disconnects on applet removal.

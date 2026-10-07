# Language support

The manager, Welcome, XP Explorer, XP Control Panel and XP Start menu now share the
private `preferences.json` language choice in the package state directory.
Supported selections: de, en, fr, es, it, pt, nl, pl, tr, ru, uk, zh (Simplified Chinese),
ja and ko. Automatic selection follows LC_ALL, gettext LANGUAGE preferences and
LC_MESSAGES/LANG; C/POSIX uses English. Regional variants map to a base catalogue.
Selecting a language does not change the operating system locale.

The manager changes immediately. Reopen Explorer and Control Panel, and sign out/in
for the applet to load the new choice. Save work before signing out. Welcome uses
the preference at its next launch. Native Cinnamon tools and installed application
names continue to use their own system translations.

Coverage is deliberately described separately from language selection:
- German is the original custom interface language.
- The English legacy catalogue covers the main interface, actions, categories and
  many error messages. It is the fallback for missing translations.
- The other twelve languages translate the manager's main pages, new controls and
  forty common legacy navigation/action labels. Longer legacy descriptions and
  some new explanatory notices still fall back to English.
- Technical recovery diagnostics remain English. Some less common legacy strings
  may still need extraction. Native-speaker review is pending; these are preview
  translations, not claims of complete linguistic coverage.

Manager catalogues are `locales/<code>.json`; explicit legacy string catalogues
are `locales/legacy/<code>.json`. Keep copies in both app asset `locales/` folders
and `assets/menu/5.8/locales/` synchronized. Do not translate schema keys, URI
schemes, desktop IDs, filenames or user data. Preserve numbered format placeholders.
Tests check selection, key coverage, template fields and catalogue copies.
RTL layout and Arabic/Hebrew support need separate work and are not advertised.

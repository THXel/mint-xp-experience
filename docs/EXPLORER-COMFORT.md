# Explorer comfort (Preview 37)

Navigation keeps the branch chosen in the folder tree. Duplicate URIs in Favorites no longer pull Downloads out of the home branch. When no branch was explicitly chosen, home locations prefer the home tree. Explicitly selected favorites retain their branch.

Favorites are shared with GTK/Nemo. Ctrl+D adds the current folder; Favorites → Manage favorites edits labels, removes shortcuts or changes their order. Removing a favorite does not delete files. Live file monitoring updates open trees. Writes use GIO etags and reject concurrent modifications; creating the bookmarks file is exclusive.

F2 selects the filename without its final extension. After renaming, the renamed item remains selected; Ctrl+Z retains the existing undo protection. Newly created folders and text files are selected too.

Search / Ctrl+F / F3 opens recursive filename search. Subfolders are optional; patterns such as *.pdf work alongside partial names. Results can be sorted and their containing folder opens with the result highlighted. Ctrl+Shift+F filters the current folder; Escape clears and closes that filter. No content indexing or additional background service is installed.

The new labels have translations for the existing 14 language choices (German source plus 13 catalogues). GUI hotkey tests use a private clipboard selection and an isolated bookmarks file, with test files only. User clipboard data and personal favorites are not accessed by the write tests.


## Preview 35

- Back/forward and refresh keep multiple selections and scroll position in the
  current window (up to 100 locations). Explicit toolbar/address/favorite
  navigation prefers the home tree; an actual tree click keeps that branch.
- Icon zoom (32–128 px) is saved per folder, together with view, sorting and detail
  column widths. Use the footer buttons or Ctrl plus/minus.
- F2 on multiple files opens a preview with `{name}`, `{n}` and `{n:03d}` patterns.
  Extensions are kept by default. Duplicate/occupied names stop the operation;
  no two-phase name swapping is attempted. Successful renames form one undo group.
- Manage favorites accepts folders dragged from file managers. Drag an existing
  favorite to reorder it. Remote favorites are not contacted while editing them;
  opening them uses the normal asynchronous GIO mount/authentication path.
- The Search Companion offers all files/folders, pictures, music, video,
  documents and folders-only categories; filename/glob matching, date and size
  filters, hidden files and optional recursion. This is filename/metadata search,
  not full-text indexing. Search can be cancelled/restarted; results reveal the
  exact file in its parent folder. Symlink directories are never traversed.
- The original procedural penguin supports waiting, searching and result states.
  Animations can be disabled; the preference survives restarting the Explorer.
- A newly imported supported XP ISO may provide Rover from I386/AMD64/rover.ac_.
  A bounded ACS reader exports image frames locally, without executing Windows
  code, speech or scripts. Original artwork is never included in releases.
  Existing ISO imports must be repeated once to obtain the new companion data.
  Applying imported icons also installs the private companion. Since Preview 36,
  switching icon themes preserves that private companion. The search window
  independently offers automatic, dog, penguin and no companion. Original
  import files remain in private state. Unsupported/missing Rover uses the penguin.
- Conflicts offer skip, keep both, and explicit replacement of local regular files.
  Directories, symlinks and network targets cannot be replaced. Preview 36 adds
  explicit merging of local directories; other targets offer keep both.
  Replacement moves the original into a hidden `.xp-replaced-*` sibling folder,
  with an index in `~/.config/xp-explorer/replacements`. Ctrl+Z restores it during
  the session, or Extras → Restore replaced files works after restarting.
  Changed files stop restoration. Backups are retained until restored; they are
  not silently pruned when the undo history expires. Preview 36 can resume interrupted restore steps when the recorded identities
  still match. A separate rescue-copy action preserves the current file when
  those checks fail; no file is overwritten to resolve a later conflict.
- A failed copy/move does not repeat successful files: the result dialog offers
  retry for the failed subset. Skipped conflicts remain skipped.

## Preview 36

- Recent search names and locations are stored locally (at most 12 each), with
  a clear-history action. Credential-bearing locations are excluded. Reset
  filters preserves the chosen name and location. During search, the current
  directory and result count are shown.
- Search companion preferences are independent of the icon theme. Both the
  companion context menu and the controls below it update immediately; the
  choice and animation setting survive restarting.
- Conflict dialogs show both paths, sizes, modification dates and bounded local
  image previews. Explicit local folder merges retain unrelated files, ask about
  leaf conflicts and form one undo group. Directory symlinks are not traversed.
  Remote merges are deliberately unsupported; normal remote browsing remains.
- Recovery lists backup dates, space used and whether restoration is safe.
  Recovery journals are written atomically; interrupted staging can resume after
  validation. Additional rescue copies never replace an existing file. Backups
  remain until recovered; there is no automatic expiry.
- Directory enumeration runs in a worker with a bounded result queue. The first
  batch appears early, and final sorting/rendering is spread across UI frames.
  Late results cannot replace a newly navigated folder. The local thumbnail
  cache uses source identity, a 256-item memory limit and periodic disk pruning
  to about 512 entries / 32 MiB (up to 31 additional writes between prunes).
- The 100 labels listed in explorer-preview36-keys.json cover the new search,
  companion, conflict and recovery surfaces, including earlier Preview 35 gaps,
  in all 14 language choices. Placeholder and catalogue-copy checks are automated.
  This does not claim native-speaker review or complete translation of every
  older application screen; older missing entries still use English fallback.


## Preview 37: embedded XP Search Companion

The Search toolbar button toggles the companion in the existing Explorer's left
pane; results occupy the existing right pane. No additional search window is
created. Ctrl+F and F3 open/focus it. The initial category links lead to a form
with filename, location and collapsible date, size and advanced options. A
speech-card tail, selectable companion and faint magnifying-glass watermark
follow the XP references. This remains filename/metadata search; no unsupported
file-content field, people directory or web-search link is presented.

The close cross, Search toggle and Back return to the prior folder view. Folders
returns to the folder tree. Opening a matching folder or revealing a result's
parent navigates in the same Explorer and selects the matching file. Escape
first cancels an active search; otherwise it closes the pane, including from
an input field. Late search/listing callbacks cannot replace later navigation.

Search results retain Open, Open containing folder and Copy (Ctrl+C). Ordinary folder mutations
and view controls are disabled while search is visible so they cannot act on an
invisible selection in the previous folder. Copy and Properties use the selected
search result; New Window and Close remain available. Open the
containing folder to perform the normal file operations. Unrelated toolbar zoom,
preview and undo buttons are also disabled in this mode and restored on exit.

The seven new interface labels are present in all 14 language choices. The
original dog still requires a supported private ISO import and is never bundled.

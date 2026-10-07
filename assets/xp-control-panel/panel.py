#!/usr/bin/python3
"""XP-style settings index. All actions use installed Mint desktop entries."""
from xp_locale import t as _xp
import sys,unicodedata
from pathlib import Path
from preferences import Preferences,DEFAULT_FAVORITES,ALIASES,fit_geometry,create_shortcut
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,Gdk,Gio,GLib,Pango
BASE=Path(__file__).resolve().parent
CATEGORIES=[
 ('appearance',_xp('Darstellung und Designs'),_xp('Hintergrund, Fenster und Taskleiste'),'preferences-desktop-theme'),
 ('network',_xp('Netzwerk und Internet'),_xp('Verbindungen, Bluetooth und Datenschutz'),'network-workgroup'),
 ('software',_xp('Software'),_xp('Programme, Updates und Standardanwendungen'),'system-software-install'),
 ('sound',_xp('Sounds und Audiogeräte'),_xp('Lautstärke, Klänge und Benachrichtigungen'),'cs-sound'),
 ('hardware',_xp('Drucker und andere Hardware'),_xp('Maus, Tastatur, Drucker und Energie'),'printer'),
 ('users',_xp('Benutzerkonten'),_xp('Persönliches Konto und Anmeldung'),'system-users'),
 ('regional',_xp('Datum, Uhrzeit und Sprache'),_xp('Kalender, Sprache und Eingabemethoden'),'cs-date-time'),
 ('access',_xp('Eingabehilfen'),_xp('Bedienung, Lesbarkeit und Gesten'),'preferences-desktop-accessibility'),
 ('system',_xp('Leistung und Wartung'),_xp('Systeminformationen, Treiber und Sicherung'),'computer')]
ENTRY_ICONS={'cinnamon-settings-mouse.desktop': 'input-mouse', 'cinnamon-settings-keyboard.desktop': 'input-keyboard', 'cinnamon-settings-fonts.desktop': 'preferences-desktop-font', 'cinnamon-settings-calendar.desktop': 'preferences-system-time', 'cinnamon-settings-backgrounds.desktop': 'preferences-desktop-wallpaper', 'cinnamon-settings-display.desktop': 'video-display', 'cinnamon-settings-themes.desktop': 'preferences-desktop-theme', 'cinnamon-settings-power.desktop': 'system-shutdown'}
# Desktop entries are loaded from the OS directory, never a user-supplied command.
ENTRIES=[
 ('appearance',_xp('Anzeige'),_xp('Auflösung und Bildschirme'),'cinnamon-settings-display.desktop'),
 ('appearance',_xp('Designs'),_xp('Fensterrahmen, Symbole und Mauszeiger'),'cinnamon-settings-themes.desktop'),
 ('appearance',_xp('Desktophintergrund'),_xp('Hintergrundbilder auswählen'),'cinnamon-settings-backgrounds.desktop'),
 ('appearance',_xp('Taskleiste'),_xp('Panels und Anordnung'),'cinnamon-settings-panel.desktop'),
 ('appearance',_xp('Schriftarten'),_xp('Schriften und Textgröße'),'cinnamon-settings-fonts.desktop'),
 ('appearance',_xp('Bildschirmschoner'),_xp('Sperrbildschirm und Wartezeit'),'cinnamon-settings-screensaver.desktop'),
 ('appearance','Desktop',_xp('Desktopsymbole und Verhalten'),'cinnamon-settings-desktop.desktop'),
 ('appearance',_xp('Fenster'),_xp('Fensterverhalten und Titelleiste'),'cinnamon-settings-windows.desktop'),
 ('appearance',_xp('Effekte'),_xp('Animationen und Übergänge'),'cinnamon-settings-effects.desktop'),
 ('appearance','Applets',_xp('Erweiterungen für die Taskleiste'),'cinnamon-settings-applets.desktop'),
 ('network',_xp('Netzwerkverbindungen'),_xp('Kabelnetz und WLAN'),'cinnamon-network-panel.desktop'),
 ('network','Bluetooth',_xp('Geräte verbinden'),'blueman-manager.desktop'),
 ('network','Firewall',_xp('Netzwerkzugriffe verwalten'),'gufw.desktop'),
 ('network',_xp('Datenschutz'),_xp('Verlauf und private Informationen'),'cinnamon-settings-privacy.desktop'),
 ('software',_xp('Software hinzufügen'),_xp('Anwendungen verwalten'),'mintinstall.desktop'),
 ('software',_xp('Aktualisierungen'),_xp('Installierte Software aktualisieren'),'mintupdate.desktop'),
 ('software',_xp('Standardprogramme'),_xp('Programme für Dateien und Links'),'cinnamon-settings-default.desktop'),
 ('software',_xp('Softwarequellen'),_xp('Paketquellen verwalten'),'mintsources.desktop'),
 ('sound',_xp('Sounds und Audiogeräte'),_xp('Ausgabe, Eingabe und Systemklänge'),'cinnamon-settings-sound.desktop'),
 ('sound',_xp('Benachrichtigungen'),_xp('Hinweise auf dem Desktop'),'cinnamon-settings-notifications.desktop'),
 ('hardware',_xp('Maus und Touchpad'),_xp('Zeiger, Tasten und Scrollen'),'cinnamon-settings-mouse.desktop'),
 ('hardware',_xp('Tastatur'),_xp('Tastenbelegung und Tastenkürzel'),'cinnamon-settings-keyboard.desktop'),
 ('hardware',_xp('Drucker und Faxgeräte'),_xp('Drucker einrichten und verwalten'),'system-config-printer.desktop'),
 ('hardware',_xp('Energieoptionen'),_xp('Bereitschaft und Energieverbrauch'),'cinnamon-settings-power.desktop'),
 ('users',_xp('Eigenes Benutzerkonto'),_xp('Benutzerbild und Kontodetails'),'cinnamon-settings-user.desktop'),
 ('users',_xp('Benutzer und Gruppen'),_xp('Benutzerkonten verwalten'),'cinnamon-settings-users.desktop'),
 ('users',_xp('Anmeldefenster'),_xp('Anmeldung und Begrüßungsbildschirm'),'lightdm-settings.desktop'),
 ('regional',_xp('Datum und Uhrzeit'),_xp('Uhrzeit, Zeitzone und Kalender'),'cinnamon-settings-calendar.desktop'),
 ('regional',_xp('Regions- und Sprachoptionen'),_xp('Systemsprachen verwalten'),'mintlocale.desktop'),
 ('regional',_xp('Eingabemethoden'),_xp('Zusätzliche Texteingabe'),'mintlocale-im.desktop'),
 ('access',_xp('Eingabehilfen'),_xp('Sehen, Hören und Bedienung'),'cinnamon-settings-universal-access.desktop'),
 ('access',_xp('Gesten'),_xp('Touchpad-Gesten anpassen'),'cinnamon-settings-gestures.desktop'),
 ('system','System',_xp('Informationen über diesen Computer'),'mintreport.desktop'),
 ('system',_xp('Treiber'),_xp('Gerätetreiber verwalten'),'mintdrivers.desktop'),
 ('system',_xp('Systemwiederherstellung'),_xp('Timeshift-Schnappschüsse'),'timeshift-gtk.desktop'),
 ('system',_xp('Sicherung'),_xp('Persönliche Daten sichern'),'mintbackup.desktop'),
 ('system',_xp('Autostart'),_xp('Programme beim Anmelden'),'cinnamon-settings-startup.desktop')]
# Cinnamon calls its display desktop entry cinnamon-display-panel.
ENTRIES=[(*e[:3],'cinnamon-display-panel.desktop' if e[3]=='cinnamon-settings-display.desktop' else e[3]) for e in ENTRIES]

def installed_entries():
 result=[]
 for category,title,description,desktop in ENTRIES:
  path=Path('/usr/share/applications')/desktop
  app=Gio.DesktopAppInfo.new_from_filename(str(path)) if path.is_file() else None
  if app:result.append(dict(category=category,title=title,description=description,desktop=desktop,app=app))
 return result

def search_text(text):
 return ''.join(c for c in unicodedata.normalize('NFKD',text.casefold()) if not unicodedata.combining(c))

def label(text,style=None):
 w=Gtk.Label(label=text,xalign=0);w.set_line_wrap(True);w.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
 if style:w.get_style_context().add_class(style)
 return w

class Panel(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title=_xp('Systemsteuerung'))
        self.set_wmclass('xp-control-panel', 'XPControlPanel')
        self.set_icon_name('preferences-desktop')
        self.get_style_context().add_class('xp-control')
        display = Gdk.Display.get_default()
        area = display.get_primary_monitor().get_workarea()
        self.set_default_size(min(1060, area.width - 24), min(800, area.height - 32))
        self.set_position(Gtk.WindowPosition.CENTER)
        self.preferences = Preferences()
        self.entries = installed_entries()
        available = {e['desktop'] for e in self.entries}
        favorites = self.preferences.data.get('favorites', DEFAULT_FAVORITES)
        self.favorites = list(dict.fromkeys(x for x in favorites if isinstance(x,str) and x in available)) if isinstance(favorites,list) else list(DEFAULT_FAVORITES)
        self.saved_geometry = self.preferences.data.get('geometry', {})
        self.normal_geometry = {}
        areas = [display.get_monitor(i).get_workarea() for i in range(display.get_n_monitors())]
        fitted = fit_geometry(self.saved_geometry, [(a.x,a.y,a.width,a.height) for a in areas])
        if fitted:
            self.set_position(Gtk.WindowPosition.NONE)
            self.move(fitted[0], fitted[1])
            self.set_default_size(fitted[2], fitted[3])
        self.category = None
        self.classic = self.preferences.data.get('classic') is True
        self.history = []
        self.future = []
        self._display_query = ''
        self._restoring = False
        self._scroll_timer = 0
        self._render_epoch = 0
        self.connect('configure-event', self.on_configure)
        self.connect('delete-event', self.on_close)
        self.connect('destroy', self.on_destroy)
        self.launcher = self.launch
        self.visible_entries = []
        self.connect('key-press-event', self.key)
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(outer)

        toolbar = Gtk.Box(spacing=8)
        toolbar.get_style_context().add_class('toolbar')
        outer.pack_start(toolbar, False, False, 0)
        self.back = Gtk.Button(label=_xp('Zurück'))
        self.back.set_image(Gtk.Image.new_from_icon_name('go-previous', Gtk.IconSize.LARGE_TOOLBAR))
        self.back.set_always_show_image(True)
        self.back.set_tooltip_text(_xp('Vorherige Ansicht (Alt+Links)'))
        self.back.connect('clicked', lambda *_: self.go_back())
        toolbar.pack_start(self.back, False, False, 0)
        self.forward = Gtk.Button.new_from_icon_name('go-next', Gtk.IconSize.LARGE_TOOLBAR)
        self.forward.set_tooltip_text(_xp('Nächste Ansicht (Alt+Rechts)'))
        self.forward.connect('clicked', lambda *_: self.go_forward())
        toolbar.pack_start(self.forward, False, False, 0)
        home = Gtk.Button.new_from_icon_name('go-home', Gtk.IconSize.LARGE_TOOLBAR)
        home.set_tooltip_text(_xp('Alle Kategorien'))
        home.connect('clicked', lambda *_: self.home())
        toolbar.pack_start(home, False, False, 0)
        toolbar.pack_start(Gtk.Box(), True, True, 0)
        search_label = label(_xp('Suchen:'))
        toolbar.pack_start(search_label, False, False, 0)
        self.search = Gtk.SearchEntry()
        self.search.set_width_chars(22)
        self.search.set_placeholder_text(_xp('Einstellung suchen'))
        self.search.set_tooltip_text(_xp('Alle Einstellungen durchsuchen (Strg+F)'))
        self.search.connect('search-changed', self.search_changed)
        self.search.connect('activate', self.activate_search)
        toolbar.pack_start(self.search, False, False, 0)

        location = Gtk.Box(spacing=8)
        location.get_style_context().add_class('location')
        outer.pack_start(location, False, False, 0)
        location.pack_start(label(_xp('Adresse:')), False, False, 0)
        self.root_link = Gtk.Button(label=_xp('Systemsteuerung'))
        self.root_link.set_image(Gtk.Image.new_from_icon_name('preferences-desktop', Gtk.IconSize.MENU))
        self.root_link.set_always_show_image(True)
        self.root_link.connect('clicked', lambda *_: self.home())
        location.pack_start(self.root_link, False, False, 0)
        self.crumb = label('')
        self.crumb.set_ellipsize(Pango.EllipsizeMode.END)
        self.crumb.set_line_wrap(False)
        location.pack_start(self.crumb, True, True, 0)
        body = Gtk.Box()
        outer.pack_start(body, True, True, 0)
        sidebar_scroll = Gtk.ScrolledWindow()
        sidebar_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sidebar_scroll.set_size_request(214, -1)
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        sidebar.get_style_context().add_class('sidebar')
        sidebar_scroll.add(sidebar)
        body.pack_start(sidebar_scroll, False, False, 0)

        navigation = self.card(sidebar, _xp('Systemsteuerung'))
        self.switch = self.side_link(navigation, '', 'view-grid', self.toggle)
        self.cat_button = self.side_link(navigation, _xp('Alle Kategorien'), 'go-home', self.home)
        self.favorite_box = self.card(sidebar, _xp('Favoriten'))
        self.render_favorites()
        related = self.card(sidebar, _xp('Siehe auch'))
        self.side_link(related, _xp('Systeminformationen'), 'computer', lambda: self.launch_desktop('mintreport.desktop'))
        self.side_link(related, _xp('Cinnamon-Einstellungen'), 'preferences-desktop', self.native)
        details = self.card(sidebar, _xp('Details'))
        self.detail_icon = Gtk.Image.new_from_icon_name('preferences-desktop', Gtk.IconSize.DIALOG)
        self.detail_icon.set_pixel_size(32)
        self.detail_icon.set_halign(Gtk.Align.START)
        details.pack_start(self.detail_icon, False, False, 0)
        self.detail_title = label(_xp('Systemsteuerung'), 'detail-title')
        self.detail_title.set_max_width_chars(23)
        details.pack_start(self.detail_title, False, False, 0)
        self.detail_text = label('', 'detail-text')
        self.detail_text.set_max_width_chars(23)
        details.pack_start(self.detail_text, False, False, 0)

        self.main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.main.get_style_context().add_class('main')
        body.pack_start(self.main, True, True, 0)
        self.heading = label('', 'heading')
        self.main.pack_start(self.heading, False, False, 0)
        self.subtitle = label('', 'subtitle')
        self.main.pack_start(self.subtitle, False, False, 0)
        separator = Gtk.Separator()
        separator.get_style_context().add_class('content-separator')
        self.main.pack_start(separator, False, False, 0)
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.main.pack_start(self.scroll, True, True, 0)
        self.flow = Gtk.FlowBox()
        self.flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flow.set_min_children_per_line(1)
        self.flow.set_max_children_per_line(2)
        self.flow.set_row_spacing(6)
        self.flow.set_column_spacing(10)
        self.flow.set_valign(Gtk.Align.START)
        self.scroll.add(self.flow)
        self.status = label('', 'status')
        outer.pack_start(self.status, False, False, 0)
        self.render()
        self.show_all()
        if self.preferences.data.get('maximized') is True:
            self.maximize()

    def card(self, sidebar, title):
        frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        frame.get_style_context().add_class('side-card')
        frame.pack_start(label(title, 'side-heading'), False, False, 0)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        content.get_style_context().add_class('side-body')
        frame.pack_start(content, False, False, 0)
        sidebar.pack_start(frame, False, False, 0)
        return content

    def side_link(self, parent, title, icon, action):
        button = Gtk.Button(label=title)
        button.get_style_context().add_class('side-link')
        image = Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.MENU)
        image.set_margin_end(6)
        button.set_image(image)
        button.set_always_show_image(True)
        button.get_child().set_halign(Gtk.Align.START)
        button.connect('clicked', lambda *_: action())
        parent.pack_start(button, False, False, 0)
        return button

    def key(self, widget, event):
        if event.keyval == Gdk.KEY_f and event.state & Gdk.ModifierType.CONTROL_MASK:
            self.search.grab_focus()
            return True
        if event.keyval == Gdk.KEY_Left and event.state & Gdk.ModifierType.MOD1_MASK:
            self.go_back()
            return True
        if event.keyval == Gdk.KEY_Right and event.state & Gdk.ModifierType.MOD1_MASK:
            self.go_forward()
            return True
        if event.keyval == Gdk.KEY_Escape:
            if self.search.get_text():
                self.go_back()
                return True
            if self.history:
                self.go_back()
                return True
        return False

    def snapshot(self):
        return dict(category=self.category, classic=self.classic, query=self._display_query,
                    scroll=self.scroll.get_vadjustment().get_value())

    def restore_scroll(self, value):
        if self._scroll_timer:
            GLib.source_remove(self._scroll_timer)
        epoch = self._render_epoch
        def apply():
            self._scroll_timer = 0
            if epoch == self._render_epoch:
                adjustment = self.scroll.get_vadjustment()
                adjustment.set_value(max(0,min(value,adjustment.get_upper()-adjustment.get_page_size())))
            return False
        self._scroll_timer = GLib.timeout_add(70, apply)

    def apply_view(self, view):
        self._restoring = True
        self.category, self.classic = view['category'], view['classic']
        self._display_query = view['query']
        self.search.set_text(view['query'])
        self._restoring = False
        self.render()
        self.restore_scroll(view['scroll'])
        self.save_preferences()

    def search_changed(self, *_):
        query = self.search.get_text()
        if self._restoring or query == self._display_query:
            return
        # One history step per search, not one per typed character.
        if not self._display_query or not query:
            self.history.append(self.snapshot())
            self.history = self.history[-30:]
        self.future.clear()
        self._display_query = query
        self.render()
        self.restore_scroll(0)

    def navigate(self, category=None, classic=False):
        self.search_changed()
        old = self.snapshot()
        if (old['category'],old['classic'],old['query']) != (category,classic,''):
            self.history.append(old)
            self.history = self.history[-30:]
            self.future.clear()
        self.apply_view(dict(category=category,classic=classic,query='',scroll=0))

    def home(self):
        self.navigate()

    def toggle(self, *_):
        self.navigate(classic=not self.classic)

    def choose(self, category):
        self.navigate(category=category)

    def go_back(self):
        self.search_changed()
        if self.history:
            self.future.append(self.snapshot())
            self.apply_view(self.history.pop())

    def go_forward(self):
        self.search_changed()
        if self.future:
            self.history.append(self.snapshot())
            self.apply_view(self.future.pop())

    def save_preferences(self):
        try:
            self.preferences.save(dict(favorites=self.favorites, classic=self.classic))
            return True
        except OSError as error:
            self.status.set_text(_xp('Einstellungen konnten nicht gespeichert werden: ')+str(error))
            return False

    def on_configure(self, *_):
        if not self.is_maximized():
            x,y=self.get_position();w,h=self.get_size()
            self.normal_geometry=dict(x=x,y=y,width=w,height=h)
        return False

    def on_close(self, *_):
        try:
            self.preferences.save(dict(favorites=self.favorites,classic=self.classic,
                geometry=self.normal_geometry or self.saved_geometry,maximized=self.is_maximized()))
        except OSError as error:
            self.status.set_text(_xp('Fensteransicht konnte nicht gespeichert werden: ')+str(error))
        return False

    def on_destroy(self, *_):
        if self._scroll_timer:
            GLib.source_remove(self._scroll_timer)
            self._scroll_timer=0
        if getattr(self,'context_menu',None):self.context_menu.destroy()

    def render_favorites(self):
        for child in self.favorite_box.get_children():child.destroy()
        entries={e['desktop']:e for e in self.entries}
        for desktop in self.favorites:
            if desktop not in entries:continue
            entry=entries[desktop]
            button=self.side_link(self.favorite_box,entry['title'],'starred',lambda e=entry:self.launcher(e))
            # Keep long names inside the sidebar; full text remains available as a tooltip.
            def ellipsize(widget):
                if isinstance(widget,Gtk.Label):
                    widget.set_ellipsize(Pango.EllipsizeMode.END);widget.set_max_width_chars(21)
                if isinstance(widget,Gtk.Container):
                    for child in widget.get_children():ellipsize(child)
            ellipsize(button);button.set_tooltip_text(entry['title']+' – '+entry['description'])
            self.attach_context(button,entry)
        if not self.favorites:
            hint=label(_xp('Einstellungen mit Rechtsklick anheften.'),'detail-text');hint.set_max_width_chars(23)
            self.favorite_box.pack_start(hint,False,False,0)
        self.favorite_box.show_all()

    def toggle_favorite(self, entry):
        previous=self.favorites[:];desktop=entry['desktop']
        if desktop in self.favorites:self.favorites.remove(desktop)
        else:self.favorites.append(desktop)
        if not self.save_preferences():self.favorites=previous;return
        self.render_favorites()
        self.status.set_text(entry['title']+(_xp(' angeheftet.') if desktop in self.favorites else _xp(' aus Favoriten entfernt.')))

    def shortcut(self, entry):
        try:
            target,trusted=create_shortcut(entry)
            self.status.set_text(_xp('Desktop-Verknüpfung erstellt: ')+entry['title']+('' if trusted else _xp(' – ggf. auf dem Desktop „Start erlauben“ wählen.')))
        except FileExistsError:
            self.status.set_text(_xp('Die Desktop-Verknüpfung existiert bereits und wurde nicht überschrieben.'))
        except (OSError,GLib.Error) as error:self.error(str(error))

    def attach_context(self, button, entry):
        button.connect('button-press-event', lambda b,e:self.context(entry,b,e) if e.button==3 else False)
        button.connect('popup-menu',lambda b:self.context(entry,b))

    def context(self, entry, button, event=None):
        button.grab_focus()
        if getattr(self,'context_menu',None):self.context_menu.destroy()
        menu=Gtk.Menu();menu.get_style_context().add_class('xp-control-menu');self.context_menu=menu
        actions=[(_xp('Öffnen'),'document-open',lambda:self.launcher(entry)),
                 (_xp('Aus Favoriten entfernen') if entry['desktop'] in self.favorites else _xp('Zu Favoriten hinzufügen'),'starred',lambda:self.toggle_favorite(entry)),
                 (_xp('Desktop-Verknüpfung erstellen'),'user-desktop',lambda:self.shortcut(entry))]
        for title,icon,action in actions:
            item=Gtk.MenuItem();row=Gtk.Box(spacing=8)
            row.pack_start(Gtk.Image.new_from_icon_name(icon,Gtk.IconSize.MENU),False,False,0)
            row.pack_start(label(title),False,False,0);item.add(row)
            item.connect('activate',lambda _,fn=action:fn());menu.append(item)
        menu.show_all()
        if event:menu.popup_at_pointer(event)
        else:menu.popup_at_widget(button,Gdk.Gravity.SOUTH_WEST,Gdk.Gravity.NORTH_WEST,Gtk.get_current_event())
        return True

    def activate_search(self, *_):
        # Resolve directly from current input, not the delayed search-changed signal.
        self.search_changed()
        self.render()
        if self.search.get_text().strip() and self.visible_entries:
            self.launcher(self.visible_entries[0])

    def show_detail(self, title, description, icon):
        self.detail_title.set_text(title)
        self.detail_text.set_text(description)
        if isinstance(icon, Gio.Icon):
            self.detail_icon.set_from_gicon(icon, Gtk.IconSize.DIALOG)
        else:
            self.detail_icon.set_from_icon_name(icon, Gtk.IconSize.DIALOG)
        self.detail_icon.set_pixel_size(32)

    def tile(self, title, description, icon, callback, classic=False, context=None, entry=None):
        button = Gtk.Button()
        button.get_style_context().add_class('tile')
        if classic:
            button.get_style_context().add_class('classic-tile')
            button.set_size_request(145, 112)
        button.set_tooltip_text(description)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL if classic else Gtk.Orientation.HORIZONTAL, spacing=9)
        button.add(box)
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.DIALOG) if isinstance(icon, Gio.Icon) else Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.DIALOG)
        image.set_pixel_size(40 if classic else 48)
        box.pack_start(image, False, False, 0)
        words = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        box.pack_start(words, True, True, 0)
        title_label = label(title, 'tile-title')
        title_label.set_max_width_chars(17 if classic else 25)
        words.pack_start(title_label, False, False, 0)
        if classic:
            title_label.set_xalign(.5)
            title_label.set_justify(Gtk.Justification.CENTER)
        else:
            desc = label(description, 'tile-description')
            desc.set_max_width_chars(29)
            words.pack_start(desc, False, False, 0)
        if context:
            category_label = label(context, 'result-category')
            category_label.set_max_width_chars(27)
            words.pack_start(category_label, False, False, 0)
        button.connect('clicked', lambda *_: callback())
        button.connect('enter-notify-event', lambda *_: self.show_detail(title, description, icon))
        button.connect('focus-in-event', lambda *_: self.show_detail(title, description, icon))
        if entry:self.attach_context(button,entry)
        self.flow.add(button)

    def render(self):
        self._render_epoch += 1
        for child in self.flow.get_children():
            child.destroy()
        query = self.search.get_text().strip()
        is_home = not (query or self.category or self.classic)
        self.visible_entries = []
        self.switch.set_label('Zur Kategorienansicht' if self.classic else _xp('Zur klassischen Ansicht'))
        self.back.set_sensitive(bool(self.history))
        self.forward.set_sensitive(bool(self.future))
        self.cat_button.set_sensitive(not is_home)
        classic = self.classic and not query
        self.flow.set_max_children_per_line(5 if classic else 2)
        self.flow.set_homogeneous(classic)
        if classic:
            self.main.get_style_context().add_class('classic-view')
        else:
            self.main.get_style_context().remove_class('classic-view')
        if is_home:
            title = _xp('Wählen Sie eine Kategorie')
            subtitle = _xp('Passen Sie Darstellung und Funktionen Ihres Computers an.')
            categories = [c for c in CATEGORIES if any(e['category'] == c[0] for e in self.entries)]
            for key, name, desc, icon in categories:
                self.tile(name, desc, icon, lambda k=key: self.choose(k))
            count = len(categories)
            self.show_detail(_xp('Systemsteuerung'), _xp('Zeigen Sie auf eine Kategorie oder Einstellung, um mehr darüber zu erfahren.'), 'preferences-desktop')
        else:
            def matches(entry):
                category_name = next(c[1] for c in CATEGORIES if c[0] == entry['category'])
                text = search_text(entry['title'] + ' ' + entry['description'] + ' ' + category_name + ' ' + ALIASES.get(entry['desktop'],''))
                return all(word in text for word in search_text(query).split())
            entries = [e for e in self.entries if matches(e)] if query else [e for e in self.entries if not self.category or e['category'] == self.category]
            entries.sort(key=lambda e: e['title'].casefold())
            self.visible_entries = entries
            title = 'Suchergebnisse' if query else next((c[1] for c in CATEGORIES if c[0] == self.category), _xp('Klassische Ansicht'))
            subtitle = _xp('Ergebnisse für „{0}“').format(query) if query else _xp('Wählen Sie die gewünschte Einstellung.')
            if not entries:
                subtitle = _xp('Keine passende Einstellung gefunden. Versuchen Sie einen anderen Suchbegriff.')
            for entry in entries:
                category_name = next(c[1] for c in CATEGORIES if c[0] == entry['category'])
                self.tile(entry['title'], entry['description'], Gio.ThemedIcon.new(ENTRY_ICONS.get(entry['desktop'], next((c[3] for c in CATEGORIES if c[0] == entry['category']), 'preferences-system'))), lambda e=entry: self.launcher(e), classic, category_name if query else None, entry=entry)
            count = len(entries)
            self.show_detail(title, _xp('Mit einem Klick öffnen Sie die gewünschte Einstellung. Alt+Links führt zur vorherigen Ansicht.'), next((c[3] for c in CATEGORIES if c[0] == self.category), 'preferences-desktop'))
        self.heading.set_text(title)
        self.subtitle.set_text(subtitle)
        self.crumb.set_text('› ' + title if not is_home else '')
        self.status.set_text(f'{count} ' + ((_xp('Kategorie') if count == 1 else _xp('Kategorien')) if is_home else (_xp('Einstellung') if count == 1 else _xp('Einstellungen'))) + (_xp('  ·  Eingabetaste öffnet den ersten Treffer') if query and count else '  ·  Linux Mint'))
        self.flow.show_all()

    def launch(self, entry):
        try:
            entry['app'].launch([], Gdk.Display.get_default().get_app_launch_context())
            self.status.set_text(entry['title'] + _xp(' wird geöffnet …'))
        except GLib.Error as error:
            self.error(str(error))

    def launch_desktop(self, desktop):
        entry = next((e for e in self.entries if e['desktop'] == desktop), None)
        if entry:
            self.launcher(entry)

    def native(self):
        try:
            Gio.Subprocess.new(['/usr/bin/cinnamon-settings'], Gio.SubprocessFlags.NONE)
        except GLib.Error as error:
            self.error(str(error))

    def error(self, text):
        dialog = Gtk.MessageDialog(transient_for=self, modal=True, message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.CLOSE, text=_xp('Die Einstellung konnte nicht geöffnet werden.'))
        dialog.format_secondary_text(text)
        dialog.run()
        dialog.destroy()

class Application(Gtk.Application):
 def __init__(self):super().__init__(application_id='org.mintxp.ControlPanel')
 def do_startup(self):
  Gtk.Application.do_startup(self);css=Gtk.CssProvider();css.load_from_path(str(BASE/'style.css'));Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),css,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
 def do_activate(self):
  w=self.get_active_window() or Panel(self);w.present()
if __name__=='__main__':sys.exit(Application().run(sys.argv))

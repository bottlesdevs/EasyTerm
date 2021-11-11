#!/usr/bin/env python
import os
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Handy', '1')
gi.require_version('Vte', '2.91')
from gi.repository import Gtk, Gdk, GLib, Vte, Handy, Pango

CONF_NAME = "EasyTerm"
CONF_DEF_CWD = os.getcwd()
CONF_DEF_CMD = ["/bin/bash"]
CONF_FONT = "Source Code Pro Regular 12"
CONF_FG = Gdk.RGBA(0.8, 0.8, 0.8, 1.0)
CONF_BG = Gdk.RGBA(0.1, 0.1, 0.1, 1.0)

class Terminal(Vte.Terminal):
    def __init__(self, *args, **kwds):
        super(Terminal, self).__init__(*args, **kwds)  
        self.set_cursor_blink_mode(Vte.CursorBlinkMode.ON)
        self.set_mouse_autohide(True)
        self.set_font(Pango.FontDescription(CONF_FONT))
        self.set_colors(
            foreground=CONF_FG,
            background=CONF_BG,
        )


class HeaderBar(Handy.HeaderBar):
    actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

    def __init__(self, *args, **kwds):
        super(HeaderBar, self).__init__(*args, **kwds)
        self.set_show_close_button(True)
        self.set_title(CONF_NAME)
        self.pack_start(self.actions_box)
    
    def build_actions(self, actions:dict):
        for action in actions:
            button = Gtk.Button()
            button.set_tooltip_text(action["tooltip"])
            button.set_image(Gtk.Image.new_from_icon_name(action["icon"], Gtk.IconSize.BUTTON))
            button.connect("clicked", action["callback"])
            self.actions_box.pack_start(button, False, False, 0)


class MainWindow(Handy.ApplicationWindow):
    Handy.init()
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    headerbar = HeaderBar()
    terminal = Terminal()

    def __init__(self, cwd:str="", command:list=[], env:list=[], actions:list=[], *args, **kwds):
        super().__init__()
        self.set_title(CONF_NAME)
        self.set_default_size(800, 450)
        self.set_dark_theme()

        self.add(self.box)
        self.box.pack_start(self.headerbar, False, False, 0)
        self.box.pack_start(self.terminal, True, True, 0)
        
        if actions:
            self.headerbar.build_actions(actions)
        
        if cwd == "":
            cwd = CONF_DEF_CWD
        if command == []:
            command = CONF_DEF_CMD

        self.terminal.spawn_sync(
            Vte.PtyFlags.DEFAULT,
            cwd,
            command,
            env,
            GLib.SpawnFlags.DO_NOT_REAP_CHILD,
            None,
            None,
            None
        )
        
        self.terminal.connect("key-press-event", self.update_title)
        self.terminal.connect("window-title-changed", self.update_title)
        self.terminal.connect("child-exited", self.update_title)
    
    def update_title(self, terminal, *args):
        self.headerbar.set_title(terminal.get_window_title())

    def set_dark_theme(self):
        settings = Gtk.Settings.get_default()
        settings.set_property("gtk-application-prefer-dark-theme", True)
        

class EasyTerm(Gtk.Application):
    def __init__(self, cwd:str="", command:list=[], env:list=[], actions:list=[], *args, **kwds):
        super().__init__(*args, **kwds)
        self.cwd = cwd
        self.command = command
        self.env = env
        self.actions = actions
            
    def do_activate(self):
        win = MainWindow(
            cwd=self.cwd,
            command=self.command,
            env=self.env,
            actions=self.actions
        )
        win.connect('delete-event', Gtk.main_quit)
        win.show_all()
        Gtk.main()
    
    def do_startup(self):
        Gtk.Application.do_startup(self)


if __name__ == "__main__":
    app = EasyTerm()
    app.run(None)
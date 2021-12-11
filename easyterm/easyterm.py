#!/usr/bin/env python
import os
import gi
import sys
import shlex
gi.require_version('Gtk', '3.0')
gi.require_version('Handy', '1')
gi.require_version('Vte', '2.91')
from gi.repository import Gtk, Gdk, Gio, GLib, Vte, Handy, Pango

CONF_NAME = "EasyTerm"
CONF_DEF_CWD = os.getcwd()
CONF_DEF_CMD = ["/bin/bash"]
CONF_FONT = "Source Code Pro Regular 12"
CONF_FG = Gdk.RGBA(0.8, 0.8, 0.8, 1.0)
CONF_BG = Gdk.RGBA(0.1, 0.1, 0.1, 1.0)

class Terminal(Vte.Terminal):
    def __init__(self, palette=None, *args, **kwds):
        super(Terminal, self).__init__(*args, **kwds)  
        self.set_cursor_blink_mode(Vte.CursorBlinkMode.ON)
        self.set_mouse_autohide(True)
        self.set_font(Pango.FontDescription(CONF_FONT))
        if palette is None or len(palette) < 2:
            self.set_colors(
                foreground=CONF_FG,
                background=CONF_BG,
            )
        else:
            self.set_colors(
                foreground=palette[0],
                background=palette[1],
            )
    
    def run_command(self, cmd):
        _cmd = str.encode(f"{cmd}\n")
        self.feed_child(_cmd)
    
    def run_command_btn(self, btn, cmd):
        self.run_command(cmd)


class HeaderBar(Handy.HeaderBar):
    actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

    def __init__(self, terminal, *args, **kwds):
        super(HeaderBar, self).__init__(*args, **kwds)
        self.set_show_close_button(True)
        self.set_title(CONF_NAME)
        self.pack_start(self.actions_box)
        self.terminal = terminal
    
    def build_actions(self, actions:dict):
        for action in actions:
            button = Gtk.Button()
            button.set_tooltip_text(action["tooltip"])
            button.set_image(
                Gtk.Image.new_from_icon_name(action["icon"], 
                Gtk.IconSize.BUTTON)
            )
            button.connect("clicked", self.terminal.run_command_btn, action["command"])
            self.actions_box.pack_start(button, False, False, 0)


class MainWindow(Handy.ApplicationWindow):
    Handy.init()
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

    def __init__(
        self, 
        cwd:str="", 
        command:list=[], 
        env:list=[], 
        actions:list=[], 
        dark_theme:bool=False,
        palette:list=[],
        *args, **kwds
    ):
        super().__init__()
        self.set_title(CONF_NAME)
        self.set_default_size(800, 450)

        self.terminal = Terminal(palette)
        self.headerbar = HeaderBar(self.terminal)

        if dark_theme:
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
        

class EasyTermLib:
    def __init__(
        self, 
        cwd:str="", 
        command:list=[], 
        env:list=[], 
        actions:list=[], 
        dark_theme:bool=False, 
        palette:list=[],
        *args, **kwds
    ):
        self.window = MainWindow(cwd, command, env, actions, dark_theme, palette)
        self.window.show_all()
        self.window.connect("delete-event", Gtk.main_quit)
        Gtk.main()
        sys.exit()

class EasyTerm(Gtk.Application):
    def __init__(
        self, 
        cwd:str="", 
        command:list=[],
        env:list=[],
        actions:list=[], 
        *args, **kwds
    ):
        super().__init__(
            application_id='com.usebottles.easyterm',
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE | Gio.ApplicationFlags.NON_UNIQUE,
            *args, **kwds
        )
        self.cwd = cwd
        self.command = command
        self.env = env
        self.actions = actions

        self.__register_arguments()
    
    def __register_arguments(self):
        self.add_main_option(
            "cwd",
            ord("w"),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.STRING,
            "Set the initial working directory",
            None
        )
        self.add_main_option(
            "command",
            ord("c"),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.STRING,
            "Set the command to execute",
            None
        )
        self.add_main_option(
            "env",
            ord("e"),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.STRING,
            "Set the environment variables",
            None
        )
        self.add_main_option(
            "actions",
            ord("a"),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.STRING,
            "Set the actions",
            None
        )
        self.add_main_option(
            "dark-theme",
            ord("d"),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            "Set the dark theme",
            None
        )
        self.add_main_option(
            "palette",
            ord("p"),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.STRING,
            "Set the palette (RGBA_back, RGBA_fore)",
            None
        )

    
    def do_command_line(self, command_line):
        cwd = ""
        command = []
        env = []
        actions = []
        dark_theme = False
        palette = []

        options = command_line.get_options_dict()
        
        if options.contains("cwd"):
            cwd = options.lookup_value("cwd").get_string()
        if options.contains("command"):
            command = shlex.split(options.lookup_value("command").get_string())
        if options.contains("env"):
            env = options.lookup_value("env").get_string().split(" ")
        if options.contains("actions"):
            actions = options.lookup_value("actions").get_string().split(" ")
        if options.lookup_value("dark-theme").get_boolean():
            dark_theme = True
        if options.contains("palette"):
            palette = options.lookup_value("palette").get_string().split(" ")
            if len(palette) < 2:
                palette = []
            else:
                back = Gdk.RGBA()
                back.parse(palette[0])
                fore = Gdk.RGBA()
                fore.parse(palette[1])
                palette = [back, fore]

        EasyTermLib(cwd, command, env, actions, dark_theme, palette)
        return 0
            
    def do_activate(self):
        win = MainWindow(
            cwd=self.cwd,
            command=self.command,
            env=self.env,
            actions=self.actions
        )
        win.connect('delete-event', Gtk.main_quit)
        win.present()
    
    def do_startup(self):
        Gtk.Application.do_startup(self)


if __name__ == "__main__":
    app = EasyTerm()
    app.run(sys.argv)

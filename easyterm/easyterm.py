#!/usr/bin/env python
import os
import gi
import sys
import shlex
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Vte', '3.91')
from gi.repository import Gtk, Gdk, Gio, GLib, Vte, Adw, Pango

Adw.init()

CONF_NAME = "EasyTerm"
CONF_DEF_CWD = os.getcwd()
CONF_DEF_CMD = ["/bin/bash"]
CONF_FONT = "Source Code Pro Regular 12"
CONF_FG = Gdk.RGBA(); CONF_FG.red = 0.8; CONF_FG.green = 0.8; CONF_FG.blue = 0.8; CONF_FG.alpha = 1.0
CONF_BG = Gdk.RGBA(); CONF_BG.red = 0.1; CONF_BG.green = 0.1; CONF_BG.blue = 0.1; CONF_BG.alpha = 1.0

class Terminal(Vte.Terminal):
    evc = Gtk.GestureClick(button=Gdk.BUTTON_SECONDARY)

    def __init__(self, palette=None, *args, **kwds):
        super(Terminal, self).__init__(*args, **kwds)  
        self.set_cursor_blink_mode(Vte.CursorBlinkMode.ON)
        self.set_mouse_autohide(True)
        self.set_font(Pango.FontDescription(CONF_FONT))
        self.add_controller(self.evc)
        
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
        
        # menu
        # copy_item = Gtk.MenuItem("Copy")
        # paste_item = Gtk.MenuItem("Paste")

        # signals
        self.evc.connect("pressed", self.show_menu_cb)
        # copy_item.connect("activate", self.copy_cb)
        # paste_item.connect("activate", self.paste_cb)

    def show_menu_cb(self, ctl, n_press, x, y):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        bc = Gtk.Button()
        bp = Gtk.Button()
        self.popover = Gtk.Popover()
        rectangle = Gdk.Rectangle()

        box.set_margin_top(6)
        box.set_margin_start(6)
        box.set_margin_bottom(6)
        box.set_margin_end(6)
        box.set_spacing(3)

        rectangle.x = int(x)
        rectangle.y = int(y)

        bc.set_label("Copy")
        bp.set_label("Paste")
        bc.add_css_class("flat")
        bp.add_css_class("flat")

        bc.connect("clicked", self.copy_cb)
        bp.connect("clicked", self.paste_cb)

        box.append(bc)
        box.append(bp)

        self.popover.add_css_class("menu")
        self.popover.set_child(box)
        self.popover.set_parent(self)
        self.popover.set_pointing_to(rectangle)
        self.popover.popup()

    def copy_cb(self, widget):
        if self.get_has_selection():
            clipboard = Gdk.Display.get_clipboard(Gdk.Display.get_default())
            clipboard.set_content(Gdk.ContentProvider.new_for_value(self.get_text_selected()))
        self.popover.popdown()

    def paste_cb(self, widget):
        clipboard = Gdk.Display.get_clipboard(Gdk.Display.get_default())
        self.paste_text(clipboard.get_content().get_value())
        self.popover.popdown()
    
    def run_command(self, cmd):
        _cmd = str.encode(f"{cmd}\n")
        self.feed_child(_cmd)
    
    def run_command_btn(self, btn, cmd):
        self.run_command(cmd)


class HeaderBar(Adw.Bin):
    actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    label_title = Gtk.Label.new(CONF_NAME)

    def __init__(self, terminal, *args, **kwds):
        super(Adw.Bin, self).__init__(*args, **kwds)
        self.terminal = terminal
        headerbar = Adw.HeaderBar()
        headerbar.set_title_widget(self.label_title)
        headerbar.pack_start(self.actions_box)
        self.set_child(headerbar)
    
    def set_title(self, title):
        self.label_title.set_text(title)
    
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

class MainWindow(Adw.ApplicationWindow):
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    
    def __init__(
        self, 
        cwd:str="", 
        command:list=[], 
        env:list=[], 
        actions:list=[], 
        dark_theme:bool=True,
        palette:list=[],
        **kwargs
    ):
        super().__init__(**kwargs)
        self.set_title(CONF_NAME)
        self.set_default_size(800, 450)

        self.terminal = Terminal(palette)
        self.headerbar = HeaderBar(self.terminal)

        if dark_theme:
            self.set_dark_theme()

        self.set_content(self.box)
        self.box.append(self.headerbar)
        self.box.append(self.terminal)

        if actions:
            self.headerbar.build_actions(actions)
        
        if cwd == "":
            cwd = CONF_DEF_CWD
        if command == []:
            command = CONF_DEF_CMD
        if palette:
            self.set_palette(palette)

        self.terminal.spawn_async(
            Vte.PtyFlags.DEFAULT,
            cwd,
            command,
            env,
            GLib.SpawnFlags.DO_NOT_REAP_CHILD,
            None,
            None,
            -1,
            None,
            None
        )
        
        self.terminal.connect("window-title-changed", self.update_title)
        self.terminal.connect("child-exited", self.update_title)

    def set_palette(self, palette):
        _, b = palette
        style = "window{background-color: %s}" % b.to_string()
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(str.encode(style))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
    def update_title(self, terminal, *args):
        self.headerbar.set_title(terminal.get_window_title())

    def set_dark_theme(self):
        style_manager = Adw.StyleManager.get_default()
        style_manager.props.color_scheme = Adw.ColorScheme.FORCE_DARK
        
class EasyTermLib:
    def __init__(
        self, 
        cwd:str="", 
        command:list=[], 
        env:list=[], 
        actions:list=[], 
        dark_theme:bool=True, 
        palette:list=[],
        *args, **kwds
    ):
        self.window = MainWindow(cwd, command, env, actions, dark_theme, palette)
        self.window.present()

class EasyTerm(Gtk.Application):
    def __init__(
        self, 
        cwd:str="", 
        command:list=[],
        env:list=[],
        actions:list=[]
    ):
        super().__init__(
            application_id='com.usebottles.easyterm',
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE | Gio.ApplicationFlags.NON_UNIQUE,
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
            "light-theme",
            ord("d"),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            "Set the light theme",
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
            
    def do_activate(
        self, 
        cwd:str="", 
        command:list=[], 
        env:list=[], 
        actions:list=[], 
        dark_theme:bool=True, 
        palette:list=[],
        **kwargs
    ):
        win = self.props.active_window
        if not win:
            win = MainWindow(
                application=self,
                cwd=cwd,
                command=command,
                env=env,
                actions=actions,
                dark_theme=dark_theme,
                palette=palette
            )
        win.present()
    
    def do_command_line(self, command_line):
        cwd = ""
        command = []
        env = []
        actions = []
        dark_theme = True
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

        if options.lookup_value("light-theme"):
            dark_theme = False

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
                
        self.do_activate(cwd, command, env, actions, dark_theme, palette)
        return 0
    
    def do_startup(self):
        Gtk.Application.do_startup(self)


class TemplateApp(Gtk.Application):

    def __init__(self):
        super().__init__(
            application_id='org.example.myapp',
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = MainWindow(application=self)
        win.present()    

if __name__ == "__main__":
    app = EasyTerm()
    app.run(sys.argv)

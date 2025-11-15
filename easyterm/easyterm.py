#!/usr/bin/env python
import os
import shlex
import sys
from typing import Any, Dict, List, Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Vte", "3.91")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk, Pango, Vte

CONF_NAME: str = "EasyTerm"
CONF_DEF_CWD: str = os.getcwd()
CONF_DEF_CMD: List[str] = ["/bin/bash"]

CONF_FG: Gdk.RGBA = Gdk.RGBA()
CONF_FG.red = 0.8
CONF_FG.green = 0.8
CONF_FG.blue = 0.8
CONF_FG.alpha = 1.0

CONF_BG: Gdk.RGBA = Gdk.RGBA()
CONF_BG.red = 0.1
CONF_BG.green = 0.1
CONF_BG.blue = 0.1
CONF_BG.alpha = 1.0

CONF_FONT_FAMILY: str = "DejaVu Sans Mono"
CONF_FONT_FALLBACKS: List[str] = [
    "Liberation Mono",
    "Cascadia Mono",
    "Fira Code",
    "Monospace",
]
CONF_FONT_SIZE: int = 12


def select_font_family(available_families: List[str]) -> str:
    """Select the best matching font family available on the system."""
    for candidate in [CONF_FONT_FAMILY, *CONF_FONT_FALLBACKS]:
        if candidate in available_families:
            return candidate
    return available_families[0] if available_families else CONF_FONT_FAMILY


class Terminal(Vte.Terminal):
    """Vte-based terminal widget."""

    def __init__(
        self,
        palette: Optional[List[Gdk.RGBA]] = None,
        *args: Any,
        **kwds: Any,
    ) -> None:
        super().__init__(*args, **kwds)
        self.set_cursor_blink_mode(Vte.CursorBlinkMode.ON)
        self.set_mouse_autohide(True)
        self.set_font(self._build_font_description())

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

        self._build_context_menu()

    def _build_font_description(self) -> Pango.FontDescription:
        """Build a Pango font description based on available families and config."""
        context = self.create_pango_context()
        families = [family.get_name() for family in context.list_families()]
        family = select_font_family(families)
        return Pango.FontDescription(f"{family} {CONF_FONT_SIZE}")

    def _build_context_menu(self) -> None:
        """Create the right-click context menu for copy and paste."""
        self.popover_menu: Gtk.Popover = Gtk.Popover()
        self.popover_menu.set_has_arrow(False)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        box.set_margin_start(6)
        box.set_margin_end(6)

        copy_btn = Gtk.Button.new_with_label("Copy")
        copy_btn.connect("clicked", self.copy_cb)
        box.append(copy_btn)

        paste_btn = Gtk.Button.new_with_label("Paste")
        paste_btn.connect("clicked", self.paste_cb)
        box.append(paste_btn)

        self.popover_menu.set_child(box)
        self.popover_menu.set_parent(self)

        gesture = Gtk.GestureClick.new()
        gesture.set_button(Gdk.BUTTON_SECONDARY)
        gesture.connect("pressed", self.show_menu_cb)
        self.add_controller(gesture)

    def show_menu_cb(
        self,
        gesture: Gtk.GestureClick,
        n_press: int,
        x: float,
        y: float,
    ) -> None:
        """Show the context menu at the pointer position."""
        rect = Gdk.Rectangle()
        rect.x = int(x)
        rect.y = int(y)
        rect.width = 1
        rect.height = 1
        self.popover_menu.set_pointing_to(rect)
        self.popover_menu.popup()

    def copy_cb(self, widget: Gtk.Widget) -> None:
        """Copy selected text to the clipboard."""
        self.copy_clipboard_format(Vte.Format.TEXT)

    def paste_cb(self, widget: Gtk.Widget) -> None:
        """Paste text from the clipboard."""
        self.paste_clipboard()

    def run_command(self, cmd: str) -> None:
        """Feed a command line followed by a newline into the child PTY."""
        _cmd = f"{cmd}\n".encode()
        self.feed_child(_cmd)

    def run_command_btn(self, btn: Gtk.Button, cmd: str) -> None:
        """Callback to run a command when a headerbar button is clicked."""
        self.run_command(cmd)


class HeaderBar:
    """Wrapper around Adw.HeaderBar to handle title and command actions."""

    def __init__(
        self,
        terminal: Terminal,
        *args: Any,
        **kwds: Any,
    ) -> None:
        self.terminal: Terminal = terminal
        self.widget: Adw.HeaderBar = Adw.HeaderBar(**kwds)

        self.actions_box: Gtk.Box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=6,
        )
        self.widget.pack_start(self.actions_box)

        self.title_label: Gtk.Label = Gtk.Label(label=CONF_NAME)
        self.widget.set_title_widget(self.title_label)

    def build_actions(self, actions: List[Dict[str, str]]) -> None:
        """Create headerbar buttons based on a list of action descriptors."""
        for action in actions:
            button = Gtk.Button()
            button.set_tooltip_text(action["tooltip"])
            icon = Gtk.Image.new_from_icon_name(action["icon"])
            button.set_child(icon)
            button.connect("clicked", self.terminal.run_command_btn, action["command"])
            self.actions_box.append(button)

    def set_title(self, title: str) -> None:
        """Update the headerbar title label."""
        self.title_label.set_label(title)

    def set_show_end_title_buttons(self, value: bool) -> None:
        """Show or hide the end title buttons."""
        self.widget.set_show_end_title_buttons(value)

    def set_show_start_title_buttons(self, value: bool) -> None:
        """Show or hide the start title buttons."""
        self.widget.set_show_start_title_buttons(value)


class MainWindow(Adw.ApplicationWindow):
    """Main application window embedding the terminal and headerbar."""

    Adw.init()

    def __init__(
        self,
        application: Adw.Application,
        cwd: str = "",
        command: Optional[List[str]] = None,
        env: Optional[List[str]] = None,
        actions: Optional[List[Dict[str, str]]] = None,
        dark_theme: bool = True,
        palette: Optional[List[Gdk.RGBA]] = None,
        *args: Any,
        **kwds: Any,
    ) -> None:
        super().__init__(application=application, *args, **kwds)
        self.set_title(CONF_NAME)
        self.set_default_size(800, 450)

        self.terminal: Terminal = Terminal(palette)
        self.headerbar: HeaderBar = HeaderBar(self.terminal)
        self.headerbar.set_show_end_title_buttons(True)
        self.headerbar.set_show_start_title_buttons(True)

        self.box: Gtk.Box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.box.append(self.terminal)

        self.toolbar_view: Adw.ToolbarView = Adw.ToolbarView()
        self.toolbar_view.add_top_bar(self.headerbar.widget)
        self.toolbar_view.set_content(self.box)

        self.set_content(self.toolbar_view)

        if dark_theme:
            self.set_dark_theme()

        if actions is None:
            actions = []
        if actions:
            self.headerbar.build_actions(actions)

        if cwd == "":
            cwd = CONF_DEF_CWD
        if not command:
            command = CONF_DEF_CMD
        if env is None:
            env = []
        if palette is None:
            palette = []

        self.terminal.spawn_async(
            Vte.PtyFlags.DEFAULT,
            cwd,
            command,
            env,
            GLib.SpawnFlags.DEFAULT,
            None,
            None,
            -1,
            None,
            None,
        )

        self.terminal.connect("window-title-changed", self.update_title)
        self.terminal.connect("child-exited", self.update_title)

    def update_title(self, terminal: Terminal, *args: Any) -> None:
        """Update the window title based on the child process window title."""
        title = terminal.get_window_title() or CONF_NAME
        self.headerbar.set_title(title)

    def set_dark_theme(self) -> None:
        """Force the application into dark color scheme."""
        style_manager = Adw.StyleManager.get_default()
        style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)


class EasyTermLib:
    """Library-style wrapper to embed EasyTerm as a reusable component."""

    def __init__(
        self,
        cwd: str = "",
        command: Optional[List[str]] = None,
        env: Optional[List[str]] = None,
        actions: Optional[List[Dict[str, str]]] = None,
        dark_theme: bool = True,
        palette: Optional[List[Gdk.RGBA]] = None,
        *args: Any,
        **kwds: Any,
    ) -> None:
        self.cwd: str = cwd
        self.command: List[str] = command or []
        self.env: List[str] = env or []
        self.actions: List[Dict[str, str]] = actions or []
        self.dark_theme: bool = dark_theme
        self.palette: List[Gdk.RGBA] = palette or []

        self.application: Adw.Application = Adw.Application(
            application_id="com.usebottles.easytermlib",
            flags=Gio.ApplicationFlags.NON_UNIQUE,
        )
        self.application.connect("activate", self._on_activate)
        exit_status = self.application.run(sys.argv[:1])
        sys.exit(exit_status)

    def _on_activate(self, application: Adw.Application) -> None:
        """Create and present the main window when the application activates."""
        window = MainWindow(
            application=application,
            cwd=self.cwd,
            command=self.command,
            env=self.env,
            actions=self.actions,
            dark_theme=self.dark_theme,
            palette=self.palette,
        )
        window.connect("close-request", self._on_close_request)
        window.present()
        self.window: MainWindow = window

    def _on_close_request(self, window: MainWindow, *args: Any) -> bool:
        """Quit the application when the window is closed."""
        self.application.quit()
        return False


class EasyTerm(Adw.Application):
    """CLI-capable EasyTerm application with command-line options support."""

    def __init__(
        self,
        cwd: str = "",
        command: Optional[List[str]] = None,
        env: Optional[List[str]] = None,
        actions: Optional[List[Dict[str, str]]] = None,
        *args: Any,
        **kwds: Any,
    ) -> None:
        super().__init__(
            application_id="com.usebottles.easyterm",
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE
            | Gio.ApplicationFlags.NON_UNIQUE,
            *args,
            **kwds,
        )
        self.cwd: str = cwd
        self.command: List[str] = command or []
        self.env: List[str] = env or []
        self.actions: List[Dict[str, str]] = actions or []
        self.dark_theme: bool = True
        self.palette: List[Gdk.RGBA] = []

        self.__register_arguments()

    def __register_arguments(self) -> None:
        """Register supported command-line options for the application."""
        self.add_main_option(
            "cwd",
            ord("w"),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.STRING,
            "Set the initial working directory",
            None,
        )
        self.add_main_option(
            "command",
            ord("c"),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.STRING,
            "Set the command to execute",
            None,
        )
        self.add_main_option(
            "env",
            ord("e"),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.STRING,
            "Set the environment variables",
            None,
        )
        self.add_main_option(
            "actions",
            ord("a"),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.STRING,
            "Set the actions",
            None,
        )
        self.add_main_option(
            "light-theme",
            ord("d"),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            "Set the light theme",
            None,
        )
        self.add_main_option(
            "palette",
            ord("p"),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.STRING,
            "Set the palette (RGBA_back, RGBA_fore)",
            None,
        )

    def do_command_line(self, command_line: Gio.ApplicationCommandLine) -> int:
        """Parse command-line options and activate the application."""
        cwd: str = ""
        command: List[str] = []
        env: List[str] = []
        actions: List[Dict[str, str]] = []
        dark_theme: bool = True
        palette: List[Gdk.RGBA] = []

        options = command_line.get_options_dict()

        if options.contains("cwd"):
            cwd = options.lookup_value("cwd").get_string()

        if options.contains("command"):
            command_str = options.lookup_value("command").get_string()
            command = shlex.split(command_str)

        if options.contains("env"):
            env_str = options.lookup_value("env").get_string()
            env = env_str.split(" ") if env_str else []

        if options.contains("actions"):
            raw = options.lookup_value("actions").get_string()
            for spec in raw.split(","):
                spec = spec.strip()
                if not spec:
                    continue
                parts = spec.split(":")
                if len(parts) == 3:
                    tooltip, icon, cmd = parts
                elif len(parts) == 2:
                    tooltip, cmd = parts
                    icon = "system-run-symbolic"
                else:
                    continue
                actions.append(
                    {
                        "tooltip": tooltip,
                        "icon": icon,
                        "command": cmd,
                    }
                )

        if options.lookup_value("light-theme"):
            dark_theme = False

        if options.contains("palette"):
            palette_tokens = options.lookup_value("palette").get_string().split(" ")
            if len(palette_tokens) >= 2:
                back = Gdk.RGBA()
                back.parse(palette_tokens[0])
                fore = Gdk.RGBA()
                fore.parse(palette_tokens[1])
                palette = [back, fore]

        self.cwd = cwd
        self.command = command
        self.env = env
        self.actions = actions
        self.dark_theme = dark_theme
        self.palette = palette
        self.activate()
        return 0

    def do_activate(self) -> None:
        """Create and present the main window if not already active."""
        win = self.props.active_window
        if not win:
            win = MainWindow(
                application=self,
                cwd=self.cwd,
                command=self.command,
                env=self.env,
                actions=self.actions,
                dark_theme=self.dark_theme,
                palette=self.palette,
            )
        win.present()

    def do_startup(self) -> None:
        """Run application startup sequence."""
        Adw.Application.do_startup(self)


if __name__ == "__main__":
    app = EasyTerm()
    app.run(sys.argv)

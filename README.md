# EasyTerm
An easy-to-bundle GTK terminal emulator.

This project is meant to be used as a dependency for other projects that
need an easy-to-bundle and lightweight terminal emulator, but also
works as a standalone terminal emulator.

## Dependencies
- GTK 3
- Handy
- Vte

## GTK4 & libadwaita
Port to GTK4 is almost simple, but is stalled because of the lack of
Vte for GTK4. This mean that also libhandy cannot be moved to libadwaita
because this last one need GTK4.

## Bottles purposes
EasyTerm should be provided as the default terminal in the Bottles project
when Vte will be ported to GTK4.

## Installation
```bash
git clone https://github.com/bottlesdevs/EasyTerm.git
cd EasyTerm
python3 setup.py install
```

## Usage
As a **library**, you can use the `EasyTerm` class as follows:
```python
from easyterm import easyterm
easyterm.EasyTerm(
    cwd='/path',
    command='/bin/bash',
    env=[],
    actions=[
        {
            "name": "Hello",
            "icon": "emblem-favorite",
            "tooltip": "Say hello to the world",
            "command": "echo Hello World"
        }
    ]
)
```

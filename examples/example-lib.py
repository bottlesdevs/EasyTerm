from easyterm import easyterm

easyterm.EasyTermLib(
    cwd='/',
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
# System Design Articles

Each article starts from a design I drew myself, then works through where it breaks and what the real design looks like. The articles are organized around the places I actually got stuck.

## Articles

| System | Core hard problem | Article |
|---|---|---|
| WhatsApp | Message delivery guarantees, routing to the socket-holding server, ordering | [designs/whatsapp](designs/whatsapp/README.md) |

## Layout

Each system gets its own folder under `designs/`, with the article and my original diagram side by side:

```
designs/
└── whatsapp/
    ├── README.md            the article
    └── starting-design.png  my first attempt, exported from Excalidraw
```

## Patterns

[patterns.md](patterns.md) collects the ideas that show up in more than one system, with links to where each one is explained.

## Checking links

```
python3 scripts/check_links.py
```

Run this before committing. It checks every relative link and `#anchor` across all the markdown files.

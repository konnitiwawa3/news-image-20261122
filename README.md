# The World Dispatch · 22 November 2026

An illustrated front page for Sunday, 22 November 2026. The edition contains 35 reports, a numbered location map and a separate Friday market reference.

Run with Python 3.13:

```sh
python3 main.py
```

The renderer writes `/output/entry.png`. For a local preview, set `MAKEFUN_OUTPUT_DIR` to a writable directory. It uses the Python standard library, fixed type masks, original line illustrations and a seeded paper texture. It uses no network services or operating-system fonts. `edition.json` contains the newspaper copy.

The typography and three-times oversampled print plate carry over the previous edition's newspaper design. The ink palette uses Astryx Stone Light's neutral 15, red 30 and blue 30. The cream stock and plate wear are rendered separately.

The program is MIT-licensed. The Newsreader and Source Sans 3 type masks are covered by the licenses in `fonts/`.

# NBA player similarity

Minimal Python project for the [project work plan](WORKPLAN.md).
Requires Python 3.12 or newer and `uv`.

From this directory, install the project into its isolated environment:

```sh
uv sync
```

Run the lightweight import smoke test with Python's standard-library test runner:

```sh
uv run python -m unittest discover -s tests -v
```

The package uses a `src/` layout and has no runtime dependencies. This setup
does not retrieve data or implement the planned similarity methodology.

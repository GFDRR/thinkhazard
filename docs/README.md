# ThinkHazard! Documentation

This directory contains the methodology documentation for ThinkHazard!, built with [Jupyter Book](https://jupyterbook.org/).

## Building the Documentation

### Prerequisites

You need Python 3.7+ and pip installed on your system.

### Installation

1. Install the required dependencies:

```bash
pip install -r requirements.txt
```

### Building the book

To build the HTML version of the book:

```bash
jupyter-book build .
```

The built HTML files will be in `_build/html/`. You can open `_build/html/index.html` in your web browser to view the documentation.

### Cleaning build files

To remove previously built files:

```bash
jupyter-book clean .
```

To remove all build files including cached notebooks:

```bash
jupyter-book clean . --all
```

## Documentation Structure

The documentation is organized as follows:

- [`intro.md`](intro.md) - Introduction to ThinkHazard!
- [`hazard-types.md`](hazard-types.md) - Overview of hazard types covered
- [`hazard-data.md`](hazard-data.md) - Hazard data classification methodology
- [`drr-guidance.md`](drr-guidance.md) - Disaster risk reduction guidance
- [`workflow.md`](workflow.md) - Technical workflow and architecture
- [`hazard-methods.md`](hazard-methods.md) - Hazard-specific classification methods
- [`api.md`](api.md) - API documentation
- [`data-references.md`](data-references.md) - Data sources and licenses

## Publishing

### GitHub Pages

To publish to GitHub Pages, you can use the `ghp-import` package:

```bash
pip install ghp-import
ghp-import -n -p -f _build/html
```

This will push the built HTML to the `gh-pages` branch of your repository.

Alternatively, you can set up GitHub Actions to automatically build and deploy the documentation on every commit. See the [Jupyter Book documentation](https://jupyterbook.org/publish/gh-pages.html) for more details.

## Configuration

The book's configuration is in [`_config.yml`](_config.yml) and the table of contents is defined in [`_toc.yml`](_toc.yml).

## Migrated from Slate

This documentation was migrated from the original Slate-based documentation in the [thinkhazardmethods repository](https://github.com/GFDRR/thinkhazardmethods). The content has been converted to modern Jupyter Book format with improved formatting and organization.

## Contributing

To contribute to the documentation:

1. Edit the relevant `.md` files
2. Build the book locally to preview your changes
3. Submit a pull request with your changes

## License

This documentation is licensed under CC-BY-SA. See the main README for more information.

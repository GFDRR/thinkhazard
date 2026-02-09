# ThinkHazard! Documentation

This directory contains the methodology documentation for ThinkHazard!, built with [Jupyter Book 2](https://jupyterbook.org/) (MyST-based).

## Building the Documentation

### Prerequisites

You need Python 3.9+ and pip installed on your system.

### Installation

1. Install the required dependencies:

```bash
pip install -r requirements.txt
```

### Building the book

To build the HTML version of the book:

```bash
# 1. Generate JSON files from CSV data
python convert_csv_to_json.py

# 2. Build the documentation with Jupyter Book 2 (uses myst.yml)
jupyter book build --html

# 3. Copy query builder and JSON files to build output
bash copy_static_files.sh
```

The built HTML files will be in `_build/html/`.

### Inspecting the book

To preview the documentation locally:

```bash
# Start a simple HTTP server
cd _build/html
python -m http.server 3100
```

Then open http://localhost:3100 in your browser.

### Cleaning build files

To remove previously built files:

```bash
jupyter book clean
```

To remove all build files including cached notebooks:

```bash
jupyter book clean --all
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

## Query Builder

The documentation includes an interactive query builder tool for finding administrative division and urban area codes:

- **Source files:**
  - `query_builder.html` - Interactive search interface (in `docs/` root)
  - `public/TH_ADM2.csv` - Administrative divisions source data
  - `public/TH_URB.csv` - Urban areas source data
  - `public/divisions_flat.json` - 43,202 divisions (generated, committed)
  - `public/urban_areas.json` - 2,919 urban areas (generated, committed)
  - `public/countries.json` - 245 countries (generated, committed)

- **Data generation:**
  ```bash
  python convert_csv_to_json.py
  ```
  This reads the CSV files from `public/` and generates JSON files in `public/`.

- **Deployment:**
  The `copy_static_files.sh` script copies JSON files from `public/` and the query builder to `_build/html/` for deployment.

## Publishing

### GitHub Pages

The project uses GitHub Actions for automatic deployment. See `.github/workflows/gh-pages.yml` for the configuration.

For detailed deployment instructions, see [DEPLOYMENT.md](DEPLOYMENT.md).

## Configuration

The book's configuration is in [`myst.yml`](myst.yml) (Jupyter Book 2/MyST format) and the table of contents is defined in [`_toc.yml`](_toc.yml).

## Migrated from Slate

This documentation was migrated from the original Slate-based documentation in the [thinkhazardmethods repository](https://github.com/GFDRR/thinkhazardmethods). The content has been converted to modern Jupyter Book format with improved formatting and organization.

## Contributing

To contribute to the documentation:

1. Edit the relevant `.md` files
2. Build the book locally to preview your changes
3. Submit a pull request with your changes

## License

This documentation is licensed under CC-BY-SA. See the main README for more information.

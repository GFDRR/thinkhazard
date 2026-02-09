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
# 1. Generate JSON files from CSV data
python convert_csv_to_json.py

# 2. Build the documentation
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

**Note:** Don't use `jupyter book start` - it doesn't properly serve the JSON files and query builder. Use the Python HTTP server instead.

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
  - `_static/TH_ADM2.csv` - Administrative divisions source data
  - `_static/TH_URB.csv` - Urban areas source data
  - `_static/divisions_flat.json` - 43,202 divisions (generated, committed)
  - `_static/urban_areas.json` - 2,919 urban areas (generated, committed)
  - `_static/countries.json` - 245 countries (generated, committed)

- **Data generation:**
  ```bash
  python convert_csv_to_json.py
  ```
  This reads the CSV files from `_static/` and generates JSON files in `_static/`.

- **Deployment:**
  The `copy_static_files.sh` script copies JSON files from `_static/` and the query builder to `_build/html/` for deployment.

## Publishing

### GitHub Pages

**Recommended: Use the Jupyter Book built-in GitHub Actions setup:**

```bash
cd docs
jupyter book init --gh-pages
```

This will generate a `.github/workflows/deploy.yml` file. You'll need to customize it to include our JSON generation and copy steps. See [DEPLOYMENT.md](DEPLOYMENT.md) for complete instructions.

**Alternative: Manual deployment with ghp-import:**

```bash
pip install ghp-import
cd docs
python convert_csv_to_json.py
jupyter book build --html
bash copy_static_files.sh
ghp-import -n -p -f _build/html
```

For detailed deployment instructions and GitHub Actions configuration, see [DEPLOYMENT.md](DEPLOYMENT.md).

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

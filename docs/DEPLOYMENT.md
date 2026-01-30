# Deployment Guide

This guide explains how to build and deploy the ThinkHazard! documentation with the integrated query builder.

## Quick Start

```bash
cd docs

# 1. Generate JSON files from CSV data
python convert_csv_to_json.py

# 2. Build documentation
jupyter-book build .

# 3. Copy query builder and JSON files to build output
bash copy_static_files.sh

# 4. Preview locally
cd _build/html
python -m http.server 3100
# Open http://localhost:3100
```

## File Organization

### Source Files (docs/)

- **Data (in `_static/`):**
  - `TH_ADM2.csv` - Administrative divisions (source data, committed)
  - `TH_URB.csv` - Urban areas (source data, committed)
  - `divisions_flat.json` - 43,202 divisions (generated, committed)
  - `urban_areas.json` - 2,919 urban areas (generated, committed)
  - `countries.json` - 245 countries (generated, committed)

- **Scripts (in `docs/` root):**
  - `convert_csv_to_json.py` - Generates JSON from CSV (outputs to `_static/`)
  - `copy_static_files.sh` - Copies files from `_static/` to `_build/html/`

- **Query Builder (in `docs/` root):**
  - `query_builder.html` - Interactive search tool

### Build Output (_build/html/)
The `_build/html/` directory contains the complete built site:
- All markdown files converted to HTML
- Query builder and JSON files copied from root
- Ready for deployment to GitHub Pages

**Note:** `_build/` is gitignored and should not be committed.

## GitHub Pages Deployment

### Option 1: Manual Deployment

```bash
# Build everything
cd docs
python convert_csv_to_json.py
jupyter-book build .
bash copy_static_files.sh

# Deploy to gh-pages branch
cd _build/html
git init
git add .
git commit -m "Deploy documentation"
git remote add origin https://github.com/GFDRR/thinkhazard.git
git push -f origin HEAD:gh-pages
```

Then enable GitHub Pages in repository settings:
- Settings → Pages
- Source: Deploy from branch
- Branch: `gh-pages`, folder: `/` (root)

### Option 2: GitHub Actions (Recommended)

Create `.github/workflows/deploy-docs.yml`:

```yaml
name: Deploy Documentation

on:
  push:
    branches: [master]
    paths:
      - 'docs/**'
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: pip install jupyter-book

      - name: Generate JSON files
        working-directory: docs
        run: python convert_csv_to_json.py

      - name: Build documentation
        working-directory: docs
        run: jupyter-book build .

      - name: Copy query builder and JSON files
        working-directory: docs
        run: bash copy_static_files.sh

      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./docs/_build/html
```

This will automatically build and deploy whenever you push changes to `docs/`.

## Updating Data

To update the division or urban area data:

1. Update the CSV files in `_static/`:
   - `TH_ADM2.csv` - Administrative divisions
   - `TH_URB.csv` - Urban areas

2. Regenerate JSON:
   ```bash
   python convert_csv_to_json.py
   ```

3. Rebuild and deploy as normal

## Query Builder

The query builder provides an interactive interface for finding division codes:

- **Features:**
  - Search 43,202 administrative divisions
  - Search 2,919 urban areas
  - Tab interface to switch between search modes
  - Auto-generated API endpoints for each location
  - Copy-paste ready URLs

- **Access:**
  - Local: http://localhost:3100/query_builder.html
  - GitHub Pages: https://gfdrr.github.io/thinkhazard/query_builder.html

## Troubleshooting

### "jupyter book start doesn't work"
Don't use `jupyter book start` - it doesn't properly serve the JSON files. Use a simple Python HTTP server instead:
```bash
cd _build/html
python -m http.server 3100
```

### "Query builder shows 'Error loading data'"
Make sure you've run `copy_static_files.sh` after building:
```bash
bash copy_static_files.sh
```

### "JSON files are out of date"
Regenerate from source CSVs:
```bash
python convert_csv_to_json.py
```

## Files Not to Commit

The following are gitignored and should not be committed:
- `_build/` - Build output (regenerated on each build)

## Files to Commit

Always commit these:
- **Source data:**
  - `_static/TH_ADM2.csv` - Administrative divisions source
  - `_static/TH_URB.csv` - Urban areas source
- **Generated data (committed for GitHub Pages):**
  - `_static/divisions_flat.json` - Generated from CSV, committed
  - `_static/urban_areas.json` - Generated from CSV, committed
  - `_static/countries.json` - Generated from CSV, committed
- **Tools:**
  - `query_builder.html` - Query builder interface
  - `convert_csv_to_json.py` - Data generation script
  - `copy_static_files.sh` - Build helper script
- **Documentation:**
  - All `.md` files

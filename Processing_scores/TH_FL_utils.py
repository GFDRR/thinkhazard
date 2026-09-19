# TH_FL_utils.py
# Flood Hazard Threshold Analysis Utilities
# Provides functions for calculating flood hazard scores based on area and value thresholds
# Scores represent the number of selected return periods exceeding both thresholds (0 to N)

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterstats import zonal_stats
from pathlib import Path
import folium
from folium.plugins import MiniMap, Fullscreen
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from IPython.display import display, clear_output, HTML
import time
import multiprocessing as mp
from functools import partial
import itertools as it

import common
from input_utils import get_adm_data


# Functions for parallel processing of zonal_stats
def zonal_stats_partial(feats, raster, stats=[], affine=None, nodata=None, all_touched=True, raster_out=True):
    """Partial zonal stats for parallel processing on a list of features"""
    return zonal_stats(feats, raster, stats=stats, affine=affine, nodata=nodata,
                      all_touched=all_touched, raster_out=raster_out)


def get_flood_raster_paths(country, flood_type, period='2020', scenario='', return_periods=[10, 100, 500, 1000]):
    """
    Construct paths to flood hazard rasters based on input parameters.

    Args:
        country: ISO3 country code
        flood_type: One of 'FLUVIAL_UNDEFENDED', 'FLUVIAL_DEFENDED', 'PLUVIAL_DEFENDED',
                   'COASTAL_UNDEFENDED', 'COASTAL_DEFENDED'
        period: Time period (e.g., '2020', '2030', '2050', '2080')
        scenario: Climate scenario (e.g., 'SSP1-2.6', 'SSP2-4.5', etc.) - only for future periods
        return_periods: List of return periods to include

    Returns:
        dict: Dictionary mapping RP names to file paths
    """
    base_path = Path(common.DATA_DIR) / 'HZD' / country / flood_type / period

    raster_paths = {}
    for rp in return_periods:
        rp_name = f'RP{rp}'

        # Construct filename based on period
        if period == '2020':
            filename = f'1in{rp}.tif'
        else:
            # Future periods include scenario in filename
            filename = f'1in{rp}_{scenario}.tif'

        raster_path = base_path / filename

        if raster_path.exists():
            raster_paths[rp_name] = str(raster_path)
        else:
            print(f"Warning: Raster not found: {raster_path}")

    return raster_paths


def calculate_mean_above_threshold(values, threshold=0):
    """
    Calculate mean of values greater than threshold.
    Returns 0 if no values meet the condition.
    """
    if values is None or len(values) == 0:
        return 0

    filtered_values = [v for v in values if v is not None and v > threshold]

    if len(filtered_values) == 0:
        return 0

    return np.mean(filtered_values)


def calculate_hazard_score(value_threshold, area_threshold_pct, *rp_stats):
    """
    Calculate hazard score based on value and area thresholds.

    Logic:
    - For each return period, check if BOTH value threshold and area threshold are met
    - Score = count of RPs meeting both thresholds (ranges from 0 to N, where N is the number of selected return periods)

    Args:
        value_threshold: Minimum mean value threshold
        area_threshold_pct: Minimum area percentage threshold
        *rp_stats: Tuples of (mean_value, area_pct) for each return period

    Returns:
        int: Hazard score (0 to N, where N = number of return periods)
    """
    score = 0

    for mean_val, area_pct in rp_stats:
        if mean_val >= value_threshold and area_pct >= area_threshold_pct:
            score += 1

    return score


def process_flood_hazard(country, adm_level, flood_types, value_threshold, area_threshold_pct,
                         period='2020', scenario='', return_periods=[10, 100, 500, 1000],
                         use_custom_boundaries=False, custom_boundaries_file_path=None,
                         custom_code_field=None, custom_name_field=None):
    """
    Main processing function for flood hazard threshold analysis.

    Args:
        country: ISO3 country code
        adm_level: Administrative level (0, 1, 2)
        flood_types: List of flood types to process
        value_threshold: Minimum value threshold (cm)
        area_threshold_pct: Minimum area percentage threshold
        period: Time period
        scenario: Climate scenario (for future periods)
        return_periods: List of return periods
        use_custom_boundaries: Whether to use custom boundaries
        custom_boundaries_file_path: Path to custom boundaries file
        custom_code_field: ID field for custom boundaries
        custom_name_field: Name field for custom boundaries

    Returns:
        dict: Dictionary mapping flood types to GeoDataFrames with results
    """
    # Load administrative boundaries
    if use_custom_boundaries and custom_boundaries_file_path:
        print(f"Loading custom boundaries from {custom_boundaries_file_path}...")
        adm_units = gpd.read_file(custom_boundaries_file_path)

        # Ensure required fields are present
        if custom_code_field and custom_name_field:
            adm_units = adm_units[[custom_code_field, custom_name_field, 'geometry']].copy()
            adm_units.rename(columns={
                custom_code_field: 'ADM_CODE',
                custom_name_field: 'ADM_NAME'
            }, inplace=True)
    else:
        print(f"Loading administrative boundaries for {country}, level {adm_level}...")
        adm_units = get_adm_data(country, adm_level)

    print(f"Loaded {len(adm_units)} administrative units")

    # Calculate unit areas in projected CRS
    print("Calculating unit areas...")
    if adm_units.crs is None:
        # Assume WGS84 if no CRS is set
        adm_units = adm_units.set_crs("EPSG:4326")

    if adm_units.crs.is_geographic:
        adm_units_proj = adm_units.to_crs(adm_units.estimate_utm_crs())
        adm_units['unit_area_m2'] = adm_units_proj.geometry.area
    else:
        adm_units['unit_area_m2'] = adm_units.geometry.area

    results = {}

    # Process each flood type
    for flood_type in flood_types:
        print(f"\n{'='*60}")
        print(f"Processing {flood_type}")
        print(f"{'='*60}")

        # Create a copy for this flood type
        adm_flood = adm_units.copy()

        # Get raster paths
        raster_paths = get_flood_raster_paths(country, flood_type, period, scenario, return_periods)

        if not raster_paths:
            print(f"No rasters found for {flood_type}. Skipping...")
            continue

        # Process each return period
        rp_stats = []
        for rp in return_periods:
            rp_name = f'RP{rp}'

            if rp_name not in raster_paths:
                print(f"Skipping {rp_name} - file not found")
                continue

            rp_path = raster_paths[rp_name]
            print(f"\nProcessing {rp_name}...")

            # Calculate zonal statistics using parallel processing
            # Note: We pass nodata=None to rasterstats to get all values,
            # then filter out negative values manually for consistency
            cores = min(len(adm_flood), mp.cpu_count())

            # Split geometries into chunks for parallel processing
            geom_list = list(adm_flood.geometry)
            chunk_size = len(geom_list) // cores + (1 if len(geom_list) % cores else 0)
            geom_chunks = [geom_list[i:i + chunk_size] for i in range(0, len(geom_list), chunk_size)]

            with mp.Pool(cores) as p:
                func = partial(zonal_stats_partial, raster=rp_path, stats=[],
                             all_touched=True, nodata=None, raster_out=True)
                stats_parallel = p.map(func, geom_chunks)

            stats_values = list(it.chain(*stats_parallel))

            # Calculate mean of values > 0 and affected area percentage
            means_above_zero = []
            area_percentages = []

            for idx, stat in enumerate(stats_values):
                unit_area = adm_flood.iloc[idx]['unit_area_m2']

                if stat is not None and 'mini_raster_array' in stat:
                    values = stat['mini_raster_array'].compressed()

                    if len(values) > 0:
                        # Exclude ALL negative values (nodata)
                        # This removes any nodata values (-32767, -32768, etc.)
                        # and keeps only valid flood depths (>= 0)
                        values = values[values >= 0]

                        if len(values) > 0:
                            # Calculate mean of values > 0
                            mean_val = calculate_mean_above_threshold(values, threshold=0)

                            # Count pixels above value threshold
                            affected_pixels = np.sum(values > value_threshold)
                            total_pixels = len(values)

                            # Calculate area percentage
                            area_pct = (affected_pixels / total_pixels) * 100 if total_pixels > 0 else 0
                        else:
                            mean_val = 0
                            area_pct = 0
                    else:
                        mean_val = 0
                        area_pct = 0
                else:
                    mean_val = 0
                    area_pct = 0

                means_above_zero.append(mean_val)
                area_percentages.append(area_pct)

            # Add to dataframe
            adm_flood[f'{rp_name}_mean'] = means_above_zero
            adm_flood[f'{rp_name}_affected_pct'] = area_percentages

            print(f"  Mean statistics: {min(means_above_zero):.2f} - {max(means_above_zero):.2f}")
            print(f"  Affected area %: {min(area_percentages):.2f}% - {max(area_percentages):.2f}%")

            rp_stats.append((means_above_zero, area_percentages))

        # Calculate hazard scores
        print("\nCalculating Hazard Scores...")
        hazard_scores = []

        for i in range(len(adm_flood)):
            # Collect (mean, area_pct) pairs for this unit across all RPs
            unit_stats = []
            for rp in return_periods:
                rp_name = f'RP{rp}'
                if f'{rp_name}_mean' in adm_flood.columns:
                    mean_val = adm_flood.iloc[i][f'{rp_name}_mean']
                    area_pct = adm_flood.iloc[i][f'{rp_name}_affected_pct']
                    unit_stats.append((mean_val, area_pct))

            score = calculate_hazard_score(value_threshold, area_threshold_pct, *unit_stats)
            hazard_scores.append(score)

        adm_flood['Hazard_score'] = hazard_scores

        # Display score distribution
        score_counts = adm_flood['Hazard_score'].value_counts().sort_index()
        print("\nHazard Score Distribution:")
        for score, count in score_counts.items():
            percentage = (count / len(adm_flood)) * 100
            print(f"  Score {score}: {count} units ({percentage:.1f}%)")

        results[flood_type] = adm_flood

    return results


def save_results(results, country, adm_level, value_threshold, area_threshold_pct, period, scenario):
    """
    Save results to GeoPackage and Excel files.

    If files exist, appends new flood types and overwrites existing ones.

    Args:
        results: Dictionary mapping flood types to GeoDataFrames
        country: ISO3 country code
        adm_level: Administrative level
        value_threshold: Value threshold used
        area_threshold_pct: Area threshold percentage used
        period: Time period
        scenario: Climate scenario

    Returns:
        tuple: (gpkg_path, excel_path)
    """
    # Prepare output filenames
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    if period == '2020':
        base_name = f"{country}_FL_hazard_ADM{adm_level}_{period}_vt{value_threshold}_at{area_threshold_pct}"
    else:
        base_name = f"{country}_FL_hazard_ADM{adm_level}_{period}_{scenario}_vt{value_threshold}_at{area_threshold_pct}"

    gpkg_path = Path(common.OUTPUT_DIR) / f"{base_name}.gpkg"
    excel_path = Path(common.OUTPUT_DIR) / f"{base_name}.xlsx"

    # Save to GeoPackage (each flood type as a layer)
    print(f"\nSaving results to {gpkg_path}...")

    # Check existing layers in GeoPackage
    existing_layers = set()
    if gpkg_path.exists():
        import fiona
        existing_layers = set(fiona.listlayers(str(gpkg_path)))

    for flood_type, gdf in results.items():
        layer_name = flood_type
        print(f"  Processing layer '{layer_name}': {len(gdf)} features, Score range: {gdf['Hazard_score'].min()}-{gdf['Hazard_score'].max()}")
        if layer_name in existing_layers:
            print(f"  Overwriting existing layer: {layer_name}")
            # Delete the existing layer first, then write
            import fiona
            with fiona.Env():
                # Remove the layer by opening in append mode and deleting
                import sqlite3
                conn = sqlite3.connect(str(gpkg_path))
                cursor = conn.cursor()
                # Delete from gpkg_contents and gpkg_geometry_columns
                cursor.execute("DELETE FROM gpkg_contents WHERE table_name = ?", (layer_name,))
                cursor.execute("DELETE FROM gpkg_geometry_columns WHERE table_name = ?", (layer_name,))
                # Drop the actual table
                cursor.execute(f"DROP TABLE IF EXISTS \"{layer_name}\"")
                conn.commit()
                conn.close()
            # Now write the new layer
            gdf.to_file(gpkg_path, layer=layer_name, driver="GPKG", mode='a')
        else:
            print(f"  Adding new layer: {layer_name}")
            # Use mode='a' if file exists, otherwise create new
            mode = 'a' if gpkg_path.exists() else 'w'
            gdf.to_file(gpkg_path, layer=layer_name, driver="GPKG", mode=mode)

    # Save to Excel (each flood type as a sheet)
    print(f"Saving results to {excel_path}...")

    # Load existing data if file exists
    existing_data = {}
    existing_sheet_names = set()
    if excel_path.exists():
        import openpyxl
        try:
            existing_wb = pd.ExcelFile(excel_path, engine='openpyxl')
            existing_sheet_names = set(existing_wb.sheet_names)
            for sheet_name in existing_wb.sheet_names:
                # Only keep sheets that are NOT being updated
                if sheet_name not in [ft[:31] for ft in results.keys()]:
                    existing_data[sheet_name] = pd.read_excel(excel_path, sheet_name=sheet_name)
                    print(f"  Preserving existing sheet: {sheet_name}")
                else:
                    print(f"  Will overwrite sheet: {sheet_name}")
            existing_wb.close()
        except Exception as e:
            print(f"  Warning: Could not read existing Excel file: {e}")
            print(f"  Creating new Excel file...")

    # Write all data (existing + new)
    # Use mode='w' to ensure clean write
    with pd.ExcelWriter(excel_path, engine='openpyxl', mode='w') as writer:
        # Write preserved existing sheets first
        for sheet_name, df in existing_data.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)

        # Write new/updated sheets
        for flood_type, gdf in results.items():
            # Drop geometry for Excel
            df = pd.DataFrame(gdf.drop(columns='geometry'))
            sheet_name = flood_type[:31]  # Excel sheet name limit
            print(f"  Processing sheet '{sheet_name}': {len(df)} rows, Score range: {df['Hazard_score'].min()}-{df['Hazard_score'].max()}")
            if sheet_name in existing_sheet_names:
                print(f"  Overwriting existing sheet: {sheet_name}")
            else:
                print(f"  Adding new sheet: {sheet_name}")
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    # Verify data integrity by comparing a sample
    print("\nVerifying data integrity...")
    for flood_type in results.keys():
        layer_name = flood_type
        sheet_name = flood_type[:31]

        # Read back from GPKG
        try:
            gpkg_data = gpd.read_file(gpkg_path, layer=layer_name)
            gpkg_score_sum = gpkg_data['Hazard_score'].sum()

            # Read back from Excel
            excel_data = pd.read_excel(excel_path, sheet_name=sheet_name)
            excel_score_sum = excel_data['Hazard_score'].sum()

            if abs(gpkg_score_sum - excel_score_sum) < 0.001:
                print(f"  ✓ {flood_type}: Data verified (score sum: {gpkg_score_sum:.0f})")
            else:
                print(f"  ✗ {flood_type}: Data MISMATCH! GPKG sum: {gpkg_score_sum:.0f}, Excel sum: {excel_score_sum:.0f}")
        except Exception as e:
            print(f"  ? {flood_type}: Could not verify - {e}")

    return str(gpkg_path), str(excel_path)


def plot_raster_layer(raster_path, rp_name, value_threshold, bounds):
    """
    Create a folium raster layer for flood hazard visualization.

    Args:
        raster_path: Path to the raster file
        rp_name: Return period name (e.g., 'RP10', 'RP100', 'RP1000')
        value_threshold: Minimum value threshold to display
        bounds: Bounding box [minx, miny, maxx, maxy]

    Returns:
        folium.raster_layers.ImageOverlay or None
    """
    import rasterio
    from rasterio.warp import calculate_default_transform, reproject, Resampling
    from rasterio.mask import mask as rio_mask
    from io import BytesIO
    import base64
    from PIL import Image

    # Define colors for return periods using blue shades
    # More frequent (RP5-10) = darker blue, less frequent (RP1000) = lighter blue
    rp_colors = {
        'RP5': (8, 48, 107, 180),        # Dark blue
        'RP10': (33, 102, 172, 180),     # Medium-dark blue
        'RP20': (67, 147, 195, 180),     # Medium blue
        'RP50': (103, 169, 207, 180),    # Medium-light blue
        'RP100': (146, 197, 222, 180),   # Light blue
        'RP200': (186, 218, 235, 180),   # Very light blue
        'RP500': (209, 229, 240, 180),   # Pale blue
        'RP1000': (222, 235, 247, 180)   # Very pale blue
    }

    try:
        with rasterio.open(raster_path) as src:
            # Check if raster needs reprojection to EPSG:4326
            if src.crs != 'EPSG:4326':
                # Reproject to EPSG:4326 for proper alignment with web maps
                from rasterio.warp import calculate_default_transform, reproject, Resampling

                transform, width, height = calculate_default_transform(
                    src.crs, 'EPSG:4326', src.width, src.height, *src.bounds
                )

                # Create output array
                data = np.empty((height, width), dtype=src.dtypes[0])

                reproject(
                    source=rasterio.band(src, 1),
                    destination=data,
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs='EPSG:4326',
                    resampling=Resampling.nearest
                )

                out_transform = transform
                out_image = data
            else:
                # Create bbox polygon for masking
                from shapely.geometry import box
                bbox = box(bounds[0], bounds[1], bounds[2], bounds[3])

                # Read and mask the raster
                out_image, out_transform = rio_mask(src, [bbox], crop=True, all_touched=True)
                out_image = out_image[0]

            # Create binary mask where values > threshold
            mask = out_image > value_threshold

            # Create RGBA image
            height, width = out_image.shape
            rgba = np.zeros((height, width, 4), dtype=np.uint8)

            # Calculate actual bounds from the cropped raster transform BEFORE any resizing
            from rasterio.transform import array_bounds
            actual_bounds = array_bounds(height, width, out_transform)
            left, bottom, right, top = actual_bounds

            # Apply color where mask is True
            # Extract RP number from name (handles both 'RP10' and 'FLUV-RP10' formats)
            rp_key = rp_name.split('-')[-1] if '-' in rp_name else rp_name
            color = rp_colors.get(rp_key, (67, 147, 195, 180))  # Default to medium blue
            rgba[mask] = color

            # Convert to PIL Image
            img = Image.fromarray(rgba, mode='RGBA')

            # Resize if too large (for performance)
            # Note: We calculate bounds before resizing to maintain accuracy
            max_size = 2000
            if max(img.size) > max_size:
                ratio = max_size / max(img.size)
                new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            # Save to bytes
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            img_base64 = base64.b64encode(buffer.read()).decode()

            # Create ImageOverlay
            layer = folium.raster_layers.ImageOverlay(
                image=f'data:image/png;base64,{img_base64}',
                bounds=[[bottom, left], [top, right]],
                opacity=0.6,
                name=f'{rp_name} Flood Extent',
                overlay=True,
                control=True,
                show=True
            )

            return layer

    except Exception as e:
        print(f"Warning: Could not create raster layer for {rp_name}: {str(e)}")
        return None


def plot_results(gdf, flood_type, num_rps):
    """
    Create a folium layer for the results.

    Args:
        gdf: GeoDataFrame with results
        flood_type: Name of the flood type
        num_rps: Number of return periods selected (for dynamic color scaling)

    Returns:
        tuple: (layer, legend_html)
    """
    # Dynamically generate color scheme based on number of return periods
    # Always include gray for score 0, then interpolate from yellow to red
    base_colors = ['#95a5a6']  # Gray for score 0

    if num_rps == 1:
        colors = base_colors + ['#e74c3c']  # Gray, Red
    elif num_rps == 2:
        colors = base_colors + ['#e67e22', '#e74c3c']  # Gray, Orange, Red
    elif num_rps == 3:
        colors = base_colors + ['#f1c40f', '#e67e22', '#e74c3c']  # Gray, Yellow, Orange, Red
    else:
        # For more than 3 RPs, interpolate colors from yellow to red
        cmap = plt.cm.YlOrRd
        colors = base_colors + [mcolors.to_hex(cmap(i / num_rps)) for i in range(1, num_rps + 1)]

    cmap = mcolors.ListedColormap(colors)

    # Create custom vertical legend HTML dynamically
    legend_items = []
    for score in range(num_rps, -1, -1):  # Reverse order (highest to lowest)
        legend_items.append(f'''
        <div style="display: flex; align-items: center; margin-bottom: 4px;">
            <div style="width: 25px; height: 18px; background-color: {colors[score]}; border: 1px solid black; margin-right: 8px;"></div>
            <span>Score {score}</span>
        </div>''')

    legend_html = f'''
    <div style="position: fixed;
                top: 10px;
                left: 10px;
                width: 150px;
                background-color: white;
                border:2px solid grey;
                z-index:9999;
                font-size:12px;
                padding: 8px;
                border-radius: 5px;
                box-shadow: 0 0 15px rgba(0,0,0,0.2);
                ">
        <p style="margin: 0 0 8px 0; font-weight: bold; font-size: 13px;">{flood_type}<br>Hazard Score</p>
        {''.join(legend_items)}
    </div>
    '''

    # Create GeoJson layer with variable opacity
    layer = folium.FeatureGroup(name=f'{flood_type} - Scores', show=True)

    # Add a slider control using custom JavaScript
    for idx, row in gdf.iterrows():
        score = row['Hazard_score']
        color = colors[int(score)] if score < len(colors) else colors[-1]

        folium.GeoJson(
            row.geometry,
            style_function=lambda x, color=color: {
                'fillColor': color,
                'color': 'black',
                'weight': 1,
                'fillOpacity': 0.7,
                'className': 'admin-layer'  # Add class for opacity control
            },
            tooltip=folium.Tooltip(f'Hazard Score: {score}')
        ).add_to(layer)

    return layer, legend_html


def create_summary_chart(results, period, scenario, num_rps):
    """
    Create a summary bar chart comparing hazard scores across flood types.

    Args:
        results: Dictionary mapping flood types to GeoDataFrames
        period: Time period
        scenario: Climate scenario
        num_rps: Number of return periods selected (for dynamic color scaling)

    Returns:
        matplotlib.figure.Figure
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    flood_types = list(results.keys())

    # Dynamically generate score range and colors based on number of RPs
    scores = list(range(num_rps + 1))  # 0 to num_rps

    # Generate color scheme matching the map
    base_colors = ['#95a5a6']  # Gray for score 0

    if num_rps == 1:
        colors = base_colors + ['#e74c3c']  # Gray, Red
    elif num_rps == 2:
        colors = base_colors + ['#e67e22', '#e74c3c']  # Gray, Orange, Red
    elif num_rps == 3:
        colors = base_colors + ['#f1c40f', '#e67e22', '#e74c3c']  # Gray, Yellow, Orange, Red
    else:
        # For more than 3 RPs, interpolate colors from yellow to red
        cmap = plt.cm.YlOrRd
        colors = base_colors + [mcolors.to_hex(cmap(i / num_rps)) for i in range(1, num_rps + 1)]

    # Prepare data
    data = {score: [] for score in scores}

    for flood_type in flood_types:
        gdf = results[flood_type]
        score_counts = gdf['Hazard_score'].value_counts()
        total = len(gdf)

        for score in scores:
            pct = (score_counts.get(score, 0) / total) * 100
            data[score].append(pct)

    # Create stacked bar chart
    bottom = np.zeros(len(flood_types))

    for score in scores:
        ax.bar(flood_types, data[score], bottom=bottom,
               label=f'Score {score}', color=colors[score], alpha=0.8)
        bottom += data[score]

    ax.set_ylabel('Percentage of Units (%)', fontsize=12)
    ax.set_xlabel('Flood Type', fontsize=12)

    if period == '2020':
        title = f'Flood Hazard Score Distribution - {period}'
    else:
        title = f'Flood Hazard Score Distribution - {period} ({scenario})'

    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.legend(loc='upper right')
    ax.set_ylim(0, 100)
    ax.grid(axis='y', alpha=0.3)

    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    return fig


def initialize_tool():
    """
    Initialize and display the flood hazard threshold analysis GUI.
    """
    # Import widget libraries
    import ipywidgets as widgets
    import notebook_utils

    # Load country data
    df = pd.read_csv('countries.csv')
    country_dict = dict(zip(df['NAM_0'], df['ISO_A3']))
    iso_to_country = dict(zip(df['ISO_A3'], df['NAM_0']))

    # Create country selector
    country_selector = notebook_utils.create_country_selector_widget(list(country_dict.keys()))
    country_selector_id = f'country-selector-{id(country_selector)}'
    country_selector.add_class(country_selector_id)

    # Administrative level selector
    adm_level_selector = notebook_utils.adm_level_selector
    adm_level_selector_id = f'adm-level-selector-{id(adm_level_selector)}'
    adm_level_selector.add_class(adm_level_selector_id)

    # Custom boundaries widgets
    custom_boundaries_radio = notebook_utils.custom_boundaries_radio
    custom_boundaries_radio_id = f'custom-boundaries-radio-{id(custom_boundaries_radio)}'
    custom_boundaries_radio.add_class(custom_boundaries_radio_id)

    custom_boundaries_file = notebook_utils.custom_boundaries_file
    custom_boundaries_file_id = f'custom-boundaries-file-{id(custom_boundaries_file)}'
    custom_boundaries_file.add_class(custom_boundaries_file_id)

    custom_boundaries_id_field = widgets.Dropdown(
        options=[],
        value=None,
        description='ID field:',
        disabled=True,
        layout=widgets.Layout(width='250px')
    )
    custom_boundaries_id_field_id = f'custom-boundaries-id-field-{id(custom_boundaries_id_field)}'
    custom_boundaries_id_field.add_class(custom_boundaries_id_field_id)

    custom_boundaries_name_field = widgets.Dropdown(
        options=[],
        value=None,
        description='Name field:',
        disabled=True,
        layout=widgets.Layout(width='250px')
    )
    custom_boundaries_name_field_id = f'custom-boundaries-name-field-{id(custom_boundaries_name_field)}'
    custom_boundaries_name_field.add_class(custom_boundaries_name_field_id)

    select_file_button = notebook_utils.select_file_button

    # Flood type selector (SelectMultiple for three flood types)
    flood_type_selector = widgets.SelectMultiple(
        options=[
            ('River Floods (Undefended)', 'FLUVIAL_UNDEFENDED'),
            ('River Floods (Defended)', 'FLUVIAL_DEFENDED'),
            ('Pluvial Floods', 'PLUVIAL_DEFENDED'),
            ('Coastal Floods (Undefended)', 'COASTAL_UNDEFENDED'),
            ('Coastal Floods (Defended)', 'COASTAL_DEFENDED')
        ],
        value=['FLUVIAL_UNDEFENDED'],
        rows=5,
        description='',
        disabled=False,
        layout=widgets.Layout(width='300px'),
        style={'description_width': '0px'}
    )
    flood_type_selector_id = f'flood-type-selector-{id(flood_type_selector)}'
    flood_type_selector.add_class(flood_type_selector_id)

    # Value threshold input
    value_threshold_input = widgets.IntText(
        value=50,
        description='Value Threshold (cm):',
        disabled=False,
        layout=widgets.Layout(width='250px'),
        style={'description_width': '150px'}
    )
    value_threshold_input_id = f'value-threshold-input-{id(value_threshold_input)}'
    value_threshold_input.add_class(value_threshold_input_id)

    # Area threshold input
    area_threshold_input = widgets.FloatText(
        value=3.0,
        description='Area Threshold (%):',
        disabled=False,
        layout=widgets.Layout(width='250px'),
        style={'description_width': '150px'}
    )
    area_threshold_input_id = f'area-threshold-input-{id(area_threshold_input)}'
    area_threshold_input.add_class(area_threshold_input_id)

    # Period selector
    period_selector = widgets.Dropdown(
        options=['2020', '2030', '2050', '2080'],
        value='2020',
        layout=widgets.Layout(width='250px')
    )
    period_selector_id = f'period-selector-{id(period_selector)}'
    period_selector.add_class(period_selector_id)

    # Scenario selector
    scenario_selector = widgets.Dropdown(
        options=['SSP1-2.6', 'SSP2-4.5', 'SSP3-7.0', 'SSP5-8.5'],
        value='SSP3-7.0',
        layout=widgets.Layout(width='250px')
    )
    scenario_selector_id = f'scenario-selector-{id(scenario_selector)}'
    scenario_selector.add_class(scenario_selector_id)

    # Return periods selector
    return_periods_selector = widgets.SelectMultiple(
        options=[5, 10, 20, 50, 100, 200, 500, 1000],
        value=[10, 100, 500, 1000],
        rows=8,
        disabled=False,
        layout=widgets.Layout(width='250px')
    )
    return_periods_selector_id = f'return-periods-selector-{id(return_periods_selector)}'
    return_periods_selector.add_class(return_periods_selector_id)

    # Raster preview checkbox
    preview_rasters_checkbox = widgets.Checkbox(
        value=False,
        description='Preview hazard rasters',
        disabled=False,
        layout=widgets.Layout(width='250px'),
        style={'description_width': 'initial'}
    )

    # Output widgets
    output = notebook_utils.output_widget
    chart_output = notebook_utils.chart_output
    map_widget = notebook_utils.map_widget

    # Event handlers
    def on_country_change(change):
        with output:
            output.clear_output()
            adm_level_selector.value = None
            notebook_utils.on_country_change(
                change, country_dict, get_adm_data, plot_geospatial_boundaries
            )

    def on_adm_level_change(change):
        notebook_utils.on_adm_level_change(
            change, country_selector, country_dict,
            get_adm_data, plot_geospatial_boundaries
        )

    def plot_geospatial_boundaries(gdf, crs: str = "EPSG:4326"):
        gdf = gdf.set_crs(crs)
        m = folium.Map()
        folium.GeoJson(
            gdf,
            style_function=lambda x: {
                'fillColor': 'none',
                'color': 'black',
                'weight': 1,
                'fillOpacity': 0
            }
        ).add_to(m)
        m.fit_bounds(m.get_bounds())
        map_widget.value = m._repr_html_()
        # Trigger raster preview after boundaries are loaded
        preview_hazard_rasters()

    def select_file(b):
        notebook_utils.select_file(b, update_preview_map)

    def update_custom_boundaries_visibility(*args):
        is_custom = custom_boundaries_radio.value == 'Custom boundaries'
        custom_boundaries_file.disabled = not is_custom
        custom_boundaries_id_field.disabled = not is_custom
        custom_boundaries_name_field.disabled = not is_custom
        select_file_button.disabled = not is_custom
        adm_level_selector.disabled = is_custom
        update_preview_map()

    def update_preview_map(*args):
        if custom_boundaries_radio.value == 'Custom boundaries':
            try:
                gdf = gpd.read_file(custom_boundaries_file.value)
                plot_geospatial_boundaries(gdf)
                notebook_utils.set_default_values(gdf, custom_boundaries_id_field, custom_boundaries_name_field)
            except Exception as e:
                print(f"Error loading custom boundaries: {str(e)}")
        elif country_selector.value:
            country = country_dict.get(country_selector.value)
            adm_level = adm_level_selector.value
            try:
                level = adm_level if adm_level is not None else 0
                gdf = get_adm_data(country, level)
                plot_geospatial_boundaries(gdf)
            except Exception as e:
                print(f"Error loading boundaries: {str(e)}")

    def update_scenario_visibility(*args):
        scenario_selector.layout.display = 'none' if period_selector.value == '2020' else 'block'

    def preview_hazard_rasters(*args):
        """Preview hazard rasters on the map when selections change"""
        try:
            # Check if preview is enabled
            if not preview_rasters_checkbox.value:
                return

            # Check if we have required selections
            if not country_selector.value:
                return

            country = country_dict.get(country_selector.value)
            flood_types = list(flood_type_selector.value) if flood_type_selector.value else []
            period = period_selector.value
            scenario = scenario_selector.value if period != '2020' else ''
            return_periods = list(return_periods_selector.value) if return_periods_selector.value else []
            value_threshold = value_threshold_input.value

            if not flood_types or not return_periods:
                return

            # Get administrative level for bounds calculation
            adm_level = adm_level_selector.value if adm_level_selector.value is not None else 0

            # Load boundaries to get bounds
            if custom_boundaries_radio.value == 'Custom boundaries' and custom_boundaries_file.value:
                gdf = gpd.read_file(custom_boundaries_file.value)
            else:
                gdf = get_adm_data(country, adm_level)

            # Ensure CRS is set
            if gdf.crs is None:
                gdf = gdf.set_crs("EPSG:4326")

            # Calculate bounds
            bounds = gdf.total_bounds
            minx, miny, maxx, maxy = bounds

            # Create map with OpenStreetMap as default
            m = folium.Map(
                location=[(miny + maxy) / 2, (minx + maxx) / 2],
                zoom_start=5,
                tiles='OpenStreetMap',
                attr='OpenStreetMap'
            )

            # Add additional basemap options
            folium.TileLayer(
                tiles='CartoDB positron',
                attr='CartoDB',
                name='CartoDB Positron',
                overlay=False,
                control=True
            ).add_to(m)

            folium.TileLayer(
                tiles='CartoDB dark_matter',
                attr='CartoDB',
                name='CartoDB Dark',
                overlay=False,
                control=True
            ).add_to(m)

            # Add blank tile layer option to disable basemap
            folium.TileLayer(
                tiles='',
                attr='No basemap',
                name='No Basemap',
                overlay=False,
                control=True
            ).add_to(m)

            # Add boundaries
            folium.GeoJson(
                gdf,
                style_function=lambda x: {
                    'fillColor': 'none',
                    'color': 'black',
                    'weight': 1,
                    'fillOpacity': 0
                }
            ).add_to(m)

            # Add raster layers
            bounds_array = [minx, miny, maxx, maxy]
            for flood_type in flood_types:
                raster_paths = get_flood_raster_paths(country, flood_type, period, scenario, return_periods)

                # Sort return periods in descending order
                sorted_rps = sorted(return_periods, reverse=True)

                for rp in sorted_rps:
                    rp_name = f'RP{rp}'
                    if rp_name in raster_paths:
                        raster_layer = plot_raster_layer(
                            raster_paths[rp_name],
                            f'{flood_type[:4]}-{rp_name}',  # Shorter name for preview
                            value_threshold,
                            bounds_array
                        )
                        if raster_layer:
                            raster_layer.add_to(m)

            # Fit bounds
            m.fit_bounds([[miny, minx], [maxy, maxx]])

            # Add layer control
            folium.LayerControl().add_to(m)

            # Update map widget
            with map_widget.hold_trait_notifications():
                map_widget.value = m._repr_html_()

        except Exception as e:
            # Print error for debugging
            with output:
                print(f"Preview error: {str(e)}")
                import traceback
                traceback.print_exc()

    # Attach observers
    country_selector.observe(on_country_change, names='value')
    adm_level_selector.observe(on_adm_level_change, names='value')
    custom_boundaries_radio.observe(update_custom_boundaries_visibility, 'value')
    select_file_button.on_click(select_file)
    period_selector.observe(update_scenario_visibility, 'value')
    update_scenario_visibility()

    # Attach hazard preview observers
    preview_rasters_checkbox.observe(preview_hazard_rasters, 'value')
    flood_type_selector.observe(preview_hazard_rasters, 'value')
    return_periods_selector.observe(preview_hazard_rasters, 'value')
    period_selector.observe(preview_hazard_rasters, 'value')
    scenario_selector.observe(preview_hazard_rasters, 'value')
    value_threshold_input.observe(preview_hazard_rasters, 'value')

    # Run button
    run_button = notebook_utils.run_button

    # Run analysis function
    def run_analysis_script(b):
        run_button.disabled = True
        run_button.description = "Analysis Running..."
        try:
            with output:
                output.clear_output(wait=True)

                # Validate inputs
                country = country_dict.get(country_selector.value, False)
                if not country:
                    print("Error: Please select a country.")
                    return

                adm_level = adm_level_selector.value
                flood_types = list(flood_type_selector.value)
                value_threshold = value_threshold_input.value
                area_threshold_pct = area_threshold_input.value
                period = period_selector.value
                scenario = scenario_selector.value if period != '2020' else ''
                return_periods = list(return_periods_selector.value)

                if not flood_types:
                    print("Error: Please select at least one flood type.")
                    return

                if not return_periods:
                    print("Error: Please select at least one return period.")
                    return

                # Handle custom boundaries
                use_custom_boundaries = custom_boundaries_radio.value == 'Custom boundaries'

                if use_custom_boundaries:
                    custom_boundaries_file_path = custom_boundaries_file.value
                    custom_code_field = custom_boundaries_id_field.value
                    custom_name_field = custom_boundaries_name_field.value
                else:
                    custom_boundaries_file_path = None
                    custom_code_field = None
                    custom_name_field = None

                start_time = time.perf_counter()

                print(f"Starting analysis for {iso_to_country[country]} ({country})...")
                print(f"Value Threshold: {value_threshold} cm")
                print(f"Area Threshold: {area_threshold_pct}%")
                print(f"Return Periods: {return_periods}")
                print(f"Flood Types: {flood_types}")

                # Run the analysis
                results = process_flood_hazard(
                    country, adm_level, flood_types, value_threshold, area_threshold_pct,
                    period, scenario, return_periods,
                    use_custom_boundaries, custom_boundaries_file_path,
                    custom_code_field, custom_name_field
                )

                if not results:
                    print("No results generated. Please check your input data.")
                    return

                # Save results
                gpkg_path, excel_path = save_results(
                    results, country, adm_level, value_threshold, area_threshold_pct, period, scenario
                )

                print(f"\nAnalysis completed in {time.perf_counter() - start_time:.2f} seconds")
                print(f"Results saved to GeoPackage: {gpkg_path}")
                print(f"Results saved to Excel: {excel_path}")

                # Plot results on map
                print("\nGenerating preview map...")
                # Create map with option to disable basemap
                m = folium.Map(
                    location=[0, 0],
                    zoom_start=5,
                    tiles='OpenStreetMap',
                    attr='OpenStreetMap'
                )

                # Add a blank tile layer option to disable basemap
                folium.TileLayer(
                    tiles='',
                    attr='No basemap',
                    name='No Basemap',
                    overlay=False,
                    control=True
                ).add_to(m)

                layers = []
                colormaps = []
                raster_layers = []
                minx, miny, maxx, maxy = float('inf'), float('inf'), float('-inf'), float('-inf')

                # Collect bounds first
                for flood_type, gdf in results.items():
                    bounds = gdf.total_bounds
                    minx = min(minx, bounds[0])
                    miny = min(miny, bounds[1])
                    maxx = max(maxx, bounds[2])
                    maxy = max(maxy, bounds[3])

                # Set map bounds
                if minx != float('inf'):
                    center_lat = (miny + maxy) / 2
                    center_lon = (minx + maxx) / 2
                    m.location = [center_lat, center_lon]
                    m.fit_bounds([[miny, minx], [maxy, maxx]])

                bounds_array = [minx, miny, maxx, maxy]

                # Add raster layers in correct order: RP1000 -> RP100 -> RP10 (bottom to top)
                print("Adding flood raster layers...")
                for flood_type in flood_types:
                    raster_paths = get_flood_raster_paths(country, flood_type, period, scenario, return_periods)

                    # Sort return periods in descending order (1000, 100, 10) so RP10 is on top
                    sorted_rps = sorted(return_periods, reverse=True)

                    for rp in sorted_rps:
                        rp_name = f'RP{rp}'
                        if rp_name in raster_paths:
                            raster_layer = plot_raster_layer(
                                raster_paths[rp_name],
                                rp_name,
                                value_threshold,
                                bounds_array
                            )
                            if raster_layer:
                                raster_layer.add_to(m)

                # Add administrative boundary layers (top layer)
                print("Adding administrative boundary layers...")
                legend_htmls = []
                num_rps = len(return_periods)
                for flood_type, gdf in results.items():
                    layer, legend_html = plot_results(gdf, flood_type, num_rps)
                    layers.append(layer)
                    legend_htmls.append(legend_html)
                    layer.add_to(m)

                # Add custom legends and controls with fullscreen support
                controls_html = """
                <style>
                    /* Ensure controls remain visible in fullscreen */
                    .custom-control {
                        position: fixed !important;
                        z-index: 999999 !important;
                    }

                    /* Additional fullscreen-specific rules */
                    body:-webkit-full-screen .custom-control,
                    body:-moz-full-screen .custom-control,
                    body:fullscreen .custom-control,
                    .leaflet-container:-webkit-full-screen .custom-control,
                    .leaflet-container:-moz-full-screen .custom-control,
                    .leaflet-container:fullscreen .custom-control {
                        position: fixed !important;
                        z-index: 999999 !important;
                        display: block !important;
                    }
                </style>
                """

                # Add legends with fullscreen support
                for idx, legend_html in enumerate(legend_htmls):
                    # Modify legend HTML to add custom-control class
                    legend_with_class = legend_html.replace(
                        '<div style="position: fixed;',
                        '<div class="custom-control legend-control" style="position: fixed;'
                    )
                    legend_with_class = legend_with_class.replace(
                        'z-index:9999;',
                        'z-index:999999;'
                    )
                    m.get_root().html.add_child(folium.Element(legend_with_class))

                # Add opacity control slider with fullscreen support - centered at bottom
                opacity_html = """
                <div class="custom-control opacity-control" style="position: fixed;
                            bottom: 10px;
                            left: 50%;
                            transform: translateX(-50%);
                            width: 250px;
                            height: 60px;
                            background-color: white;
                            border:2px solid grey;
                            z-index:999999;
                            font-size:12px;
                            padding: 8px;
                            border-radius: 5px;
                            box-shadow: 0 0 15px rgba(0,0,0,0.2);
                            box-sizing: border-box;
                            ">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                    <span style="font-size: 13px; font-weight: bold;">ADM Opacity</span>
                    <span id="opacityValue" style="font-size: 13px; font-weight: bold;">70%</span>
                </div>
                <input type="range" min="0" max="100" value="70" class="slider" id="opacitySlider"
                       style="width: 100%; margin: 0;">
                </div>

                <script>
                setTimeout(function() {
                    var slider = document.getElementById("opacitySlider");
                    var output = document.getElementById("opacityValue");

                    if (slider && output) {
                        slider.oninput = function() {
                            output.innerHTML = this.value + "%";
                            var opacity = this.value / 100;

                            // Update all GeoJSON polygon opacities
                            var svgElements = document.querySelectorAll('path[stroke="black"]');
                            svgElements.forEach(function(path) {
                                // Check if this is likely an admin boundary (has fill)
                                var fill = path.getAttribute('fill');
                                if (fill && fill !== 'none') {
                                    path.setAttribute('fill-opacity', opacity);
                                }
                            });
                        };
                    }
                }, 1000);
                </script>
                """

                m.get_root().html.add_child(folium.Element(controls_html))
                m.get_root().html.add_child(folium.Element(opacity_html))

                # Add controls
                folium.LayerControl(position='topright', collapsed=False).add_to(m)
                MiniMap(toggle_display=True, position='bottomright').add_to(m)
                Fullscreen(position='bottomleft').add_to(m)

                map_widget.value = m._repr_html_()

                # Export map if checkbox is enabled
                if notebook_utils.export_charts_chk.value:
                    maps_dir = Path(common.OUTPUT_DIR) / 'maps'
                    maps_dir.mkdir(exist_ok=True)

                    # Create filename
                    if period == '2020':
                        map_filename = f"{country}_FL_threshold_{period}_vt{value_threshold}_at{area_threshold_pct}.html"
                    else:
                        map_filename = f"{country}_FL_threshold_{period}_{scenario}_vt{value_threshold}_at{area_threshold_pct}.html"

                    map_path = maps_dir / map_filename
                    m.save(str(map_path))
                    print(f"Map exported to: {map_path}")

                # Create summary chart
                with chart_output:
                    clear_output(wait=True)
                    if len(results) > 0:
                        chart = create_summary_chart(results, period, scenario, num_rps)
                        display(chart)

                        # Export chart if checkbox is enabled
                        if notebook_utils.export_charts_chk.value:
                            chart_dir = Path(common.OUTPUT_DIR) / 'charts'
                            chart_dir.mkdir(exist_ok=True)

                            # Create filename
                            if period == '2020':
                                chart_filename = f"{country}_FL_threshold_{period}_vt{value_threshold}_at{area_threshold_pct}.png"
                            else:
                                chart_filename = f"{country}_FL_threshold_{period}_{scenario}_vt{value_threshold}_at{area_threshold_pct}.png"

                            chart_path = chart_dir / chart_filename
                            chart.savefig(chart_path, dpi=300, bbox_inches='tight')
                            print(f"Chart exported to: {chart_path}")

                        plt.close(chart)

        except Exception as e:
            print(f"An error occurred during analysis: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            run_button.disabled = False
            run_button.description = "Run Analysis"

    run_button.on_click(run_analysis_script)

    # Create UI components
    country_boundaries = notebook_utils.create_country_boundaries(
        country_selector, adm_level_selector, custom_boundaries_radio,
        select_file_button, custom_boundaries_file,
        custom_boundaries_id_field, custom_boundaries_name_field
    )

    # Hazard info section
    hazard_info_content = widgets.VBox([
        widgets.HTML(value='<b>Flood Types</b>'),
        flood_type_selector,
        widgets.HTML(value='<br><b>Thresholds</b>'),
        value_threshold_input,
        area_threshold_input,
        widgets.HTML(value='<br><b>Time Period</b>'),
        period_selector,
        scenario_selector,
        widgets.HTML(value='<br><b>Return Periods</b>'),
        return_periods_selector,
        widgets.HTML(value='<br>'),
        preview_rasters_checkbox
    ], layout=widgets.Layout(padding='10px'))

    # Arrange sections in tabs
    tabs = widgets.Tab(layout={'width': '350px', 'height': '500px'})
    tabs.children = [country_boundaries, hazard_info_content]
    tabs.set_title(0, 'Boundaries')
    tabs.set_title(1, 'Hazard')

    # Remove colored borders
    for child in tabs.children:
        child.layout.border = None
        child.layout.padding = '5px'

    # Info box
    info_box = notebook_utils.info_box
    info_box.add_class('info-box')

    # Footer
    footer = notebook_utils.create_footer()

    # Sidebar
    sidebar = notebook_utils.create_sidebar(info_box, tabs, output, footer)

    # Header
    header = notebook_utils.create_header_widget(hazard="FL_THRESHOLD")

    # Get UI components
    map_and_chart, content_layout, final_layout = notebook_utils.get_ui_components(sidebar, header, map_widget)

    # Display the layout
    display(final_layout)

    # Initial updates
    update_custom_boundaries_visibility()
    update_scenario_visibility()

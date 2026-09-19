# TH_HZD_utils.py
# Multi-Hazard Threshold Analysis Utilities
# Provides functions for calculating hazard scores for various natural hazards

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


# HAZARD CONFIGURATION
# Paths are relative to the DATA_DIR from common.py
HAZARD_CONFIG = {
    'earthquake': {
        'name': 'Earthquake',
        'default_threshold': 80,  # Not used - RP-specific thresholds apply
        'default_area_threshold': 5.0,
        'unit': 'PGA-g',
        'folder': 'HZD/GLB/EQ',
        'files': ['GAR17_pga250.tif', 'GAR17_pga475.tif', 'GAR17_pga975.tif', 'GAR17_pga2475.tif'],
        'rp_names': ['RP250', 'RP475', 'RP975', 'RP2475'],
        'type': 'raster_rp_thresholds',  # Special type for RP-specific thresholds
        'not_affected': True,  # Score -1 for areas with no pixels exceeding thresholds
        'rp_thresholds': {
            'RP250': 120,   # >120 PGA-g
            'RP475': 100,   # >100 PGA-g
            'RP975': 80,    # >80 PGA-g
            'RP2475': 60    # >60 PGA-g
        }
    },
    'landslide': {
        'name': 'Landslide',
        'default_threshold': 0,
        'default_area_threshold': 2.0,
        'unit': 'Index',
        'folder': 'HZD/GLB/LS',
        'files': ['LS_CDRI_baseline.tif'],
        'rp_names': ['Index'],
        'type': 'raster_remap',
        'remap': {1: -1, 2: 0, 3: 1, 4: 2, 5: 3}  # Index 1 = not affected
    },
    'tsunami': {
        'name': 'Tsunami',
        'default_threshold': 1,  # Not used - RP-specific thresholds apply
        'default_area_threshold': 0.0,
        'unit': 'm',
        'folder': 'HZD/GLB/TS',
        'files': ['RP100.tif', 'RP500.tif', 'RP2500.tif'],
        'rp_names': ['RP100', 'RP500', 'RP2500'],
        'type': 'raster_tsunami',  # Special type for tsunami (uses majority, different scoring)
        'not_affected': True,
        'rp_thresholds': {
            'RP100': 2.0,  # meters
            'RP500': 1.0,  # meters
            'RP2500': 0.5  # meters
        }
    },
    'volcano': {
        'name': 'Volcano',
        'default_threshold': 2,
        'default_area_threshold': 3.0,
        'unit': 'VEI',
        'folder': 'HZD/GLB/VEI',
        'files': ['VEI_buffered.gpkg'],
        'type': 'vector_intersect',
        'field': 'VEI',
        'not_affected': True,  # Score -1 for areas outside VEI buffers
        'remap': {
            'ranges': [
                (0, 2, -1),      # VEI < 2: no hazard
                (2, 3, 0),       # VEI 2-3: score 0
                (3, 4, 1),       # VEI 3-4: score 1
                (4, 5, 2),       # VEI 4-5: score 2
                (5, 999, 3)      # VEI > 5: score 3
            ]
        }
    },
    'cyclone': {
        'name': 'Cyclone',
        'default_threshold': 36,  # Not used - RP-specific thresholds apply
        'default_area_threshold': 5.0,
        'unit': 'm/s',
        'folder': 'HZD/GLB/STORM/2020',
        'files': ['1in50.tif', '1in100.tif', '1in1000.tif', '1in10000.tif'],
        'rp_names': ['RP50', 'RP100', 'RP1000', 'RP10000'],
        'type': 'raster_rp_thresholds',  # Special type for RP-specific thresholds
        'not_affected': True,  # Score -1 for areas with no pixels exceeding thresholds
        'rp_thresholds': {
            'RP50': 36,      # >36 m/s
            'RP100': 36,     # >36 m/s
            'RP1000': 30,    # >30 m/s
            'RP10000': 26    # >26 m/s
        }
    },
    'extreme_heat': {
        'name': 'Extreme Heat',
        'default_threshold': 28,  # Not used - RP-specific thresholds apply
        'default_area_threshold': 30.0,
        'unit': 'WBGT °C',
        'folder': 'HZD/GLB/HS',
        'files': ['RP5.tif', 'RP20.tif', 'RP100.tif'],
        'rp_names': ['RP5', 'RP20', 'RP100'],
        'type': 'raster_heat',  # Special type for RP-specific thresholds
        'rp_thresholds': {
            'RP5': 32,    # >32°C = High
            'RP20': 28,   # >28°C = Medium
            'RP100': 25   # >25°C = Low
        }
    },
    'wildfire': {
        'name': 'Wildfire',
        'default_threshold': 50,
        'default_area_threshold': 20.0,
        'unit': 'FWI',
        'folder': 'HZD/GLB/FWI',
        'files': ['RP5.tif', 'RP25.tif', 'RP50.tif'],
        'rp_names': ['RP5', 'RP25', 'RP50'],
        'type': 'raster_mean',
        'not_affected': True  # Score -1 for areas with no FWI values > 0
    },
    'water_scarcity': {
        'name': 'Water Scarcity',
        'default_threshold': 1,
        'unit': 'TBD',
        'folder': 'HZD/GLB/WS',
        'files': [],
        'type': 'wip'
    }
}


# Functions for parallel processing of zonal_stats
def zonal_stats_partial(feats, raster, stats=[], affine=None, nodata=None, all_touched=True, raster_out=True):
    """Partial zonal stats for parallel processing on a list of features"""
    return zonal_stats(feats, raster, stats=stats, affine=affine, nodata=nodata,
                      all_touched=all_touched, raster_out=raster_out)


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


def calculate_hazard_score_raster(value_threshold, area_threshold_pct, *rp_stats):
    """
    Calculate hazard score based on area threshold for raster data.

    Logic:
    - For each return period, check if area threshold is met
    - Area is calculated as percentage of pixels with values > value_threshold
    - Score = count of RPs meeting area threshold (0, 1, 2, or 3)

    Args:
        value_threshold: Value threshold (used to identify affected pixels)
        area_threshold_pct: Minimum area percentage threshold
        *rp_stats: Tuples of (mean_value, area_pct) for each return period
                   Note: mean_value is kept for backwards compatibility but not used in scoring

    Returns:
        int: Hazard score (0-3)
    """
    score = 0

    for mean_val, area_pct in rp_stats:
        # Only check if area percentage meets threshold
        # The area_pct already represents pixels with values > value_threshold
        if area_pct >= area_threshold_pct:
            score += 1

    return score


def process_raster_mean_hazard(adm_units, hazard_key, value_threshold, area_threshold_pct):
    """
    Process hazard types that use raster area-based approach (earthquake, cyclone, wildfire).

    Logic:
    - For each RP scenario, calculate the area percentage with values > value_threshold
    - If area percentage >= area_threshold_pct, the RP contributes +1 to hazard score
    - Final score = sum of RPs meeting the area threshold (0-3)
    - For cyclone: if no pixels exceed threshold in ANY RP, score = -1 (not affected)
    - For wildfire: if area with FWI > 0 doesn't meet area_threshold_pct in ANY RP, score = -1 (not affected)
      This means even if some pixels have FWI > 0, if the affected area is too small (< area_threshold_pct),
      the unit is considered "not affected" by wildfire risk.

    Args:
        adm_units: GeoDataFrame with administrative boundaries
        hazard_key: Key to HAZARD_CONFIG dictionary
        value_threshold: Minimum value threshold to identify affected pixels
        area_threshold_pct: Minimum area percentage threshold for scoring

    Returns:
        GeoDataFrame with hazard scores and statistics (scores: -1, 0-3 for cyclone/wildfire; 0-3 for earthquake)
    """
    config = HAZARD_CONFIG[hazard_key]
    print(f"\n{'='*60}")
    print(f"Processing {config['name']} Hazard")
    print(f"{'='*60}")

    adm_hazard = adm_units.copy()

    # Process each raster layer
    rp_stats = []
    for rp_name, filename in zip(config['rp_names'], config['files']):
        raster_path = Path(common.DATA_DIR) / config['folder'] / filename

        if not raster_path.exists():
            print(f"Warning: Raster not found: {raster_path}")
            continue

        print(f"\nProcessing {rp_name}...")

        # Calculate zonal statistics using parallel processing
        cores = min(len(adm_hazard), mp.cpu_count())

        # Split geometries into chunks for parallel processing
        geom_list = list(adm_hazard.geometry)
        chunk_size = len(geom_list) // cores + (1 if len(geom_list) % cores else 0)
        geom_chunks = [geom_list[i:i + chunk_size] for i in range(0, len(geom_list), chunk_size)]

        with mp.Pool(cores) as p:
            func = partial(zonal_stats_partial, raster=str(raster_path), stats=[],
                         all_touched=True, nodata=-9999, raster_out=True)
            stats_parallel = p.map(func, geom_chunks)

        stats_values = list(it.chain(*stats_parallel))

        # Calculate mean of values > 0 and affected area percentage
        means_above_zero = []
        area_percentages = []
        area_above_zero_pcts = []  # For wildfire: track % of area with FWI > 0

        for idx, stat in enumerate(stats_values):
            unit_area = adm_hazard.iloc[idx]['unit_area_m2']

            if stat is not None and 'mini_raster_array' in stat:
                values = stat['mini_raster_array'].compressed()

                if len(values) > 0:
                    # Calculate mean of values > 0
                    mean_val = calculate_mean_above_threshold(values, threshold=0)

                    # Count pixels above value threshold
                    affected_pixels = np.sum(values > value_threshold)
                    total_pixels = len(values)

                    # Calculate area percentage (pixels > value_threshold)
                    area_pct = (affected_pixels / total_pixels) * 100 if total_pixels > 0 else 0

                    # For wildfire: also track percentage of pixels with any FWI > 0
                    if hazard_key == 'wildfire':
                        pixels_above_zero = np.sum(values > 0)
                        area_pct_above_zero = (pixels_above_zero / total_pixels) * 100 if total_pixels > 0 else 0
                        area_above_zero_pcts.append(area_pct_above_zero)
                else:
                    mean_val = 0
                    area_pct = 0
                    if hazard_key == 'wildfire':
                        area_above_zero_pcts.append(0)
            else:
                mean_val = 0
                area_pct = 0
                if hazard_key == 'wildfire':
                    area_above_zero_pcts.append(0)

            means_above_zero.append(mean_val)
            area_percentages.append(area_pct)

        # Add to dataframe
        adm_hazard[f'{rp_name}_mean'] = means_above_zero
        adm_hazard[f'{rp_name}_affected_pct'] = area_percentages

        # For wildfire: also store area > 0 percentage
        if hazard_key == 'wildfire':
            adm_hazard[f'{rp_name}_area_above_zero_pct'] = area_above_zero_pcts

        print(f"  Mean statistics: {min(means_above_zero):.2f} - {max(means_above_zero):.2f}")
        print(f"  Affected area %: {min(area_percentages):.2f}% - {max(area_percentages):.2f}%")

        rp_stats.append((means_above_zero, area_percentages))

    # Calculate hazard scores
    print("\nCalculating Hazard Scores...")
    hazard_scores = []

    for i in range(len(adm_hazard)):
        # Collect (mean, area_pct) pairs for this unit across all RPs
        unit_stats = []
        for rp_name in config['rp_names']:
            if f'{rp_name}_mean' in adm_hazard.columns:
                mean_val = adm_hazard.iloc[i][f'{rp_name}_mean']
                area_pct = adm_hazard.iloc[i][f'{rp_name}_affected_pct']
                unit_stats.append((mean_val, area_pct))

        score = calculate_hazard_score_raster(value_threshold, area_threshold_pct, *unit_stats)

        # For cyclone: if no pixels exceed threshold (area_pct = 0) in ALL RPs, mark as not affected (-1)
        if hazard_key == 'cyclone':
            all_zero = all(area_pct == 0 for _, area_pct in unit_stats)
            if all_zero:
                score = -1

        # For wildfire: mark as not affected (-1) if area with FWI > 0 doesn't meet area threshold in ANY RP
        if hazard_key == 'wildfire':
            # Check if any RP has sufficient area with FWI > 0
            has_sufficient_area = False
            for rp_name in config['rp_names']:
                if f'{rp_name}_area_above_zero_pct' in adm_hazard.columns:
                    area_above_zero = adm_hazard.iloc[i][f'{rp_name}_area_above_zero_pct']
                    if area_above_zero >= area_threshold_pct:
                        has_sufficient_area = True
                        break

            # If no RP has sufficient area with FWI > 0, mark as not affected
            if not has_sufficient_area:
                score = -1

        hazard_scores.append(score)

    adm_hazard['Hazard_score'] = hazard_scores

    # Display score distribution
    score_counts = adm_hazard['Hazard_score'].value_counts().sort_index()
    print("\nHazard Score Distribution:")
    for score, count in score_counts.items():
        percentage = (count / len(adm_hazard)) * 100
        print(f"  Score {score}: {count} units ({percentage:.1f}%)")

    return adm_hazard


def process_landslide_hazard(adm_units, hazard_key, value_threshold, area_threshold_pct):
    """
    Process landslide hazard with area-based index classification.

    Logic:
    - For each admin unit, calculate the total area covered by each landslide index class (1-5)
    - Check if the area of the highest index class exceeds the area threshold
    - Assign hazard score based on the highest index class that meets the area threshold

    Args:
        adm_units: GeoDataFrame with administrative boundaries
        hazard_key: Key to HAZARD_CONFIG dictionary (should be 'landslide')
        value_threshold: Not used for landslide
        area_threshold_pct: Minimum area percentage threshold

    Returns:
        GeoDataFrame with hazard scores
    """
    config = HAZARD_CONFIG[hazard_key]
    print(f"\n{'='*60}")
    print(f"Processing {config['name']} Hazard")
    print(f"{'='*60}")
    print(f"Using area-based classification with {area_threshold_pct}% threshold")

    adm_hazard = adm_units.copy()

    raster_path = Path(common.DATA_DIR) / config['folder'] / config['files'][0]

    if not raster_path.exists():
        print(f"Error: Raster not found: {raster_path}")
        return adm_hazard

    # Check if processing global dataset (large)
    is_global = len(adm_hazard) > 1000  # If more than 1000 units, assume global

    if is_global and 'ISO_A3' in adm_hazard.columns:
        print(f"\nDetected large global dataset ({len(adm_hazard)} units)")
        print(f"Processing sequentially by country to avoid memory issues...")
        print(f"Note: This will be slower but memory-safe for large global rasters.")

        # Get unique countries
        countries = adm_hazard['ISO_A3'].unique()
        print(f"Found {len(countries)} countries to process")

        # Initialize results dictionary to maintain correct order
        stats_dict = {}
        from tqdm import tqdm

        # Process each country sequentially (no multiprocessing to avoid memory issues)
        country_list = list(countries)
        for country in tqdm(country_list, desc="Processing countries"):
            country_mask = adm_hazard['ISO_A3'] == country
            country_indices = adm_hazard[country_mask].index.tolist()
            country_geoms = list(adm_hazard[country_mask].geometry)

            # Process this country sequentially
            try:
                country_stats = zonal_stats(country_geoms, str(raster_path), stats=[],
                                          all_touched=True, nodata=-9999, raster_out=True)

                # Verify we got the right number of results
                if len(country_stats) != len(country_geoms):
                    print(f"\nWarning: {country} returned {len(country_stats)} results for {len(country_geoms)} geometries")
                    while len(country_stats) < len(country_geoms):
                        country_stats.append(None)

                # Store results in dictionary with original indices
                for idx, stat in zip(country_indices, country_stats):
                    stats_dict[idx] = stat

            except Exception as e:
                print(f"\nError processing {country}: {e}")
                # Add None results for this country
                for idx in country_indices:
                    stats_dict[idx] = None

        # Convert dictionary to list in correct order
        stats_values = [stats_dict.get(idx, None) for idx in adm_hazard.index]

        print(f"Completed processing all {len(countries)} countries")
        print(f"Total results: {len(stats_values)}, expected: {len(adm_hazard)}")
    else:
        print(f"\nProcessing landslide index with area-based approach...")

        # For smaller datasets, use parallel processing
        cores = min(len(adm_hazard), mp.cpu_count())

        # Split geometries into smaller chunks to avoid memory issues
        geom_list = list(adm_hazard.geometry)
        # Use smaller chunks - max 100 geometries per chunk
        chunk_size = min(100, len(geom_list) // cores + (1 if len(geom_list) % cores else 0))
        geom_chunks = [geom_list[i:i + chunk_size] for i in range(0, len(geom_list), chunk_size)]

        print(f"Processing {len(geom_list)} units in {len(geom_chunks)} chunks with {cores} cores...")

        # Get raster arrays for each unit
        try:
            with mp.Pool(cores) as p:
                func = partial(zonal_stats_partial, raster=str(raster_path), stats=[],
                             all_touched=True, nodata=-9999, raster_out=True)
                stats_parallel = p.map(func, geom_chunks)

            stats_values = list(it.chain(*stats_parallel))
        except Exception as e:
            print(f"Warning: Parallel processing failed ({e}), falling back to sequential processing...")
            # Fallback to sequential processing
            stats_values = zonal_stats(geom_list, str(raster_path), stats=[],
                                      all_touched=True, nodata=-9999, raster_out=True)

    # Process each unit's raster data
    max_index_values = []
    hazard_scores = []

    # Store area percentages for each index class for reporting
    index_area_stats = {1: [], 2: [], 3: [], 4: [], 5: []}

    for idx, stat in enumerate(stats_values):
        unit_area = adm_hazard.iloc[idx]['unit_area_m2']

        if stat is not None and 'mini_raster_array' in stat:
            # Use memory-efficient approach: count directly on masked array without decompression
            arr = stat['mini_raster_array']

            # Ensure data stays as original dtype (usually uint8 for landslide) to save memory
            data = arr.data

            # Count valid pixels and class occurrences directly on masked array
            if arr.mask is np.ma.nomask:
                # No mask, all pixels are valid
                total_pixels = data.size
            else:
                # Count only non-masked pixels - use int32 instead of int64 for counting
                total_pixels = int(np.sum(~arr.mask, dtype=np.int32))

            if total_pixels > 0:
                # Count pixels for each index class (1-5) directly without creating intermediate arrays
                index_counts = {}
                for index_class in [1, 2, 3, 4, 5]:
                    if arr.mask is np.ma.nomask:
                        # No mask - count all matching pixels, use int32 for memory efficiency
                        pixel_count = int(np.count_nonzero(data == index_class))
                    else:
                        # With mask - count only non-masked matching pixels
                        # Use bitwise operations to avoid creating large intermediate arrays
                        pixel_count = int(np.count_nonzero((data == index_class) & (~arr.mask)))
                    area_pct = (pixel_count / total_pixels) * 100
                    index_counts[index_class] = area_pct
                    index_area_stats[index_class].append(area_pct)

                # Find the highest index class that meets the area threshold
                # Check from highest (5) to lowest (1)
                max_index = 1  # Default: index 1 (not affected)
                for index_class in [5, 4, 3, 2, 1]:
                    if index_counts[index_class] >= area_threshold_pct:
                        max_index = index_class
                        break

                max_index_values.append(max_index)

                # Remap to hazard score
                score = config['remap'].get(max_index, 0)
                hazard_scores.append(score)
            else:
                max_index_values.append(0)
                hazard_scores.append(0)
                for index_class in [1, 2, 3, 4, 5]:
                    index_area_stats[index_class].append(0)
        else:
            max_index_values.append(0)
            hazard_scores.append(0)
            for index_class in [1, 2, 3, 4, 5]:
                index_area_stats[index_class].append(0)

    adm_hazard['LS_Index_max'] = max_index_values
    adm_hazard['Hazard_score'] = hazard_scores

    # Add area percentage columns for each index class
    for index_class in [1, 2, 3, 4, 5]:
        adm_hazard[f'LS_Index{index_class}_area_pct'] = index_area_stats[index_class]

    # Display score distribution
    score_counts = adm_hazard['Hazard_score'].value_counts().sort_index()
    print("\nHazard Score Distribution:")
    for score, count in score_counts.items():
        percentage = (count / len(adm_hazard)) * 100
        print(f"  Score {score}: {count} units ({percentage:.1f}%)")

    # Display index class statistics
    print("\nLandslide Index Class Statistics (max area %):")
    for index_class in [5, 4, 3, 2, 1]:
        areas = [a for a in index_area_stats[index_class] if a > 0]
        if areas:
            print(f"  Index {index_class}: max={max(areas):.1f}%, mean={np.mean(areas):.1f}%")

    return adm_hazard


def process_volcano_hazard(adm_units, hazard_key, value_threshold, area_threshold_pct):
    """
    Process volcano hazard with VEI intersection and remapping.

    Logic:
    - Units outside VEI buffers: score = -1 (not affected)
    - Units with intersection but no VEI meets area threshold: score = -1 (not affected)
    - Units with qualifying VEI: score = remapped value (0-3)

    Args:
        adm_units: GeoDataFrame with administrative boundaries
        hazard_key: Key to HAZARD_CONFIG dictionary (should be 'volcano')
        value_threshold: Not used for volcano
        area_threshold_pct: Minimum area percentage threshold for intersection

    Returns:
        GeoDataFrame with hazard scores (scores: -1, 0-3)
    """
    config = HAZARD_CONFIG[hazard_key]
    print(f"\n{'='*60}")
    print(f"Processing {config['name']} Hazard")
    print(f"{'='*60}")

    adm_hazard = adm_units.copy()

    volcano_path = Path(common.DATA_DIR) / config['folder'] / config['files'][0]

    if not volcano_path.exists():
        print(f"Error: Vector file not found: {volcano_path}")
        return adm_hazard

    print(f"\nLoading volcano exposure data...")
    volcano_gdf = gpd.read_file(volcano_path)

    # Ensure same CRS
    if volcano_gdf.crs != adm_hazard.crs:
        volcano_gdf = volcano_gdf.to_crs(adm_hazard.crs)

    print(f"Processing VEI intersections...")

    vei_values = []
    hazard_scores = []

    for idx, adm_row in adm_hazard.iterrows():
        adm_geom = adm_row.geometry
        adm_area = adm_row['unit_area_m2']

        # Find intersecting volcano polygons
        intersecting = volcano_gdf[volcano_gdf.intersects(adm_geom)]

        if len(intersecting) == 0:
            # No intersection with any volcano buffer = not affected
            vei_values.append(0)
            hazard_scores.append(-1)
            continue

        # Calculate intersection areas and find max VEI that meets area threshold
        max_vei = 0
        for _, volcano_row in intersecting.iterrows():
            intersection = adm_geom.intersection(volcano_row.geometry)

            # Calculate intersection area in projected CRS
            if adm_hazard.crs.is_geographic:
                # Project to UTM for area calculation
                adm_geom_proj = gpd.GeoSeries([intersection], crs=adm_hazard.crs).to_crs(
                    adm_hazard.estimate_utm_crs()
                )
                intersection_area = adm_geom_proj.geometry.area.iloc[0]
            else:
                intersection_area = intersection.area

            # Check if intersection meets area threshold
            area_pct = (intersection_area / adm_area) * 100

            if area_pct >= area_threshold_pct:
                vei = volcano_row[config['field']]
                if vei > max_vei:
                    max_vei = vei

        vei_values.append(max_vei)

        # If max_vei is 0, no VEI met the area threshold = not affected
        if max_vei == 0:
            hazard_scores.append(-1)
        else:
            # Remap VEI to hazard score
            score = 0
            for min_val, max_val, hazard_score in config['remap']['ranges']:
                if min_val <= max_vei < max_val:
                    if hazard_score == -1:  # No hazard
                        score = 0
                    else:
                        score = hazard_score
                    break

            hazard_scores.append(score)

    adm_hazard['VEI_max'] = vei_values
    adm_hazard['Hazard_score'] = hazard_scores

    # Display score distribution
    score_counts = adm_hazard['Hazard_score'].value_counts().sort_index()
    print("\nHazard Score Distribution:")
    for score, count in score_counts.items():
        percentage = (count / len(adm_hazard)) * 100
        print(f"  Score {score}: {count} units ({percentage:.1f}%)")

    return adm_hazard


def process_extreme_heat_hazard(adm_units, hazard_key, value_threshold, area_threshold_pct, rp_thresholds=None):
    """
    Process extreme heat hazard with RP-specific temperature thresholds.

    Logic:
    - RP5 >threshold with area >= area_threshold_pct = High (score 3)
    - RP20 >threshold with area >= area_threshold_pct = Medium (score 2)
    - RP100 >threshold with area >= area_threshold_pct = Low (score 1)
    - All RPs below thresholds = No hazard (score 0)

    Args:
        adm_units: GeoDataFrame with administrative boundaries
        hazard_key: Key to HAZARD_CONFIG dictionary (should be 'extreme_heat')
        value_threshold: Not used - RP-specific thresholds passed separately
        area_threshold_pct: Minimum area percentage threshold
        rp_thresholds: Dict with 'RP5', 'RP20', 'RP100' temperature thresholds (optional, uses config defaults if None)

    Returns:
        GeoDataFrame with hazard scores
    """
    config = HAZARD_CONFIG[hazard_key]

    # Use provided thresholds or fall back to config defaults
    if rp_thresholds is None:
        rp_thresholds = config['rp_thresholds']

    print(f"\n{'='*60}")
    print(f"Processing {config['name']} Hazard")
    print(f"{'='*60}")
    print(f"Using RP-specific thresholds:")
    print(f"  RP5 >{rp_thresholds['RP5']}°C = High")
    print(f"  RP20 >{rp_thresholds['RP20']}°C = Medium")
    print(f"  RP100 >{rp_thresholds['RP100']}°C = Low")
    print(f"Area threshold: {area_threshold_pct}%")

    adm_hazard = adm_units.copy()

    # Process each return period with its specific threshold
    rp_results = {}

    for rp_name, filename in zip(config['rp_names'], config['files']):
        raster_path = Path(common.DATA_DIR) / config['folder'] / filename

        if not raster_path.exists():
            print(f"Warning: Raster not found: {raster_path}")
            continue

        # Get the temperature threshold for this RP
        temp_threshold = rp_thresholds[rp_name]
        print(f"\nProcessing {rp_name} (threshold: {temp_threshold}°C)...")

        # Calculate zonal statistics using parallel processing
        cores = min(len(adm_hazard), mp.cpu_count())

        # Split geometries into chunks for parallel processing
        geom_list = list(adm_hazard.geometry)
        chunk_size = len(geom_list) // cores + (1 if len(geom_list) % cores else 0)
        geom_chunks = [geom_list[i:i + chunk_size] for i in range(0, len(geom_list), chunk_size)]

        with mp.Pool(cores) as p:
            func = partial(zonal_stats_partial, raster=str(raster_path), stats=[],
                         all_touched=True, nodata=-9999, raster_out=True)
            stats_parallel = p.map(func, geom_chunks)

        stats_values = list(it.chain(*stats_parallel))

        # Calculate mean and area percentage for each unit
        means = []
        area_percentages = []

        for idx, stat in enumerate(stats_values):
            if stat is not None and 'mini_raster_array' in stat:
                values = stat['mini_raster_array'].compressed()

                if len(values) > 0:
                    # Calculate mean temperature
                    mean_val = np.mean(values)

                    # Count pixels above temperature threshold
                    affected_pixels = np.sum(values > temp_threshold)
                    total_pixels = len(values)

                    # Calculate area percentage
                    area_pct = (affected_pixels / total_pixels) * 100 if total_pixels > 0 else 0
                else:
                    mean_val = 0
                    area_pct = 0
            else:
                mean_val = 0
                area_pct = 0

            means.append(mean_val)
            area_percentages.append(area_pct)

        # Store results for this RP
        adm_hazard[f'{rp_name}_mean'] = means
        adm_hazard[f'{rp_name}_area_pct'] = area_percentages
        rp_results[rp_name] = {'means': means, 'area_pcts': area_percentages}

        print(f"  Mean temp: {min(means):.1f}°C - {max(means):.1f}°C")
        print(f"  Area >{temp_threshold}°C: {min(area_percentages):.1f}% - {max(area_percentages):.1f}%")

    # Calculate hazard scores based on RP-specific logic
    print("\nCalculating Hazard Scores...")
    hazard_scores = []

    for i in range(len(adm_hazard)):
        score = 0

        # Check RP5 (High): >threshold with area >= area_threshold_pct
        if 'RP5' in rp_results:
            if rp_results['RP5']['area_pcts'][i] > 0 and rp_results['RP5']['area_pcts'][i] >= area_threshold_pct:
                score = 3  # High

        # Check RP20 (Medium): >threshold with area >= area_threshold_pct
        if 'RP20' in rp_results and score < 2:
            if rp_results['RP20']['area_pcts'][i] > 0 and rp_results['RP20']['area_pcts'][i] >= area_threshold_pct:
                score = 2  # Medium

        # Check RP100 (Low): >threshold with area >= area_threshold_pct
        if 'RP100' in rp_results and score < 1:
            if rp_results['RP100']['area_pcts'][i] > 0 and rp_results['RP100']['area_pcts'][i] >= area_threshold_pct:
                score = 1  # Low

        # If no RP exceeded thresholds, score remains 0 (no hazard)

        hazard_scores.append(score)

    adm_hazard['Hazard_score'] = hazard_scores

    # Display score distribution
    score_counts = adm_hazard['Hazard_score'].value_counts().sort_index()
    print("\nHazard Score Distribution:")
    for score, count in score_counts.items():
        percentage = (count / len(adm_hazard)) * 100
        score_label = {0: 'None', 1: 'Low', 2: 'Medium', 3: 'High'}.get(score, str(score))
        print(f"  Score {score} ({score_label}): {count} units ({percentage:.1f}%)")

    return adm_hazard


def process_rp_threshold_hazard(adm_units, hazard_key, value_threshold, area_threshold_pct, rp_thresholds=None):
    """
    Process hazards with RP-specific thresholds (earthquake, cyclone).

    Logic:
    - Each RP has its own intensity threshold
    - For each RP, calculate the area percentage with values > RP-specific threshold
    - If area percentage >= area_threshold_pct, the RP contributes +1 to hazard score
    - Final score = sum of RPs meeting the area threshold (1-4)
    - Score -1 if no RP meets the area threshold (includes both no exposure and exposure below threshold)

    Args:
        adm_units: GeoDataFrame with administrative boundaries
        hazard_key: Key to HAZARD_CONFIG dictionary
        value_threshold: Not used - RP-specific thresholds apply
        area_threshold_pct: Minimum area percentage threshold
        rp_thresholds: Dict with RP-specific thresholds (optional, uses config defaults if None)

    Returns:
        GeoDataFrame with hazard scores and statistics (scores: -1, 1-4)
    """
    config = HAZARD_CONFIG[hazard_key]

    # Use provided thresholds or fall back to config defaults
    if rp_thresholds is None:
        rp_thresholds = config['rp_thresholds']

    print(f"\n{'='*60}")
    print(f"Processing {config['name']} Hazard")
    print(f"{'='*60}")
    print(f"Using RP-specific thresholds:")
    for rp_name in config['rp_names']:
        print(f"  {rp_name} >{rp_thresholds[rp_name]} {config['unit']}")
    print(f"Area threshold: {area_threshold_pct}%")

    adm_hazard = adm_units.copy()

    # Process each return period with its specific threshold
    rp_results = {}

    for rp_name, filename in zip(config['rp_names'], config['files']):
        raster_path = Path(common.DATA_DIR) / config['folder'] / filename

        if not raster_path.exists():
            print(f"Warning: Raster not found: {raster_path}")
            continue

        # Get the threshold for this RP
        rp_threshold = rp_thresholds[rp_name]
        print(f"\nProcessing {rp_name} (threshold: {rp_threshold} {config['unit']})...")

        # Calculate zonal statistics using parallel processing
        cores = min(len(adm_hazard), mp.cpu_count())

        # Split geometries into chunks for parallel processing
        geom_list = list(adm_hazard.geometry)
        chunk_size = len(geom_list) // cores + (1 if len(geom_list) % cores else 0)
        geom_chunks = [geom_list[i:i + chunk_size] for i in range(0, len(geom_list), chunk_size)]

        with mp.Pool(cores) as p:
            func = partial(zonal_stats_partial, raster=str(raster_path), stats=[],
                         all_touched=True, nodata=-9999, raster_out=True)
            stats_parallel = p.map(func, geom_chunks)

        stats_values = list(it.chain(*stats_parallel))

        # Calculate mean and area percentage for each unit
        means = []
        area_percentages = []

        for idx, stat in enumerate(stats_values):
            if stat is not None and 'mini_raster_array' in stat:
                values = stat['mini_raster_array'].compressed()

                if len(values) > 0:
                    # Calculate mean
                    mean_val = np.mean(values)

                    # Count pixels above RP-specific threshold
                    affected_pixels = np.sum(values > rp_threshold)
                    total_pixels = len(values)

                    # Calculate area percentage
                    area_pct = (affected_pixels / total_pixels) * 100 if total_pixels > 0 else 0
                else:
                    mean_val = 0
                    area_pct = 0
            else:
                mean_val = 0
                area_pct = 0

            means.append(mean_val)
            area_percentages.append(area_pct)

        # Store results for this RP
        adm_hazard[f'{rp_name}_mean'] = means
        adm_hazard[f'{rp_name}_area_pct'] = area_percentages
        rp_results[rp_name] = {'means': means, 'area_pcts': area_percentages}

        print(f"  Mean: {min(means):.1f} - {max(means):.1f} {config['unit']}")
        print(f"  Area >{rp_threshold}: {min(area_percentages):.1f}% - {max(area_percentages):.1f}%")

    # Calculate hazard scores - count RPs meeting threshold
    print("\nCalculating Hazard Scores...")
    hazard_scores = []

    for i in range(len(adm_hazard)):
        rp_count = 0

        # Count how many RPs meet the area threshold
        for rp_name in config['rp_names']:
            if rp_name in rp_results:
                area_pct = rp_results[rp_name]['area_pcts'][i]
                if area_pct >= area_threshold_pct:
                    rp_count += 1

        # Convert RP count to score: 0 RPs = -1, 1 RP = 0, 2 RPs = 1, 3 RPs = 2, 4 RPs = 3
        if rp_count == 0:
            score = -1
        else:
            score = rp_count - 1

        hazard_scores.append(score)

    adm_hazard['Hazard_score'] = hazard_scores

    # Display score distribution
    score_counts = adm_hazard['Hazard_score'].value_counts().sort_index()
    print("\nHazard Score Distribution:")
    for score, count in score_counts.items():
        percentage = (count / len(adm_hazard)) * 100
        if score == -1:
            print(f"  Score {score} (Not Affected): {count} units ({percentage:.1f}%)")
        else:
            print(f"  Score {score}: {count} units ({percentage:.1f}%)")

    return adm_hazard


def process_tsunami_hazard(adm_units, hazard_key, value_threshold, area_threshold_pct, rp_thresholds=None):
    """
    Process tsunami hazard with RP-specific thresholds using MAJORITY values.

    Logic different from earthquake/cyclone:
    - Uses MAJORITY (most common) inundation depth per unit (not mean or max)
    - Score -1: No data (not affected - no inundation in any RP)
    - Score 0: Has data but all RPs below threshold
    - Score 1-3: Number of RPs meeting threshold (1 RP = score 1, 2 RPs = score 2, 3 RPs = score 3)

    Args:
        adm_units: GeoDataFrame with administrative boundaries
        hazard_key: Key to HAZARD_CONFIG dictionary (should be 'tsunami')
        value_threshold: Not used - RP-specific thresholds apply
        area_threshold_pct: Minimum area percentage threshold (usually 0 for tsunami)
        rp_thresholds: Dict with RP-specific thresholds (optional, uses config defaults if None)

    Returns:
        GeoDataFrame with hazard scores and statistics (scores: -1, 0, 1, 2, 3)
    """
    config = HAZARD_CONFIG[hazard_key]

    # Use provided thresholds or fall back to config defaults
    if rp_thresholds is None:
        rp_thresholds = config['rp_thresholds']

    print(f"\n{'='*60}")
    print(f"Processing {config['name']} Hazard")
    print(f"{'='*60}")
    print(f"Using RP-specific thresholds (MAJORITY inundation depth):")
    for rp_name in config['rp_names']:
        print(f"  {rp_name} >{rp_thresholds[rp_name]} {config['unit']}")
    print(f"Area threshold: {area_threshold_pct}%")

    adm_hazard = adm_units.copy()

    # Process each return period with its specific threshold
    rp_results = {}

    for rp_name, filename in zip(config['rp_names'], config['files']):
        raster_path = Path(common.DATA_DIR) / config['folder'] / filename

        if not raster_path.exists():
            print(f"Warning: Raster not found: {raster_path}")
            continue

        # Get the threshold for this RP
        rp_threshold = rp_thresholds[rp_name]
        print(f"\nProcessing {rp_name} (threshold: {rp_threshold} {config['unit']})...")

        # Calculate zonal statistics using parallel processing
        cores = min(len(adm_hazard), mp.cpu_count())

        # Split geometries into chunks for parallel processing
        geom_list = list(adm_hazard.geometry)
        chunk_size = len(geom_list) // cores + (1 if len(geom_list) % cores else 0)
        geom_chunks = [geom_list[i:i + chunk_size] for i in range(0, len(geom_list), chunk_size)]

        with mp.Pool(cores) as p:
            func = partial(zonal_stats_partial, raster=str(raster_path), stats=[],
                         all_touched=True, nodata=-9999, raster_out=True)
            stats_parallel = p.map(func, geom_chunks)

        stats_values = list(it.chain(*stats_parallel))

        # Calculate MAX and area percentage for each unit
        max_values = []
        area_percentages = []

        for idx, stat in enumerate(stats_values):
            if stat is not None and 'mini_raster_array' in stat:
                values = stat['mini_raster_array'].compressed()

                if len(values) > 0:
                    # Calculate MAJORITY (most common) inundation depth, ignoring zero and nodata
                    positive_values = values[values > 0]
                    if len(positive_values) > 0:
                        unique_vals, counts = np.unique(positive_values, return_counts=True)
                        majority_val = unique_vals[np.argmax(counts)]
                    else:
                        majority_val = 0

                    # Count pixels above RP-specific threshold
                    affected_pixels = np.sum(values > rp_threshold)
                    total_pixels = len(values)

                    # Calculate area percentage
                    area_pct = (affected_pixels / total_pixels) * 100 if total_pixels > 0 else 0
                else:
                    majority_val = 0
                    area_pct = 0
            else:
                majority_val = 0
                area_pct = 0

            max_values.append(majority_val)
            area_percentages.append(area_pct)

        # Store results for this RP
        adm_hazard[f'{rp_name}_majority'] = max_values
        adm_hazard[f'{rp_name}_area_pct'] = area_percentages
        rp_results[rp_name] = {'majority_values': max_values, 'area_pcts': area_percentages}

        print(f"  Majority: {min(max_values):.1f} - {max(max_values):.1f} {config['unit']}")
        print(f"  Area >{rp_threshold}: {min(area_percentages):.1f}% - {max(area_percentages):.1f}%")

    # Calculate hazard scores - different logic than earthquake/cyclone
    print("\nCalculating Hazard Scores...")
    hazard_scores = []

    for i in range(len(adm_hazard)):
        # Check if unit has ANY tsunami data (any RP has majority > 0)
        has_data = False
        for rp_name in config['rp_names']:
            if rp_name in rp_results:
                if rp_results[rp_name]['majority_values'][i] > 0:
                    has_data = True
                    break

        if not has_data:
            # Score -1: No inundation data at all
            score = -1
        else:
            # Count how many RPs meet the threshold
            rp_count = 0
            for rp_name in config['rp_names']:
                if rp_name in rp_results:
                    majority_val = rp_results[rp_name]['majority_values'][i]
                    rp_threshold = rp_thresholds[rp_name]
                    area_pct = rp_results[rp_name]['area_pcts'][i]
                    # RP meets threshold if majority value exceeds threshold AND area percentage meets minimum
                    if majority_val >= rp_threshold and area_pct >= area_threshold_pct:
                        rp_count += 1

            # Score = number of RPs meeting threshold (0, 1, 2, or 3)
            score = rp_count

        hazard_scores.append(score)

    adm_hazard['Hazard_score'] = hazard_scores

    # Display score distribution
    score_counts = adm_hazard['Hazard_score'].value_counts().sort_index()
    print("\nHazard Score Distribution:")
    for score, count in score_counts.items():
        percentage = (count / len(adm_hazard)) * 100
        if score == -1:
            print(f"  Score {score} (No Data - Not Affected): {count} units ({percentage:.1f}%)")
        elif score == 0:
            print(f"  Score {score} (Below Threshold): {count} units ({percentage:.1f}%)")
        else:
            print(f"  Score {score} ({score} RP{'s' if score > 1 else ''} meet threshold): {count} units ({percentage:.1f}%)")

    return adm_hazard


def process_hazard(adm_units, hazard_key, value_threshold, area_threshold_pct):
    """
    Main processing function that routes to specific hazard processors.

    Args:
        adm_units: GeoDataFrame with administrative boundaries
        hazard_key: Key to HAZARD_CONFIG dictionary
        value_threshold: Minimum value threshold
        area_threshold_pct: Minimum area percentage threshold

    Returns:
        GeoDataFrame with hazard scores and statistics
    """
    config = HAZARD_CONFIG[hazard_key]

    # Check if hazard is work in progress
    if config['type'] == 'wip':
        print(f"\n{config['name']} hazard is work in progress and not yet implemented.")
        return None

    # Route to appropriate processor
    if config['type'] == 'raster_mean':
        return process_raster_mean_hazard(adm_units, hazard_key, value_threshold, area_threshold_pct)
    elif config['type'] == 'raster_remap':
        return process_landslide_hazard(adm_units, hazard_key, value_threshold, area_threshold_pct)
    elif config['type'] == 'vector_intersect':
        return process_volcano_hazard(adm_units, hazard_key, value_threshold, area_threshold_pct)
    elif config['type'] == 'raster_heat':
        return process_extreme_heat_hazard(adm_units, hazard_key, value_threshold, area_threshold_pct)
    elif config['type'] == 'raster_rp_thresholds':
        return process_rp_threshold_hazard(adm_units, hazard_key, value_threshold, area_threshold_pct)
    else:
        print(f"Unknown hazard type: {config['type']}")
        return None


def load_adm2_global(country_filter=None, use_cache=True):
    """
    Load global ADM2 boundaries from WorldBank REST API with caching.

    Args:
        country_filter: Optional list of ISO3 country codes to filter. If None, loads all.
        use_cache: Whether to use cached data if available (default: True)

    Returns:
        GeoDataFrame with ADM2 boundaries
    """
    import requests
    from shapely.geometry import shape
    from input_utils import get_layer_id_for_adm
    import os
    import hashlib

    # Create cache directory
    cache_dir = Path(common.DATA_DIR) / 'ADM'
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Generate cache filename based on filter and service type
    service_suffix = "NEW" if common.USE_NEW_SERVICE else "VIEW"
    if country_filter:
        if isinstance(country_filter, str):
            country_filter = [country_filter]
        # Sort for consistent cache key
        filter_key = '_'.join(sorted(country_filter))
        cache_file = cache_dir / f"ADM2_cached_{filter_key}_{service_suffix}.gpkg"
    else:
        cache_file = cache_dir / f"ADM2_cached_GLOBAL_{service_suffix}.gpkg"

    # Check if cache exists
    if use_cache and cache_file.exists():
        print(f"Loading cached ADM2 boundaries from {cache_file}...")
        try:
            gdf = gpd.read_file(cache_file)
            print(f"Successfully loaded {len(gdf)} cached ADM2 units")
            return gdf
        except Exception as e:
            print(f"Warning: Failed to load cache ({e}), fetching from API...")

    # Get the correct layer ID for ADM2 (dynamically from API)
    layer_id = get_layer_id_for_adm(2)
    query_url = f"{common.rest_api_url}/{layer_id}/query"

    # Build where clause
    if country_filter:
        where_clause = "ISO_A3 IN ('" + "','".join(country_filter) + "')"
    else:
        where_clause = "1=1"  # Get all records

    print(f"Fetching ADM2 boundaries from WorldBank REST API...")
    if country_filter:
        print(f"Filter: {len(country_filter)} countries - {', '.join(country_filter[:5])}{' ...' if len(country_filter) > 5 else ''}")
    else:
        print(f"Filter: Global (all countries)")

    # First, get the count
    count_params = {
        'where': where_clause,
        'returnCountOnly': 'true',
        'f': 'json'
    }

    response = requests.get(query_url, params=count_params)
    if response.status_code != 200:
        raise Exception(f"Error fetching count: {response.status_code}")

    total_count = response.json().get('count', 0)
    print(f"Total ADM2 units to fetch: {total_count}")

    if total_count == 0:
        raise Exception("No ADM2 units found for the specified filter.")

    # Fetch in batches due to API limitations
    all_features = []
    batch_size = 2000  # API typically limits to 1000-2000 records per request
    offset = 0

    from tqdm import tqdm
    with tqdm(total=total_count, desc="Downloading ADM2 boundaries") as pbar:
        while offset < total_count:
            params = {
                'where': where_clause,
                'outFields': '*',
                'resultOffset': offset,
                'resultRecordCount': batch_size,
                'f': 'geojson'
            }

            response = requests.get(query_url, params=params)

            if response.status_code != 200:
                print(f"Warning: Error fetching batch at offset {offset}: {response.status_code}")
                break

            data = response.json()
            features = data.get('features', [])

            if not features:
                break

            all_features.extend(features)
            offset += len(features)
            pbar.update(len(features))

            # Break if we got fewer features than requested (end of data)
            if len(features) < batch_size:
                break

    print(f"Successfully fetched {len(all_features)} ADM2 units")

    # Convert to GeoDataFrame
    geometry = [shape(feature['geometry']) for feature in all_features]
    properties = [feature['properties'] for feature in all_features]
    gdf = gpd.GeoDataFrame(properties, geometry=geometry, crs="EPSG:4326")

    # Standardize column names using field mapping from common.py
    adm2_code_field = common.adm_field_mapping[2]['code']
    adm2_name_field = common.adm_field_mapping[2]['name']

    if adm2_code_field in gdf.columns and adm2_name_field in gdf.columns:
        gdf['ADM_CODE'] = gdf[adm2_code_field]
        gdf['ADM_NAME'] = gdf[adm2_name_field]

    # Save to cache
    print(f"Saving to cache: {cache_file}...")
    gdf.to_file(cache_file, driver="GPKG")
    print(f"Cache saved successfully")

    return gdf


def load_boundaries(unit_level, custom_boundaries_file_path=None, country_filter=None):
    """
    Load administrative boundaries based on unit level selection.

    Args:
        unit_level: 'ADM2' or 'Urban'
        custom_boundaries_file_path: Path to custom boundaries file (for Urban)
        country_filter: Optional list of ISO3 codes for ADM2 filtering

    Returns:
        GeoDataFrame with boundaries
    """
    if unit_level == 'ADM2':
        return load_adm2_global(country_filter=country_filter)

    elif unit_level == 'Urban':
        if not custom_boundaries_file_path:
            custom_boundaries_file_path = 'data/ADM/TH_urban.gpkg'

        print(f"Loading urban boundaries from {custom_boundaries_file_path}...")
        adm_units = gpd.read_file(custom_boundaries_file_path)

        return adm_units
    else:
        raise ValueError(f"Unknown unit level: {unit_level}")


def save_results(result_gdf, hazard_key, unit_level, value_threshold, area_threshold_pct, country_codes=None, rp_thresholds=None):
    """
    Save results to GeoPackage and Excel files.

    Args:
        result_gdf: GeoDataFrame with results
        hazard_key: Hazard type key
        unit_level: Unit level (ADM2 or Urban)
        value_threshold: Value threshold used
        area_threshold_pct: Area threshold percentage used
        country_codes: List of country ISO codes (optional)
        rp_thresholds: Dict of RP-specific thresholds for extreme heat (optional)

    Returns:
        tuple: (gpkg_path, excel_path)
    """
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    config = HAZARD_CONFIG[hazard_key]

    # Determine country prefix
    if country_codes and len(country_codes) > 0:
        # Use country codes joined with underscore if multiple countries selected
        country_prefix = "_".join(country_codes)
    else:
        country_prefix = "GLB"

    # Format threshold part of filename
    if hazard_key == 'extreme_heat' and rp_thresholds:
        # For extreme heat, use RP-specific thresholds: vt{rp100}-{rp20}-{rp5}
        threshold_str = f"vt{int(rp_thresholds['RP100'])}-{int(rp_thresholds['RP20'])}-{int(rp_thresholds['RP5'])}"
    else:
        # For other hazards, use standard value threshold
        threshold_str = f"vt{value_threshold}"

    base_name = f"{country_prefix}_{config['name']}_hazard_{unit_level}_{threshold_str}_at{area_threshold_pct}_{timestamp}"

    # Create TH subfolder if it doesn't exist
    output_dir = Path(common.OUTPUT_DIR) / "TH"
    output_dir.mkdir(parents=True, exist_ok=True)

    gpkg_path = output_dir / f"{base_name}.gpkg"
    excel_path = output_dir / f"{base_name}.xlsx"

    # Save to GeoPackage
    print(f"\nSaving results to {gpkg_path}...")
    result_gdf.to_file(gpkg_path, driver="GPKG")

    # Save to Excel
    print(f"Saving results to {excel_path}...")
    df = pd.DataFrame(result_gdf.drop(columns='geometry'))
    df.to_excel(excel_path, index=False)

    return str(gpkg_path), str(excel_path)


def plot_results(gdf, hazard_name):
    """
    Create a folium layer for the results.

    Args:
        gdf: GeoDataFrame with results
        hazard_name: Name of the hazard

    Returns:
        tuple: (layer, legend_html)
    """
    # Define color scheme for hazard scores (index: -1, 0, 1, 2, 3, 4)
    color_map = {
        -1: '#a8a8a8',  # Not affected - Gray
        0: '#f1ff6f',   # No significant hazard - Light Yellow
        1: '#f8da2e',   # Low hazard - Yellow
        2: '#f6912b',   # Medium hazard - Orange
        3: '#d52d24',   # High hazard - Red
        4: '#8b0000'    # Very High hazard - Dark Red (for 4 RP hazards)
    }

    # Check if dataset contains score -1 (not affected)
    has_not_affected = (gdf['Hazard_score'] == -1).any()

    # Create custom vertical legend HTML
    legend_items = []

    # Check for highest score in data
    max_score = int(gdf['Hazard_score'].max())
    has_score_4 = max_score >= 4

    # Build legend from highest to lowest score
    # Add score 4 if present (earthquake/cyclone with 4 RPs)
    if has_score_4:
        legend_items.append(f'''
        <div style="display: flex; align-items: center; margin-bottom: 4px;">
            <div style="width: 25px; height: 18px; background-color: {color_map[4]}; border: 1px solid black; margin-right: 8px;"></div>
            <span>Score 4 (Very High)</span>
        </div>''')

    # Add score 3
    if has_not_affected or has_score_4:
        legend_items.append(f'''
        <div style="display: flex; align-items: center; margin-bottom: 4px;">
            <div style="width: 25px; height: 18px; background-color: {color_map[3]}; border: 1px solid black; margin-right: 8px;"></div>
            <span>Score 3 (High)</span>
        </div>''')
    else:
        legend_items.append(f'''
        <div style="display: flex; align-items: center; margin-bottom: 4px;">
            <div style="width: 25px; height: 18px; background-color: {color_map[3]}; border: 1px solid black; margin-right: 8px;"></div>
            <span>Score 3</span>
        </div>''')

    legend_items.append(f'''
        <div style="display: flex; align-items: center; margin-bottom: 4px;">
            <div style="width: 25px; height: 18px; background-color: {color_map[2]}; border: 1px solid black; margin-right: 8px;"></div>
            <span>Score 2</span>
        </div>''')

    legend_items.append(f'''
        <div style="display: flex; align-items: center; margin-bottom: 4px;">
            <div style="width: 25px; height: 18px; background-color: {color_map[1]}; border: 1px solid black; margin-right: 8px;"></div>
            <span>Score 1</span>
        </div>''')

    legend_items.append(f'''
        <div style="display: flex; align-items: center; margin-bottom: 4px;">
            <div style="width: 25px; height: 18px; background-color: {color_map[0]}; border: 1px solid black; margin-right: 8px;"></div>
            <span>Score 0</span>
        </div>''')

    # Add "Not Affected" only if present in data
    if has_not_affected:
        legend_items.append(f'''
        <div style="display: flex; align-items: center;">
            <div style="width: 25px; height: 18px; background-color: {color_map[-1]}; border: 1px solid black; margin-right: 8px;"></div>
            <span>Not Affected</span>
        </div>''')

    legend_html = f'''
    <div style="position: fixed;
                top: 10px;
                left: 10px;
                width: 170px;
                background-color: white;
                border:2px solid grey;
                z-index:9999;
                font-size:12px;
                padding: 8px;
                border-radius: 5px;
                box-shadow: 0 0 15px rgba(0,0,0,0.2);
                ">
        <p style="margin: 0 0 8px 0; font-weight: bold; font-size: 13px;">{hazard_name}<br>Hazard Score</p>
        {''.join(legend_items)}
    </div>
    '''

    # Create GeoJson layer
    layer = folium.FeatureGroup(name=f'{hazard_name} - Scores', show=True)

    for idx, row in gdf.iterrows():
        score = int(row['Hazard_score'])
        color = color_map.get(score, color_map[0])  # Default to score 0 color if not found

        # Get unit name for tooltip if available
        unit_name = row.get('ADM_NAME', row.get('name', f'Unit {idx}'))

        # Format score label for tooltip
        if score == -1:
            score_label = "Not Affected"
        else:
            score_label = f"Score {score}"

        folium.GeoJson(
            row.geometry,
            style_function=lambda x, color=color: {
                'fillColor': color,
                'color': 'black',
                'weight': 1,
                'fillOpacity': 0.7,
                'className': 'admin-layer'
            },
            tooltip=folium.Tooltip(f'{unit_name}<br>Hazard {score_label}')
        ).add_to(layer)

    return layer, legend_html


def create_summary_chart(result_gdf, hazard_name):
    """
    Create a summary bar chart of hazard score distribution.

    Args:
        result_gdf: GeoDataFrame with results
        hazard_name: Name of the hazard

    Returns:
        matplotlib.figure.Figure
    """
    fig, ax = plt.subplots(figsize=(8, 6))

    # Define color scheme matching map visualization
    color_map = {
        -1: '#a8a8a8',  # Not affected - Gray
        0: '#f1ff6f',   # No significant hazard - Light Yellow
        1: '#f8da2e',   # Low hazard - Yellow
        2: '#f6912b',   # Medium hazard - Orange
        3: '#d52d24',   # High hazard - Red
        4: '#8b0000'    # Very High hazard - Dark Red
    }

    score_counts = result_gdf['Hazard_score'].value_counts()
    total = len(result_gdf)

    # Check for special scores in data
    has_not_affected = -1 in score_counts.index
    max_score = int(result_gdf['Hazard_score'].max())

    # Build score list dynamically based on data
    scores = []
    if has_not_affected:
        scores.append(-1)
    for s in range(0, min(max_score + 1, 5)):  # Up to 4
        scores.append(s)

    data = []
    labels = []
    bar_colors = []

    for score in scores:
        count = score_counts.get(score, 0)
        pct = (count / total) * 100
        data.append(pct)

        if score == -1:
            labels.append('Not Affected')
        else:
            labels.append(f'Score {score}')

        bar_colors.append(color_map[score])

    ax.bar(labels, data, color=bar_colors, alpha=0.9, edgecolor='black', linewidth=0.5)
    ax.set_ylabel('Percentage of Units (%)', fontsize=12)
    ax.set_xlabel('Hazard Score', fontsize=12)
    ax.set_title(f'{hazard_name} Hazard Score Distribution', fontsize=14, fontweight='bold')
    ax.set_ylim(0, 100)
    ax.grid(axis='y', alpha=0.3)

    # Add value labels on bars
    for i, v in enumerate(data):
        if v > 0:  # Only show label if percentage > 0
            ax.text(i, v + 1, f'{v:.1f}%', ha='center', va='bottom', fontsize=10)

    plt.tight_layout()

    return fig


def initialize_tool():
    """
    Initialize and display the multi-hazard threshold analysis GUI.
    """
    # Import widget libraries
    import ipywidgets as widgets
    import notebook_utils

    # Load country data
    df = pd.read_csv('countries.csv')

    # Create a mapping that handles territories properly
    # For entries where NAM_0 appears multiple times, show as "Country (ISO3)"
    name_counts = df['NAM_0'].value_counts()

    country_dict = {}
    for _, row in df.iterrows():
        name = row['NAM_0']
        iso3 = row['ISO_A3']

        # If this country name appears multiple times, append ISO code for clarity
        if name_counts[name] > 1:
            display_name = f"{name} ({iso3})"
        else:
            display_name = name

        country_dict[display_name] = iso3

    # Unit level selector
    unit_level_selector = widgets.Dropdown(
        options=['ADM2', 'Urban'],
        value='ADM2',
        description='Unit Level:',
        disabled=False,
        layout=widgets.Layout(width='250px'),
        style={'description_width': '100px'}
    )

    # Country filter for ADM2
    country_filter_selector = widgets.SelectMultiple(
        options=sorted(country_dict.keys()),
        value=(),  # Use empty tuple instead of list to allow deselection
        rows=15,   # Increased height
        description='',  # No description to save space
        disabled=False,  # Enabled by default since ADM2 is default
        layout=widgets.Layout(width='100%', height='350px'),  # Use full width, taller
        style={'description_width': '0px'}
    )

    # Clear selection button
    clear_countries_button = widgets.Button(
        description='Clear Selection',
        disabled=False,  # Enabled by default since ADM2 is default
        button_style='warning',
        layout=widgets.Layout(width='150px')
    )

    def clear_country_selection(b):
        country_filter_selector.value = ()
        update_preview_map()

    clear_countries_button.on_click(clear_country_selection)

    country_filter_label = widgets.HTML(
        value='<i>Ctrl+Click to select/deselect.<br>Empty = global analysis.</i>',
        layout=widgets.Layout(width='100%')
    )

    # Cache refresh checkbox
    refresh_cache_checkbox = widgets.Checkbox(
        value=False,
        description='Refresh cache',
        disabled=False,  # Enabled by default since ADM2 is default
        indent=False,
        layout=widgets.Layout(width='150px')
    )

    # Hazard selector
    hazard_selector = widgets.Dropdown(
        options=[
            ('Earthquake', 'earthquake'),
            ('Landslide', 'landslide'),
            ('Tsunami', 'tsunami'),
            ('Volcano', 'volcano'),
            ('Cyclone', 'cyclone'),
            ('Extreme Heat', 'extreme_heat'),
            ('Wildfire', 'wildfire'),
            ('Water Scarcity', 'water_scarcity')
        ],
        value='earthquake',
        description='Hazard:',
        disabled=False,
        layout=widgets.Layout(width='250px'),
        style={'description_width': '100px'}
    )

    # Value threshold label
    value_threshold_label = widgets.Label(
        value='Value Threshold:',
        layout=widgets.Layout(width='110px')
    )

    # Value threshold input (no description, for HBox layout)
    value_threshold_input = widgets.FloatText(
        value=80,
        description='',
        disabled=False,
        layout=widgets.Layout(width='70px'),
        style={'description_width': '0px'}
    )

    # Threshold unit label
    threshold_unit_label = widgets.Label(
        value='(PGA-g)',
        layout=widgets.Layout(width='auto')
    )

    # Container for value threshold row (hidden by default since earthquake is default hazard)
    value_threshold_box = widgets.HBox(
        [value_threshold_label, value_threshold_input, threshold_unit_label],
        layout=widgets.Layout(display='none')
    )

    # Area threshold slider and input (synchronized)
    # Initialize with earthquake's default (since earthquake is the default hazard)
    initial_area_threshold = HAZARD_CONFIG['earthquake'].get('default_area_threshold', 10.0)

    area_threshold_slider = widgets.FloatSlider(
        value=initial_area_threshold,
        min=0.0,
        max=100.0,
        step=0.5,
        description='',
        disabled=False,
        continuous_update=False,
        orientation='horizontal',
        readout=False,
        layout=widgets.Layout(width='210px', margin='0px 5px 0px 0px')
    )

    area_threshold_text = widgets.FloatText(
        value=initial_area_threshold,
        min=0.0,
        max=100.0,
        step=0.5,
        disabled=False,
        layout=widgets.Layout(width='60px')
    )

    area_threshold_label = widgets.Label('Area (%):', layout=widgets.Layout(width='70px'))

    # Link slider and text input bidirectionally
    def on_slider_change(change):
        area_threshold_text.value = change['new']

    def on_text_change(change):
        new_val = change['new']
        # Cap at 100 if user enters > 100
        if new_val > 100:
            area_threshold_text.value = 100.0
            new_val = 100.0
        # Cap at 0 if user enters < 0
        elif new_val < 0:
            area_threshold_text.value = 0.0
            new_val = 0.0

        area_threshold_slider.value = new_val

    area_threshold_slider.observe(on_slider_change, names='value')
    area_threshold_text.observe(on_text_change, names='value')

    area_threshold_input = widgets.HBox([
        area_threshold_label,
        area_threshold_slider,
        area_threshold_text
    ], layout=widgets.Layout(align_items='center'))

    # RP-specific thresholds for earthquake (initially displayed as default)
    eq_rp250_label = widgets.Label(value='RP250:', layout=widgets.Layout(width='80px'))
    eq_rp250_input = widgets.FloatText(value=120, description='', layout=widgets.Layout(width='50px'), style={'description_width': '0px'})
    eq_rp250_unit = widgets.Label(value='PGA-g', layout=widgets.Layout(width='50px'))

    eq_rp475_label = widgets.Label(value='RP475:', layout=widgets.Layout(width='80px'))
    eq_rp475_input = widgets.FloatText(value=100, description='', layout=widgets.Layout(width='50px'), style={'description_width': '0px'})
    eq_rp475_unit = widgets.Label(value='PGA-g', layout=widgets.Layout(width='50px'))

    eq_rp975_label = widgets.Label(value='RP975:', layout=widgets.Layout(width='80px'))
    eq_rp975_input = widgets.FloatText(value=80, description='', layout=widgets.Layout(width='50px'), style={'description_width': '0px'})
    eq_rp975_unit = widgets.Label(value='PGA-g', layout=widgets.Layout(width='50px'))

    eq_rp2475_label = widgets.Label(value='RP2475:', layout=widgets.Layout(width='80px'))
    eq_rp2475_input = widgets.FloatText(value=60, description='', layout=widgets.Layout(width='50px'), style={'description_width': '0px'})
    eq_rp2475_unit = widgets.Label(value='PGA-g', layout=widgets.Layout(width='50px'))

    eq_thresholds_box = widgets.VBox([
        widgets.HBox([eq_rp250_label, eq_rp250_input, eq_rp250_unit]),
        widgets.HBox([eq_rp475_label, eq_rp475_input, eq_rp475_unit]),
        widgets.HBox([eq_rp975_label, eq_rp975_input, eq_rp975_unit]),
        widgets.HBox([eq_rp2475_label, eq_rp2475_input, eq_rp2475_unit])
    ], layout=widgets.Layout(display='block'))  # Shown by default (earthquake is default)

    # RP-specific thresholds for cyclone (initially hidden)
    cy_rp50_label = widgets.Label(value='RP50:', layout=widgets.Layout(width='80px'))
    cy_rp50_input = widgets.FloatText(value=36, description='', layout=widgets.Layout(width='50px'), style={'description_width': '0px'})
    cy_rp50_unit = widgets.Label(value='m/s', layout=widgets.Layout(width='50px'))

    cy_rp100_label = widgets.Label(value='RP100:', layout=widgets.Layout(width='80px'))
    cy_rp100_input = widgets.FloatText(value=36, description='', layout=widgets.Layout(width='50px'), style={'description_width': '0px'})
    cy_rp100_unit = widgets.Label(value='m/s', layout=widgets.Layout(width='50px'))

    cy_rp1000_label = widgets.Label(value='RP1000:', layout=widgets.Layout(width='80px'))
    cy_rp1000_input = widgets.FloatText(value=30, description='', layout=widgets.Layout(width='50px'), style={'description_width': '0px'})
    cy_rp1000_unit = widgets.Label(value='m/s', layout=widgets.Layout(width='50px'))

    cy_rp10000_label = widgets.Label(value='RP10000:', layout=widgets.Layout(width='80px'))
    cy_rp10000_input = widgets.FloatText(value=26, description='', layout=widgets.Layout(width='50px'), style={'description_width': '0px'})
    cy_rp10000_unit = widgets.Label(value='m/s', layout=widgets.Layout(width='50px'))

    cy_thresholds_box = widgets.VBox([
        widgets.HBox([cy_rp50_label, cy_rp50_input, cy_rp50_unit]),
        widgets.HBox([cy_rp100_label, cy_rp100_input, cy_rp100_unit]),
        widgets.HBox([cy_rp1000_label, cy_rp1000_input, cy_rp1000_unit]),
        widgets.HBox([cy_rp10000_label, cy_rp10000_input, cy_rp10000_unit])
    ], layout=widgets.Layout(display='none'))  # Hidden by default

    # RP-specific thresholds for tsunami (initially hidden)
    ts_rp100_label = widgets.Label(value='RP100:', layout=widgets.Layout(width='80px'))
    ts_rp100_input = widgets.FloatText(value=2.0, description='', layout=widgets.Layout(width='50px'), style={'description_width': '0px'})
    ts_rp100_unit = widgets.Label(value='m', layout=widgets.Layout(width='50px'))

    ts_rp500_label = widgets.Label(value='RP500:', layout=widgets.Layout(width='80px'))
    ts_rp500_input = widgets.FloatText(value=1.0, description='', layout=widgets.Layout(width='50px'), style={'description_width': '0px'})
    ts_rp500_unit = widgets.Label(value='m', layout=widgets.Layout(width='50px'))

    ts_rp2500_label = widgets.Label(value='RP2500:', layout=widgets.Layout(width='80px'))
    ts_rp2500_input = widgets.FloatText(value=0.5, description='', layout=widgets.Layout(width='50px'), style={'description_width': '0px'})
    ts_rp2500_unit = widgets.Label(value='m', layout=widgets.Layout(width='50px'))

    ts_thresholds_box = widgets.VBox([
        widgets.HBox([ts_rp100_label, ts_rp100_input, ts_rp100_unit]),
        widgets.HBox([ts_rp500_label, ts_rp500_input, ts_rp500_unit]),
        widgets.HBox([ts_rp2500_label, ts_rp2500_input, ts_rp2500_unit])
    ], layout=widgets.Layout(display='none'))  # Hidden by default

    # RP-specific thresholds for extreme heat (initially hidden)
    rp5_threshold_label = widgets.Label(value='RP5 (High):', layout=widgets.Layout(width='80px'))
    rp5_threshold_input = widgets.FloatText(
        value=32,
        description='',
        layout=widgets.Layout(width='50px'),
        style={'description_width': '0px'}
    )
    rp5_unit_label = widgets.Label(value='°C', layout=widgets.Layout(width='30px'))

    rp20_threshold_label = widgets.Label(value='RP20 (Med):', layout=widgets.Layout(width='80px'))
    rp20_threshold_input = widgets.FloatText(
        value=28,
        description='',
        layout=widgets.Layout(width='50px'),
        style={'description_width': '0px'}
    )
    rp20_unit_label = widgets.Label(value='°C', layout=widgets.Layout(width='30px'))

    rp100_threshold_label = widgets.Label(value='RP100 (Low):', layout=widgets.Layout(width='80px'))
    rp100_threshold_input = widgets.FloatText(
        value=25,
        description='',
        layout=widgets.Layout(width='50px'),
        style={'description_width': '0px'}
    )
    rp100_unit_label = widgets.Label(value='°C', layout=widgets.Layout(width='30px'))

    # Container for RP thresholds (initially hidden)
    rp_thresholds_box = widgets.VBox([
        widgets.HBox([rp5_threshold_label, rp5_threshold_input, rp5_unit_label]),
        widgets.HBox([rp20_threshold_label, rp20_threshold_input, rp20_unit_label]),
        widgets.HBox([rp100_threshold_label, rp100_threshold_input, rp100_unit_label])
    ], layout=widgets.Layout(display='none'))  # Hidden by default

    # Output widgets
    output = notebook_utils.output_widget
    chart_output = notebook_utils.chart_output
    map_widget = notebook_utils.map_widget

    # Update threshold based on hazard selection
    def on_hazard_change(change):
        hazard_key = change['new']
        config = HAZARD_CONFIG[hazard_key]
        value_threshold_input.value = config['default_threshold']
        threshold_unit_label.value = f"({config['unit']})"

        # Update area threshold to hazard-specific default
        if 'default_area_threshold' in config:
            area_threshold_slider.value = config['default_area_threshold']
            area_threshold_text.value = config['default_area_threshold']

        # Hide all threshold boxes first
        eq_thresholds_box.layout.display = 'none'
        cy_thresholds_box.layout.display = 'none'
        ts_thresholds_box.layout.display = 'none'
        rp_thresholds_box.layout.display = 'none'
        value_threshold_box.layout.display = 'flex'
        intensity_threshold_label.layout.display = 'block'

        # Show appropriate thresholds based on hazard type
        if hazard_key == 'earthquake':
            intensity_threshold_label.value = '<b>RP-Specific Thresholds:</b>'
            eq_thresholds_box.layout.display = 'block'
            value_threshold_box.layout.display = 'none'
        elif hazard_key == 'cyclone':
            intensity_threshold_label.value = '<b>RP-Specific Thresholds:</b>'
            cy_thresholds_box.layout.display = 'block'
            value_threshold_box.layout.display = 'none'
        elif hazard_key == 'tsunami':
            intensity_threshold_label.value = '<b>RP-Specific Thresholds:</b>'
            ts_thresholds_box.layout.display = 'block'
            value_threshold_box.layout.display = 'none'
        elif hazard_key == 'extreme_heat':
            intensity_threshold_label.value = '<b>RP-Specific Thresholds:</b>'
            rp_thresholds_box.layout.display = 'block'
            value_threshold_box.layout.display = 'none'
        elif hazard_key in ['landslide', 'volcano']:
            # Hide intensity threshold section for area-based only hazards
            intensity_threshold_label.layout.display = 'none'
            value_threshold_box.layout.display = 'none'
        else:
            # Standard value threshold for wildfire
            intensity_threshold_label.value = '<b>Value Threshold:</b>'
            value_threshold_input.disabled = False
            value_threshold_input.layout.opacity = '1.0'
            threshold_unit_label.value = f"({config['unit']})"

        # Check if hazard is WIP
        if config['type'] == 'wip':
            output.clear_output()
            with output:
                print(f"Note: {config['name']} hazard is work in progress and not yet implemented.")

    hazard_selector.observe(on_hazard_change, names='value')

    # Update country filter availability based on unit level
    def on_unit_level_change(change):
        unit_level = change['new']
        if unit_level == 'ADM2':
            country_filter_selector.disabled = False
            clear_countries_button.disabled = False
            refresh_cache_checkbox.disabled = False
        else:
            country_filter_selector.disabled = True
            clear_countries_button.disabled = True
            refresh_cache_checkbox.disabled = True
            country_filter_selector.value = ()
        update_preview_map()

    unit_level_selector.observe(on_unit_level_change, names='value')

    # Boundary preview map
    def plot_geospatial_boundaries(gdf, crs: str = "EPSG:4326"):
        gdf = gdf.set_crs(crs) if gdf.crs is None else gdf
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

    def update_preview_map(*args):
        unit_level = unit_level_selector.value
        try:
            if unit_level == 'Urban':
                gdf = gpd.read_file('data/ADM/TH_urban.gpkg')
                plot_geospatial_boundaries(gdf)
            elif unit_level == 'ADM2':
                # Don't load for preview - too large
                with output:
                    output.clear_output()
                    if country_filter_selector.value:
                        print(f"ADM2 boundaries will be loaded for: {', '.join(country_filter_selector.value)}")
                    else:
                        print("ADM2 boundaries will be loaded globally (all countries)")
                    print("Note: Boundaries will be fetched when analysis is run")
        except Exception as e:
            with output:
                print(f"Error loading boundaries: {str(e)}")

    country_filter_selector.observe(lambda x: update_preview_map(), 'value')

    # Run button
    run_button = notebook_utils.run_button

    # Run analysis function
    def run_analysis_script(b):
        run_button.disabled = True
        run_button.description = "Analysis Running..."
        try:
            with output:
                output.clear_output(wait=True)

                unit_level = unit_level_selector.value
                hazard_key = hazard_selector.value
                value_threshold = value_threshold_input.value
                area_threshold_pct = area_threshold_slider.value  # Can use slider or text, they're synced

                config = HAZARD_CONFIG[hazard_key]

                # Check if WIP
                if config['type'] == 'wip':
                    print(f"Error: {config['name']} hazard is not yet implemented.")
                    return

                start_time = time.perf_counter()

                print(f"Starting {config['name']} hazard analysis...")
                print(f"Unit Level: {unit_level}")
                print(f"Value Threshold: {value_threshold} {config['unit']}")
                print(f"Area Threshold: {area_threshold_pct}%")

                # Load boundaries
                if unit_level == 'Urban':
                    adm_units = gpd.read_file('data/ADM/TH_urban.gpkg')
                elif unit_level == 'ADM2':
                    # Get country filter and cache settings
                    countries = list(country_filter_selector.value)
                    country_codes = [country_dict[c] for c in countries] if countries else None
                    use_cache = not refresh_cache_checkbox.value  # Invert: checked = refresh = don't use cache

                    adm_units = load_adm2_global(country_filter=country_codes, use_cache=use_cache)
                else:
                    print("Error: Unknown unit level.")
                    return

                print(f"Loaded {len(adm_units)} administrative units")

                # Fix invalid geometries
                print("Validating geometries...")
                invalid_count = (~adm_units.geometry.is_valid).sum()
                if invalid_count > 0:
                    print(f"  Found {invalid_count} invalid geometries, fixing...")
                    adm_units['geometry'] = adm_units.geometry.buffer(0)

                # Calculate unit areas in projected CRS
                print("Calculating unit areas...")
                if adm_units.crs is None:
                    adm_units = adm_units.set_crs("EPSG:4326")

                import warnings
                with warnings.catch_warnings():
                    warnings.filterwarnings('ignore', message='invalid value encountered in area')
                    if adm_units.crs.is_geographic:
                        adm_units_proj = adm_units.to_crs(adm_units.estimate_utm_crs())
                        adm_units['unit_area_m2'] = adm_units_proj.geometry.area
                    else:
                        adm_units['unit_area_m2'] = adm_units.geometry.area

                # Process hazard (with special handling for RP-specific thresholds)
                rp_thresholds = None
                if hazard_key == 'earthquake':
                    # Get RP-specific thresholds from UI
                    rp_thresholds = {
                        'RP250': eq_rp250_input.value,
                        'RP475': eq_rp475_input.value,
                        'RP975': eq_rp975_input.value,
                        'RP2475': eq_rp2475_input.value
                    }
                    result_gdf = process_rp_threshold_hazard(
                        adm_units, hazard_key, value_threshold, area_threshold_pct, rp_thresholds
                    )
                elif hazard_key == 'cyclone':
                    # Get RP-specific thresholds from UI
                    rp_thresholds = {
                        'RP50': cy_rp50_input.value,
                        'RP100': cy_rp100_input.value,
                        'RP1000': cy_rp1000_input.value,
                        'RP10000': cy_rp10000_input.value
                    }
                    result_gdf = process_rp_threshold_hazard(
                        adm_units, hazard_key, value_threshold, area_threshold_pct, rp_thresholds
                    )
                elif hazard_key == 'tsunami':
                    # Get RP-specific thresholds from UI
                    rp_thresholds = {
                        'RP100': ts_rp100_input.value,
                        'RP500': ts_rp500_input.value,
                        'RP2500': ts_rp2500_input.value
                    }
                    result_gdf = process_tsunami_hazard(
                        adm_units, hazard_key, value_threshold, area_threshold_pct, rp_thresholds
                    )
                elif hazard_key == 'extreme_heat':
                    # Get RP-specific thresholds from UI
                    rp_thresholds = {
                        'RP5': rp5_threshold_input.value,
                        'RP20': rp20_threshold_input.value,
                        'RP100': rp100_threshold_input.value
                    }
                    result_gdf = process_extreme_heat_hazard(
                        adm_units, hazard_key, value_threshold, area_threshold_pct, rp_thresholds
                    )
                else:
                    result_gdf = process_hazard(adm_units, hazard_key, value_threshold, area_threshold_pct)

                if result_gdf is None:
                    print("Analysis failed or hazard not implemented.")
                    return

                # Save results
                # Get country codes for filename
                countries = list(country_filter_selector.value)
                save_country_codes = [country_dict[c] for c in countries] if countries else None

                gpkg_path, excel_path = save_results(
                    result_gdf, hazard_key, unit_level, value_threshold, area_threshold_pct, save_country_codes, rp_thresholds
                )

                print(f"\nAnalysis completed in {time.perf_counter() - start_time:.2f} seconds")
                print(f"Results saved to GeoPackage: {gpkg_path}")
                print(f"Results saved to Excel: {excel_path}")

                # Plot results on map
                print("\nGenerating preview map...")
                m = folium.Map(
                    location=[0, 0],
                    zoom_start=5,
                    tiles='OpenStreetMap',
                    attr='OpenStreetMap'
                )

                # Add blank tile layer option
                folium.TileLayer(
                    tiles='',
                    attr='No basemap',
                    name='No Basemap',
                    overlay=False,
                    control=True
                ).add_to(m)

                # Get bounds
                bounds = result_gdf.total_bounds
                center_lat = (bounds[1] + bounds[3]) / 2
                center_lon = (bounds[0] + bounds[2]) / 2
                m.location = [center_lat, center_lon]
                m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])

                # Add results layer
                layer, legend_html = plot_results(result_gdf, config['name'])
                layer.add_to(m)

                # Add legend
                m.get_root().html.add_child(folium.Element(legend_html))

                # Add controls
                folium.LayerControl(position='topright', collapsed=False).add_to(m)
                MiniMap(toggle_display=True, position='bottomright').add_to(m)
                Fullscreen(position='bottomleft').add_to(m)

                map_widget.value = m._repr_html_()

                # Create summary chart
                with chart_output:
                    clear_output(wait=True)
                    chart = create_summary_chart(result_gdf, config['name'])
                    display(chart)

                    # Export chart if checkbox is enabled
                    if notebook_utils.export_charts_chk.value:
                        chart_path = gpkg_path.replace('.gpkg', '_chart.png')
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
    boundary_tab = widgets.VBox([
        widgets.HTML(value='<b>Unit Level</b>'),
        unit_level_selector,
        widgets.HTML(value='<br><i>ADM2: Global administrative boundaries from WorldBank API</i>'),
        widgets.HTML(value='<i>Urban: Local boundary file (data/ADM/TH_urban.gpkg)</i>'),
        widgets.HTML(value='<br><b>Country Filter (ADM2 only)</b>'),
        country_filter_selector,
        widgets.HBox([clear_countries_button, refresh_cache_checkbox]),
        country_filter_label
    ], layout=widgets.Layout(padding='10px'))

    # Label for intensity thresholds (changes based on hazard)
    # Default to earthquake's label since earthquake is the default hazard
    intensity_threshold_label = widgets.HTML(value='<b>RP-Specific Thresholds:</b>')

    hazard_tab = widgets.VBox([
        widgets.HTML(value='<b>Hazard Type</b>'),
        hazard_selector,
        widgets.HTML(value='<br><b>Thresholds</b>'),
        intensity_threshold_label,
        value_threshold_box,  # Standard value threshold (hidden for RP-specific hazards)
        eq_thresholds_box,  # RP-specific thresholds for earthquake (shown by default)
        cy_thresholds_box,  # RP-specific thresholds for cyclone
        ts_thresholds_box,  # RP-specific thresholds for tsunami
        rp_thresholds_box,  # RP-specific thresholds for extreme heat
        area_threshold_input
    ], layout=widgets.Layout(padding='10px'))

    # Arrange sections in tabs
    tabs = widgets.Tab(layout={'width': '350px', 'height': '650px'})  # Increased height for country list
    tabs.children = [boundary_tab, hazard_tab]
    tabs.set_title(0, 'Boundary')
    tabs.set_title(1, 'Hazard')

    # Info box
    info_box = notebook_utils.info_box
    info_box.value = 'Multi-hazard threshold analysis tool. Select boundary type and hazard parameters.'

    # Footer with Run button
    footer = notebook_utils.create_footer()

    # Sidebar - custom layout with output below run button
    sidebar_content = widgets.VBox([
        info_box,
        tabs
    ], layout=widgets.Layout(overflow='auto'))

    sidebar = widgets.VBox([
        sidebar_content,
        footer,
        output
    ], layout=widgets.Layout(width='370px', height='100%'))

    # Header
    header = widgets.HTML(value=f"""
    <div style='
        background: linear-gradient(to bottom, #003366, transparent);
        padding: 20px;
        border-radius: 10px 10px 0 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
        width: 100%;
        box-sizing: border-box;
    '>
        <div style="flex: 1;">
            <h1 style='color: #FFFFFF; margin: 0; font-size: 1.5vw;'>RISK DATA LIBRARY</h1>
            <h2 style='color: #ff5733; margin: 10px 0; font-size: 1.2vw;'><b>ANALYTICAL TOOL</b></h2>
            <h4 style='color: #118AB2; margin: 0; font-size: 1vw;'><b>MULTI-HAZARD THRESHOLD ANALYSIS</b></h4>
        </div>
    </div>
    """, layout=widgets.Layout(width='99%'))

    # Get UI components
    map_and_chart, content_layout, final_layout = notebook_utils.get_ui_components(sidebar, header, map_widget)

    # Display the layout
    display(final_layout)

    # Initial preview
    update_preview_map()

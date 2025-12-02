"""
AWS Fathom ADM Extract - Administrative Unit Hazard Ranking from AWS Tiles
Adapted from AWS_Fathom_extract.py and TH_FL_utils.py

This script performs flood hazard ranking by administrative unit using global-extent
Fathom tiles hosted on AWS S3, rather than country-extent locally downloaded data.

The hazard ranking is based on:
- Value threshold: Minimum flood depth (cm) to consider
- Area threshold: Minimum percentage of area affected
- Hazard score: Count of return periods meeting both thresholds (0-3)

MEMORY OPTIMIZATION:
- Uses VRT (Virtual Raster) instead of physical merging - VRT is just XML metadata
- VRT has no memory footprint - tiles are read on-demand as needed
- Windowed reading: only reads pixels within each admin unit's bbox
- Efficient for large countries spanning hundreds of tiles
"""

import boto3
import os
import sys
import rasterio as rst
from rasterio.mask import mask as rio_mask
import numpy as np
import math
import geopandas as gpd
import pandas as pd
import time
from dotenv import load_dotenv
from os.path import join, expanduser, exists
import logging
from datetime import datetime
from pathlib import Path
from shapely.geometry import box, shape
import subprocess
import requests


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# WB ArcGIS REST API URL for administrative boundaries
WB_ARCGIS_URL = "https://services.arcgis.com/iQ1dY19aHwbSDYIF/arcgis/rest/services/World_Bank_Global_Administrative_Divisions/FeatureServer"


def get_layer_id_for_adm(adm_level):
    """
    Get the correct layer ID from WB ArcGIS service based on administrative level.

    :param adm_level: Administrative level (0, 1, 2, etc.)
    :return: Layer ID for the specified admin level
    """
    layers_url = f"{WB_ARCGIS_URL}/layers"
    target_layer_name = f"WB_GAD_ADM{adm_level}"

    try:
        response = requests.get(layers_url, params={'f': 'json'}, timeout=30)

        if response.status_code != 200:
            logger.error(f"Failed to fetch layers. Status code: {response.status_code}")
            return None

        layers_info = response.json().get('layers', [])

        layers = [elem['id'] for elem in layers_info if elem['name'] == target_layer_name]
        if len(layers) == 0:
            raise ValueError(f"Layer matching {target_layer_name} not found.")

        logger.info(f"Found layer ID {layers[0]} for {target_layer_name}")
        return layers[0]

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching layer ID: {e}")
        raise


def get_all_countries_list(adm_level):
    """
    Fetch list of all countries available in the WB ArcGIS service.

    :param adm_level: Administrative level (0, 1, 2, etc.)
    :return: List of ISO3 country codes
    """
    logger.info(f"Fetching list of all countries from WB ArcGIS service (ADM{adm_level})...")

    layer_id = get_layer_id_for_adm(adm_level)

    query_url = f"{WB_ARCGIS_URL}/{layer_id}/query"
    params = {
        'where': '1=1',  # Get all records
        'outFields': 'ISO_A3',
        'returnGeometry': 'false',
        'returnDistinctValues': 'true',
        'f': 'json'
    }

    try:
        response = requests.get(query_url, params=params, timeout=120)

        if response.status_code != 200:
            logger.error(f"Error fetching countries list: {response.status_code}")
            raise Exception(f"Failed to fetch countries list: HTTP {response.status_code}")

        data = response.json()
        features = data.get('features', [])

        if not features:
            raise Exception("No countries found in WB service")

        # Extract unique country codes
        countries = sorted(list(set([f['attributes']['ISO_A3'] for f in features if f['attributes'].get('ISO_A3')])))

        logger.info(f"Found {len(countries)} countries in WB service")
        return countries

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching countries list: {e}")
        raise


def get_adm_data(country, adm_level):
    """
    Fetch administrative boundary data from WB ArcGIS REST API service.

    :param country: ISO3 country code (e.g., 'USA', 'BRA', 'IND')
    :param adm_level: Administrative level (0, 1, 2, etc.)
    :return: GeoDataFrame with administrative boundaries
    """
    logger.info(f"Fetching administrative boundaries for {country}, level {adm_level} from WB ArcGIS service...")

    layer_id = get_layer_id_for_adm(adm_level)

    query_url = f"{WB_ARCGIS_URL}/{layer_id}/query"
    params = {
        'where': f"ISO_A3 = '{country}'",
        'outFields': '*',
        'f': 'geojson'
    }

    try:
        response = requests.get(query_url, params=params, timeout=60)

        if response.status_code != 200:
            logger.error(f"Error fetching data: {response.status_code}")
            raise Exception(f"Failed to fetch admin boundaries: HTTP {response.status_code}")

        data = response.json()
        features = data.get('features', [])

        if not features:
            raise Exception(f"No features found for country {country} at admin level {adm_level}")

        # Convert GeoJSON to GeoDataFrame
        geometry = [shape(feature['geometry']) for feature in features]
        properties = [feature['properties'] for feature in features]
        gdf = gpd.GeoDataFrame(properties, geometry=geometry, crs="EPSG:4326")

        logger.info(f"Successfully fetched {len(gdf)} administrative units")
        return gdf

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching admin data: {e}")
        raise


def get_credentials(credentials_csv=None):
    """
    Get AWS credentials from environment variables
    :param credentials_csv: Deprecated - kept for compatibility
    :return: -
    """
    load_dotenv(join(expanduser("~"), ".aws", "credentials"))


def get_s3_key(filename, rp, ftype='PLUVIAL-DEFENDED', scenario='2020'):
    """
    Get the S3 key for the correct fathom data
    :param filename: filename of the tile in format n00e000.tif
    :param rp: return period of the fathom layer (e.g., '1in100')
    :param ftype: data type. pick one of following:
        - COASTAL-UNDEFENDED
        - COASTAL-DEFENDED
        - FLUVIAL-UNDEFENDED
        - FLUVIAL-DEFENDED
        - PLUVIAL-DEFENDED
    :param scenario: scenario (e.g., '2020', '2030-SSP1_2.6')
    :return: AWS S3 key to file
    """
    key = f"FATHOM/v2023/GLOBAL-1ARCSEC-NW_OFFSET-{rp}-{ftype}-DEPTH-{scenario}-PERCENTILE50-v3.0/{filename}"
    return key


def download_tile(key, s3client, bucket, output_path):
    """
    Download file from AWS to local using exact AWS key
    :param key: Exact filename with prefix on S3
    :param s3client: s3 client object
    :param bucket: name of bucket
    :param output_path: path to save the file
    :return: Path to downloaded file
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    s3client.download_file(bucket, key, output_path)
    return output_path


def create_tile_filename(lon, lat):
    """
    Create appropriate filename for fathom data based on coordinates
    :param lon: longitude
    :param lat: latitude
    :return: filename in format n00e000.tif
    """
    lat_floor = math.floor(lat)
    lon_floor = math.floor(lon)

    prefix_lat = 'n' if lat_floor >= 0 else 's'
    lat_val = str(abs(lat_floor)).zfill(2)

    prefix_lon = 'e' if lon_floor >= 0 else 'w'
    lon_val = str(abs(lon_floor)).zfill(3)

    return f"{prefix_lat}{lat_val}{prefix_lon}{lon_val}.tif"


def get_tiles_for_bounds(bounds):
    """
    Get list of tile filenames needed to cover a bounding box
    :param bounds: (minx, miny, maxx, maxy) in WGS84
    :return: list of tile filenames
    """
    minx, miny, maxx, maxy = bounds

    tiles = set()

    # Generate tiles for all combinations of lat/lon within bounds
    lat_min = math.floor(miny)
    lat_max = math.floor(maxy)
    lon_min = math.floor(minx)
    lon_max = math.floor(maxx)

    for lat in range(lat_min, lat_max + 1):
        for lon in range(lon_min, lon_max + 1):
            tiles.add(create_tile_filename(lon, lat))

    return sorted(list(tiles))


def download_tiles_and_create_vrt(s3, bucket, tiles, rp, ftype, scenario, scratch_dir):
    """
    Download tiles and create a VRT (Virtual Raster) mosaic.
    VRT is a lightweight XML file that references the tiles without loading them into memory.

    :param s3: AWS S3 client
    :param bucket: S3 bucket name
    :param tiles: list of tile filenames
    :param rp: return period (e.g., '1in100')
    :param ftype: flood type
    :param scenario: scenario
    :param scratch_dir: temporary directory for downloads
    :return: path to VRT file
    """
    downloaded_files = []

    for tile in tiles:
        key = get_s3_key(tile, rp, ftype, scenario)
        output_path = os.path.join(scratch_dir, tile)

        try:
            logger.info(f"Downloading tile {tile}...")
            download_tile(key, s3, bucket, output_path)
            downloaded_files.append(output_path)
        except Exception as e:
            logger.warning(f"Failed to download {tile}: {e}")
            continue

    if not downloaded_files:
        raise ValueError("No tiles could be downloaded")

    # If only one tile, return it directly (no need for VRT)
    if len(downloaded_files) == 1:
        return downloaded_files[0]

    # Create VRT mosaic (virtual - no memory footprint)
    logger.info(f"Creating VRT mosaic from {len(downloaded_files)} tiles...")
    vrt_path = os.path.join(scratch_dir, f"mosaic_{rp}_{ftype}_{scenario}.vrt")

    # Use gdalbuildvrt via subprocess for better compatibility
    try:
        cmd = ['gdalbuildvrt', '-overwrite', vrt_path] + downloaded_files
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.info(f"VRT created successfully at {vrt_path}")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        # Fallback: manually create VRT using rasterio
        logger.warning("gdalbuildvrt not available, using rasterio fallback...")
        vrt_path = create_vrt_manual(downloaded_files, vrt_path)

    return vrt_path


def create_vrt_manual(input_files, output_vrt):
    """
    Manually create a VRT file using rasterio when gdalbuildvrt is not available.

    :param input_files: list of input raster paths
    :param output_vrt: path to output VRT file
    :return: path to created VRT
    """
    # Get metadata from first file
    with rst.open(input_files[0]) as src:
        meta = src.meta.copy()
        nodata = src.nodata
        dtype = src.dtypes[0]
        crs = src.crs

    # Calculate bounds of all tiles
    bounds_list = []
    for fp in input_files:
        with rst.open(fp) as src:
            bounds_list.append(src.bounds)

    # Get overall bounds
    from rasterio.coords import BoundingBox
    minx = min(b.left for b in bounds_list)
    miny = min(b.bottom for b in bounds_list)
    maxx = max(b.right for b in bounds_list)
    maxy = max(b.top for b in bounds_list)

    # Use the first file's resolution
    with rst.open(input_files[0]) as src:
        res = src.res

    # Calculate dimensions
    width = int((maxx - minx) / res[0])
    height = int((maxy - miny) / res[1])

    # Create transform
    from rasterio.transform import from_bounds
    transform = from_bounds(minx, miny, maxx, maxy, width, height)

    # Build VRT XML manually
    vrt_xml = f'''<VRTDataset rasterXSize="{width}" rasterYSize="{height}">
  <SRS>{crs.to_wkt()}</SRS>
  <GeoTransform>{transform.a}, {transform.b}, {transform.c}, {transform.d}, {transform.e}, {transform.f}</GeoTransform>
  <VRTRasterBand dataType="{dtype}" band="1">
    <NoDataValue>{nodata if nodata is not None else -9999}</NoDataValue>
'''

    # Add each source file
    for fp in input_files:
        with rst.open(fp) as src:
            src_bounds = src.bounds
            # Calculate pixel offset in the VRT
            x_off = int((src_bounds.left - minx) / res[0])
            y_off = int((maxy - src_bounds.top) / res[1])

            vrt_xml += f'''    <SimpleSource>
      <SourceFilename relativeToVRT="1">{os.path.basename(fp)}</SourceFilename>
      <SourceBand>1</SourceBand>
      <SrcRect xOff="0" yOff="0" xSize="{src.width}" ySize="{src.height}"/>
      <DstRect xOff="{x_off}" yOff="{y_off}" xSize="{src.width}" ySize="{src.height}"/>
    </SimpleSource>
'''

    vrt_xml += '''  </VRTRasterBand>
</VRTDataset>'''

    # Write VRT file
    with open(output_vrt, 'w') as f:
        f.write(vrt_xml)

    logger.info(f"Manual VRT created at {output_vrt}")
    return output_vrt


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
    - Score = count of RPs meeting both thresholds (0, 1, 2, or 3)

    Args:
        value_threshold: Minimum mean value threshold
        area_threshold_pct: Minimum area percentage threshold
        *rp_stats: Tuples of (mean_value, area_pct) for each return period

    Returns:
        int: Hazard score (0-3)
    """
    score = 0

    for mean_val, area_pct in rp_stats:
        if mean_val >= value_threshold and area_pct >= area_threshold_pct:
            score += 1

    return score


def calculate_zonal_stats_for_unit(geometry, raster_path, value_threshold):
    """
    Calculate zonal statistics for a single administrative unit.
    Uses windowed reading - only reads the pixels needed for this geometry's bbox.
    Works efficiently with VRT files (only accesses relevant tiles).

    :param geometry: shapely geometry of the admin unit
    :param raster_path: path to raster file (can be VRT or regular GeoTIFF)
    :param value_threshold: minimum value threshold
    :return: tuple of (mean_above_zero, area_percentage)
    """
    try:
        with rst.open(raster_path) as src:
            # Get the geometry bounds
            geom_bounds = geometry.bounds  # (minx, miny, maxx, maxy)

            # Check if geometry intersects with raster bounds
            raster_bounds = src.bounds
            if not (geom_bounds[0] < raster_bounds[2] and geom_bounds[2] > raster_bounds[0] and
                    geom_bounds[1] < raster_bounds[3] and geom_bounds[3] > raster_bounds[1]):
                logger.warning("Geometry does not intersect with raster bounds")
                return 0, 0

            # Mask the raster with the geometry
            # crop=True limits reading to the geometry's bounding box
            # With VRT, this only reads the necessary tiles from disk
            out_image, out_transform = rio_mask(
                src,
                [geometry],
                crop=True,
                all_touched=True,
                nodata=-9999,
                filled=True  # Fill masked values with nodata
            )

            # Get the data array (first band)
            data = out_image[0]

            # Create mask for valid data
            # Handle multiple possible nodata values
            valid_mask = (data != -9999) & ~np.isnan(data)
            if src.nodata is not None:
                valid_mask &= (data != src.nodata)

            if not valid_mask.any():
                return 0, 0

            values = data[valid_mask]

            if len(values) == 0:
                return 0, 0

            # Calculate mean of values > 0
            mean_val = calculate_mean_above_threshold(values, threshold=0)

            # Count pixels above value threshold
            affected_pixels = np.sum(values > value_threshold)
            total_pixels = len(values)

            # Calculate area percentage
            area_pct = (affected_pixels / total_pixels) * 100 if total_pixels > 0 else 0

            return mean_val, area_pct

    except Exception as e:
        logger.error(f"Error calculating zonal stats: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 0, 0


def process_country_flood_hazard(
    country,
    adm_units,
    s3,
    bucket,
    output_dir,
    adm_level=None,
    flood_types=None,
    value_threshold=100,
    area_threshold_pct=3.0,
    period='2020',
    scenario='',
    return_periods=None,
    scratch_dir='scratch_aws'
):
    """
    Process flood hazard analysis for a single country.

    Args:
        country: ISO3 country code
        adm_units: GeoDataFrame with administrative boundaries for this country
        s3: AWS S3 client
        bucket: S3 bucket name
        output_dir: Directory for output files
        adm_level: Administrative level (for naming)
        flood_types: List of flood types to process
        value_threshold: Minimum value threshold (cm)
        area_threshold_pct: Minimum area percentage threshold
        period: Time period
        scenario: Climate scenario (for future periods)
        return_periods: List of return periods
        scratch_dir: Directory for temporary files

    Returns:
        dict: Dictionary mapping flood types to GeoDataFrames with results
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"PROCESSING COUNTRY: {country}")
    logger.info(f"{'='*80}")

    # Set defaults
    if flood_types is None:
        flood_types = [
            ('FU', 'FLUVIAL-UNDEFENDED'),
            ('FD', 'FLUVIAL-DEFENDED'),
            ('PD', 'PLUVIAL-DEFENDED'),
            ('CU', 'COASTAL-UNDEFENDED'),
            ('CD', 'COASTAL-DEFENDED')
        ]

    if return_periods is None:
        return_periods = [10, 100, 1000]

    # Create country-specific scratch directory
    country_scratch = os.path.join(scratch_dir, country)
    os.makedirs(country_scratch, exist_ok=True)

    # Ensure WGS84
    if adm_units.crs is None or adm_units.crs.to_epsg() != 4326:
        logger.info("Converting CRS to EPSG:4326")
        adm_units = adm_units.to_crs(epsg=4326)

    # Calculate unit areas
    logger.info("Calculating unit areas...")
    adm_units_proj = adm_units.to_crs(adm_units.estimate_utm_crs())
    adm_units['unit_area_m2'] = adm_units_proj.geometry.area

    # Get bounding box for all units
    bounds = adm_units.total_bounds
    logger.info(f"Study area bounds: {bounds}")

    results = {}

    # Process each flood type
    for ftype_short, ftype_long in flood_types:
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing {ftype_long}")
        logger.info(f"{'='*60}")

        # Create a copy for this flood type
        adm_flood = adm_units.copy()

        # Get tiles needed for this area
        tiles = get_tiles_for_bounds(bounds)
        logger.info(f"Need {len(tiles)} tiles to cover study area")

        # Process each return period
        rp_stats = []

        for rp in return_periods:
            rp_name = f'RP{rp}'
            logger.info(f"\nProcessing {rp_name}...")

            # Determine scenario format for AWS
            if period == '2020':
                aws_scenario = '2020'
            else:
                aws_scenario = f"{period}-{scenario}"

            rp_text = f'1in{rp}'

            try:
                # Download tiles and create VRT (virtual mosaic - no memory footprint)
                vrt_path = download_tiles_and_create_vrt(
                    s3, bucket, tiles, rp_text, ftype_long, aws_scenario, country_scratch
                )

                # Calculate zonal statistics for each admin unit
                # VRT allows on-demand reading - only necessary tiles are accessed per geometry
                means_above_zero = []
                area_percentages = []

                logger.info(f"Calculating zonal statistics for {len(adm_flood)} units...")

                for idx, row in adm_flood.iterrows():
                    mean_val, area_pct = calculate_zonal_stats_for_unit(
                        row.geometry, vrt_path, value_threshold
                    )
                    means_above_zero.append(mean_val)
                    area_percentages.append(area_pct)

                    if (idx + 1) % 10 == 0:
                        logger.info(f"  Processed {idx + 1}/{len(adm_flood)} units")

                # Add to dataframe
                adm_flood[f'{rp_name}_mean'] = means_above_zero
                adm_flood[f'{rp_name}_affected_pct'] = area_percentages

                logger.info(f"  Mean statistics: {min(means_above_zero):.2f} - {max(means_above_zero):.2f}")
                logger.info(f"  Affected area %: {min(area_percentages):.2f}% - {max(area_percentages):.2f}%")

                rp_stats.append((means_above_zero, area_percentages))

                # Note: We keep the tiles and VRT until the end of processing
                # This allows reuse if needed and clean batch deletion



            except Exception as e:
                logger.error(f"Error processing {rp_name}: {e}")
                # Add empty columns
                adm_flood[f'{rp_name}_mean'] = 0
                adm_flood[f'{rp_name}_affected_pct'] = 0
                rp_stats.append(([0] * len(adm_flood), [0] * len(adm_flood)))

        # Calculate hazard scores
        logger.info("\nCalculating Hazard Scores...")
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
        logger.info("\nHazard Score Distribution:")
        for score, count in score_counts.items():
            percentage = (count / len(adm_flood)) * 100
            logger.info(f"  Score {score}: {count} units ({percentage:.1f}%)")

        results[ftype_short] = adm_flood

    # Clean up country-specific scratch directory
    logger.info("Cleaning up temporary files...")
    try:
        import shutil
        shutil.rmtree(country_scratch)
    except:
        pass

    logger.info(f"Completed processing for {country}")
    return results


def process_flood_hazard_aws(
    adm_level,
    s3,
    bucket,
    output_dir='output',
    countries=None,
    adm_units_file=None,
    layer_name=None,
    flood_types=None,
    value_threshold=100,
    area_threshold_pct=3.0,
    period='2020',
    scenario='',
    return_periods=None,
    scratch_dir='scratch_aws'
):
    """
    Main processing function for flood hazard threshold analysis using AWS tiles.
    Automatically processes all countries found in the administrative boundaries data.

    Args:
        adm_level: Administrative level (0, 1, 2)
        s3: AWS S3 client
        bucket: S3 bucket name
        output_dir: Directory for output files
        countries: List of ISO3 country codes to process (if None, fetches all from WB service or file)
        adm_units_file: Path to geopackage/shapefile with administrative boundaries (alternative to WB service)
        layer_name: Layer name within the input file (only used with adm_units_file)
        flood_types: List of flood types to process
        value_threshold: Minimum value threshold (cm)
        area_threshold_pct: Minimum area percentage threshold
        period: Time period
        scenario: Climate scenario (for future periods)
        return_periods: List of return periods
        scratch_dir: Directory for temporary files

    Returns:
        dict: Dictionary mapping country codes to their results dictionaries
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(scratch_dir, exist_ok=True)

    all_countries_results = {}

    # Load or fetch administrative boundaries
    if adm_units_file is not None:
        # Load from file
        logger.info(f"Loading administrative boundaries from {adm_units_file}...")
        if layer_name:
            adm_all = gpd.read_file(adm_units_file, layer=layer_name)
        else:
            adm_all = gpd.read_file(adm_units_file)
        logger.info(f"Loaded {len(adm_all)} administrative units")

        # Extract unique countries from the data
        if 'ISO_A3' not in adm_all.columns:
            raise ValueError("Input file must contain 'ISO_A3' column with country codes")

        countries_in_data = adm_all['ISO_A3'].unique()
        logger.info(f"Found {len(countries_in_data)} countries in the data: {', '.join(sorted(countries_in_data))}")

    else:
        # Fetch from WB ArcGIS service
        if countries is None:
            # Get ALL countries from the service
            countries_in_data = get_all_countries_list(adm_level)
            logger.info(f"Will process ALL {len(countries_in_data)} countries from WB service")
        else:
            # Use specified list
            countries_in_data = countries
            logger.info(f"Will process {len(countries_in_data)} specified countries from WB service: {', '.join(sorted(countries_in_data))}")

        adm_all = None

    # Process each country
    for idx, country in enumerate(sorted(countries_in_data), 1):
        logger.info(f"\n{'#'*80}")
        logger.info(f"# COUNTRY {idx}/{len(countries_in_data)}: {country}")
        logger.info(f"{'#'*80}\n")

        try:
            # Get country-specific boundaries
            if adm_all is not None:
                # Filter from loaded data
                adm_country = adm_all[adm_all['ISO_A3'] == country].copy()
                logger.info(f"Filtered {len(adm_country)} units for {country}")
            else:
                # Fetch from WB service
                adm_country = get_adm_data(country, adm_level)

            if len(adm_country) == 0:
                logger.warning(f"No administrative units found for {country}, skipping...")
                continue

            # Process this country
            country_results = process_country_flood_hazard(
                country=country,
                adm_units=adm_country,
                s3=s3,
                bucket=bucket,
                output_dir=output_dir,
                adm_level=adm_level,
                flood_types=flood_types,
                value_threshold=value_threshold,
                area_threshold_pct=area_threshold_pct,
                period=period,
                scenario=scenario,
                return_periods=return_periods,
                scratch_dir=scratch_dir
            )

            all_countries_results[country] = country_results

        except Exception as e:
            logger.error(f"Failed to process {country}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            continue

    # Clean up main scratch directory
    logger.info("\nCleaning up main scratch directory...")
    try:
        import shutil
        shutil.rmtree(scratch_dir)
    except:
        pass

    logger.info(f"\n{'='*80}")
    logger.info(f"PROCESSING COMPLETE")
    logger.info(f"Successfully processed {len(all_countries_results)}/{len(countries_in_data)} countries")
    logger.info(f"{'='*80}")

    # Create global outputs
    if len(all_countries_results) > 0:
        logger.info("\nCreating global outputs...")
        create_global_outputs(
            all_countries_results,
            output_dir,
            adm_level,
            period,
            scenario,
            flood_types if flood_types else [
                ('FU', 'FLUVIAL-UNDEFENDED'),
                ('FD', 'FLUVIAL-DEFENDED'),
                ('PD', 'PLUVIAL-DEFENDED'),
                ('CU', 'COASTAL-UNDEFENDED'),
                ('CD', 'COASTAL-DEFENDED')
            ]
        )

    return all_countries_results


def create_global_outputs(all_countries_results, output_dir, adm_level, period, scenario, flood_types):
    """
    Create global GeoPackage and summary Excel report from all country results.

    Args:
        all_countries_results: Dictionary mapping country codes to their results
        output_dir: Output directory
        adm_level: Administrative level
        period: Time period
        scenario: Climate scenario
        flood_types: List of flood type tuples
    """
    adm_level_str = f"ADM{adm_level}" if adm_level is not None else "ADM"

    if period == '2020':
        base_name = f"GLOBAL_FL_hazard_{adm_level_str}_{period}"
    else:
        base_name = f"GLOBAL_FL_hazard_{adm_level_str}_{period}_{scenario.split('-')[0]}"

    global_gpkg = os.path.join(output_dir, f"{base_name}.gpkg")
    global_excel = os.path.join(output_dir, f"{base_name}_summary.xlsx")

    # ========================================================================
    # 1. CREATE GLOBAL GEOPACKAGE
    # ========================================================================
    logger.info(f"Creating global GeoPackage: {global_gpkg}")

    # Process each flood type
    for ftype_short, ftype_long in flood_types:
        # Combine all countries for this flood type
        country_gdfs = []

        for country, results in all_countries_results.items():
            if ftype_short in results:
                gdf = results[ftype_short].copy()
                # Ensure ISO_A3 column exists
                if 'ISO_A3' not in gdf.columns:
                    gdf['ISO_A3'] = country
                country_gdfs.append(gdf)

        if country_gdfs:
            # Concatenate all countries
            global_gdf = pd.concat(country_gdfs, ignore_index=True)

            # Save to global geopackage
            layer = f"{ftype_short}_{period}"
            if period != '2020':
                layer = f"{ftype_short}_{period}_{scenario.split('-')[0]}"

            global_gdf.to_file(global_gpkg, layer=layer, driver="GPKG")
            logger.info(f"  Saved layer: {layer} ({len(global_gdf)} units from {len(country_gdfs)} countries)")

    # ========================================================================
    # 2. CREATE GLOBAL SUMMARY EXCEL
    # ========================================================================
    logger.info(f"Creating global summary Excel: {global_excel}")

    with pd.ExcelWriter(global_excel, engine='openpyxl') as writer:

        # Process each flood type
        for ftype_short, ftype_long in flood_types:

            # Collect country-level statistics
            country_stats = []

            for country in sorted(all_countries_results.keys()):
                results = all_countries_results[country]

                if ftype_short not in results:
                    continue

                gdf = results[ftype_short]

                # Calculate total area (in km²)
                total_area_m2 = gdf['unit_area_m2'].sum()
                total_area_km2 = total_area_m2 / 1_000_000

                # Count units by score
                score_counts = gdf['Hazard_score'].value_counts().sort_index()
                total_units = len(gdf)

                # Calculate area by score
                score_areas = {}
                for score in range(4):
                    score_units = gdf[gdf['Hazard_score'] == score]
                    score_area_m2 = score_units['unit_area_m2'].sum()
                    score_areas[score] = score_area_m2 / 1_000_000  # Convert to km²

                # Build statistics row
                stat_row = {
                    'Country': country,
                    'Total_Units': total_units,
                    'Total_Area_km2': round(total_area_km2, 2)
                }

                # Add count and percentage for each score
                for score in range(4):
                    count = score_counts.get(score, 0)
                    pct = (count / total_units * 100) if total_units > 0 else 0
                    stat_row[f'Score_{score}_Count'] = count
                    stat_row[f'Score_{score}_Count_Pct'] = round(pct, 2)

                # Add area and percentage for each score
                for score in range(4):
                    area = score_areas.get(score, 0)
                    pct = (area / total_area_km2 * 100) if total_area_km2 > 0 else 0
                    stat_row[f'Score_{score}_Area_km2'] = round(area, 2)
                    stat_row[f'Score_{score}_Area_Pct'] = round(pct, 2)

                country_stats.append(stat_row)

            if country_stats:
                # Create DataFrame
                df_stats = pd.DataFrame(country_stats)

                # Add global totals row
                global_totals = {
                    'Country': 'GLOBAL TOTAL',
                    'Total_Units': df_stats['Total_Units'].sum(),
                    'Total_Area_km2': round(df_stats['Total_Area_km2'].sum(), 2)
                }

                # Calculate global totals for each score
                for score in range(4):
                    global_totals[f'Score_{score}_Count'] = df_stats[f'Score_{score}_Count'].sum()
                    global_totals[f'Score_{score}_Area_km2'] = round(df_stats[f'Score_{score}_Area_km2'].sum(), 2)

                    # Calculate global percentages
                    total_units = global_totals['Total_Units']
                    total_area = global_totals['Total_Area_km2']

                    global_totals[f'Score_{score}_Count_Pct'] = round(
                        (global_totals[f'Score_{score}_Count'] / total_units * 100) if total_units > 0 else 0, 2
                    )
                    global_totals[f'Score_{score}_Area_Pct'] = round(
                        (global_totals[f'Score_{score}_Area_km2'] / total_area * 100) if total_area > 0 else 0, 2
                    )

                # Append global totals
                df_stats = pd.concat([df_stats, pd.DataFrame([global_totals])], ignore_index=True)

                # Save to Excel
                sheet_name = f"{ftype_short}_{period}"[:31]
                df_stats.to_excel(writer, sheet_name=sheet_name, index=False)
                logger.info(f"  Created summary sheet: {sheet_name}")

    logger.info(f"\nGlobal outputs created successfully!")
    logger.info(f"  GeoPackage: {global_gpkg}")
    logger.info(f"  Summary: {global_excel}")


if __name__ == '__main__':
    # ===================================================================
    # CONFIGURATION
    # ===================================================================

    # Administrative level to process
    adm_level = 2  # 0=country, 1=provinces/states, 2=districts

    # OPTION 1: Fetch boundaries from WB ArcGIS service
    USE_WB_SERVICE = True
    
    # countries_to_process = ['FJI', 'TON', 'WSM']  # List of ISO3 country codes
    countries_to_process = None  # Process all countries automatically

    # OPTION 2: Use local boundary file (processes all countries in the file)
    # USE_WB_SERVICE = False
    # input_boundaries = 'data/admin_boundaries.gpkg'  # Must have ISO_A3 column
    # layer_name = None

    input_boundaries = 'data/admin_boundaries.gpkg'  # Only used if USE_WB_SERVICE = False
    layer_name = None  # Only used if USE_WB_SERVICE = False

    # Output configuration
    output_dir = 'output'  # One file per country will be created

    # Hazard parameters
    value_threshold = 50  # cm - minimum flood depth to consider
    area_threshold_pct = 3.0  # percent - minimum area affected

    # Define flood types with their short and long names
    flood_types = [
        ('FU', 'FLUVIAL-UNDEFENDED'),
        ('CU', 'COASTAL-UNDEFENDED'),
        ('PD', 'PLUVIAL-DEFENDED'),
        # ('FD', 'FLUVIAL-DEFENDED'),
        # ('CD', 'COASTAL-DEFENDED')
    ]

    # Define periods, scenarios, and return periods to process
    period = '2020'
    scenario = ''  # For 2020, leave empty. For future: 'SSP1_2.6', 'SSP2_4.5', 'SSP3_7.0', 'SSP5_8.5'
    return_periods = [10, 100, 1000]

    # ===================================================================
    # EXECUTION
    # ===================================================================

    # Get AWS credentials
    get_credentials()

    # Initialize S3 client
    s3 = boto3.client('s3')
    bucket = 'wbg-geography01'

    # Process the data
    start_time = datetime.now()
    logger.info(f"Starting analysis at {start_time.strftime('%H:%M:%S')}")

    if USE_WB_SERVICE:
        # Fetch boundaries from WB ArcGIS service for specified countries
        results = process_flood_hazard_aws(
            adm_level=adm_level,
            s3=s3,
            bucket=bucket,
            output_dir=output_dir,
            countries=countries_to_process,
            flood_types=flood_types,
            value_threshold=value_threshold,
            area_threshold_pct=area_threshold_pct,
            period=period,
            scenario=scenario,
            return_periods=return_periods,
            scratch_dir='scratch_aws'
        )
    else:
        # Use local boundary file - processes all countries in the file
        results = process_flood_hazard_aws(
            adm_level=adm_level,
            s3=s3,
            bucket=bucket,
            output_dir=output_dir,
            adm_units_file=input_boundaries,
            layer_name=layer_name,
            flood_types=flood_types,
            value_threshold=value_threshold,
            area_threshold_pct=area_threshold_pct,
            period=period,
            scenario=scenario,
            return_periods=return_periods,
            scratch_dir='scratch_aws'
        )

    end_time = datetime.now()
    delta = end_time - start_time
    logger.info(f"\nCompleted at {end_time.strftime('%H:%M:%S')}")
    logger.info(f"Total Runtime: {delta.seconds//60} minutes and {delta.seconds % 60} seconds")

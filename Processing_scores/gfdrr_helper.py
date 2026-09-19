import os, logging

import rasterio

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt

from affine import Affine
from rasterio.features import rasterize, MergeAlg

def map_flood(mapD, return_period, out_file):
    fig, axes = plt.subplots(nrows=1, ncols=3, figsize=(15, 6))
    flood_columns = [f"frac_area_flooded_CU_{return_period}yr", f"frac_area_flooded_FU_{return_period}yr", f"frac_area_flooded_PD_{return_period}yr"]
    flood_titles = ["Coastal", "Fluvial", "Pluvial"]
    flood_thresh = [0, 1, 3, 5, 10, 100]
    i = 0

    for col in flood_columns:
        ax = axes[i]
        if i ==1:
            legend_kwds={
                'title': 'Fraction of Area Flooded (%)',
                'ncol': 3,#len(flood_thresh)-1,
                'bbox_to_anchor': (1.2, 0.0), # Fine-tune the position relative to the plot
            }
        else:
            legend_kwds=None
        mapD.plot(column=col, ax=ax, legend=i==1, cmap='Blues', missing_kwds={"color": "lightgrey"},
                  scheme="UserDefined", classification_kwds={"bins": flood_thresh}, legend_kwds=legend_kwds)
        #ax.set_axis_off()
        ax.set_title(f'{flood_titles[i]} Flooding - {return_period}-Year Return Period')
        ax.set_facecolor('darkslategray')
        i += 1
    plt.tight_layout()
    plt.savefig(out_file)
    plt.close()

def calculate_think_hazard_score(inD, raster_path, depth_threshold, idx_col,
                                 all_touched=True):
    """
    Calculate hazard score for a single administrative unit based on mean depth and area percentage.

    Args:
        inD: GeoDataFrame with geometry of the admin units
        raster_path: path to raster file (can be VRT or regular GeoTIFF)
        depth_threshold: minimum depth threshold for hazard scoring
        idx_col: column name for the index
        all_touched: whether to include pixels touched by geometry boundary

    Note:
        Nodata values are automatically handled by excluding all negative values (< 0).
        Valid flood depths are always >= 0.
    """
    with rasterio.Env(GDAL_HTTP_UNSAFESSL='YES'):
        curRaster = rasterio.open(raster_path)
        res = {}

        # Note: We don't need to read the nodata value since we simply exclude all negative values
        # Valid flood depths are always >= 0, so any negative value is nodata

        for idx, row in inD.iterrows():
            geometry = row["geometry"]

            # FIXED: Calculate correct corners
            # Upper-left: (minx, maxy)
            # Lower-right: (maxx, miny)
            ul = curRaster.index(geometry.bounds[0], geometry.bounds[3])
            lr = curRaster.index(geometry.bounds[2], geometry.bounds[1])

            # FIXED: Build window manually from calculated corners
            # Do NOT use from_bounds() - it bypasses the corner calculation!
            window = (
                (float(ul[0]), float(lr[0] + 1)),  # (row_start, row_stop)
                (float(ul[1]), float(lr[1] + 1)),  # (col_start, col_stop)
            )

            try:
                # Read data from the window
                data = curRaster.read(1, window=window)

                # FIXED: Create affine transform anchored at upper-left corner
                # Use ul[0] for both X and Y offsets (not lr[0]!)
                t = curRaster.transform
                shifted_affine = Affine(
                    t.a, t.b, t.c + ul[1] * t.a,  # X offset: ul[1] * pixel_width
                    t.d, t.e, t.f + ul[0] * t.e   # Y offset: ul[0] * pixel_height (FIXED: was lr[0])
                )

                # Rasterize the geometry with corrected affine
                geom_mask = rasterize(
                    [(geometry, 0)],
                    out_shape=data.shape,
                    transform=shifted_affine,
                    fill=1,
                    all_touched=all_touched,
                    dtype=np.uint8,
                )

                # FIXED: Create nodata mask properly
                # Exclude all negative values as nodata (Fathom uses various negative values)
                # Valid flood depths are always >= 0
                nodata_mask = (data < 0)

                # FIXED: Combine masks properly
                # combined_mask = True means: outside geometry OR nodata (exclude these pixels)
                combined_mask = geom_mask.astype(bool) | nodata_mask

                # Extract valid values (inside geometry AND valid data)
                valid_values = data[~combined_mask]

                if len(valid_values) > 0:
                    # Mean of all wet pixels (depth > 0)
                    wet = valid_values[valid_values > 0]
                    mean_val = float(np.mean(wet)) if len(wet) > 0 else 0.0

                    # Area fraction: pixels above depth threshold / all valid land pixels
                    area_flooded = np.sum(valid_values > depth_threshold)
                    frac_area_flooded = (area_flooded / len(valid_values)) * 100
                else:
                    mean_val = 0.0
                    frac_area_flooded = 0.0

                res[idx] = {
                    idx_col: row[idx_col],
                    'mean_val': mean_val,
                    'frac_area_flooded': frac_area_flooded,
                }

            except Exception as e:
                logging.error(f"Error processing geometry at index {idx}: {e}")
                res[idx] = {
                    idx_col: row[idx_col],
                    'mean_val': 0,
                    'frac_area_flooded': 0,
                }

        curRaster.close()
        return pd.DataFrame.from_dict(res, orient='index')


def calculate_hazard_score(depth_threshold, area_threshold, *args):
    """
    Calculate hazard score based on dual thresholds.

    Args:
        depth_threshold: minimum mean depth (cm) for scoring
        area_threshold: minimum area percentage (%) for scoring
        *args: pairs of (mean_val, frac_area_flooded) for each return period

    Returns:
        int: hazard score (0-4 based on number of return periods exceeding both thresholds)
    """
    score = 0
    for mean_val, frac_area in args:
        # Both conditions must be met for this return period to count
        if mean_val >= depth_threshold and frac_area >= area_threshold:
            score += 1
    return score

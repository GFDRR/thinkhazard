# TH admin layer fixer
# Basically adds rows (features) and columns (attributes) fixing issues in the
# original WB admin layers derived from GAUL2015. 
# Uses patch files (.shp) to correct ADM layers and renames some ADM units
# with better-known spelling to improve search. Saves as shp.
# - TH_fields.dbf includes the translations for country names for ADM0.
# - ADM0_patch.shp includes the edited shape for France and New Zealand to solve zoom issues,
#   added missing disputed areas (Falkland, Western Sahara).
# - ADM1_patch.shp includes the edited shape for Tokyo and New Zealand to solve zoom issues. 

# Import libraries
import os
import numpy as np
import pandas as pd
import geopandas as gpd
from datetime import datetime

# set working directory
wd = "X:/Work/WB/Thinkhazard/Geodata/admin/Basemap_processing/"

os.chdir(wd)

# Read file from File Geodatabase
wb_gdb = "2015_GAUL_Dataset_Mod.gdb"

# ADM0 is updated using a patch file (TH_patch.shp) which substitute some of the
# existing geometries (France country zoom extent)

# Load ADM0 shp files and table
wb = gpd.read_file(wb_gdb, driver="FileGDB", encoding='utf-8', layer='g2015_2014_0').drop(['EXP0_YEAR', 'STR0_YEAR'], 1)
thp0 = gpd.read_file('ADM0_patch.shp', encoding='utf-8')
tha = gpd.read_file('TH_fields.dbf', encoding='utf-8').drop('geometry', 1)
# Remove france
for index, row in wb.iterrows():
    if row['ADM0_NAME'] == 'France':
        wb.drop(index, inplace=True)
# Merge shp files
ADM0 = gpd.GeoDataFrame(pd.concat([wb, thp0], ignore_index=True))
#Add TH attributes from table
ADM0 = ADM0.merge(tha, on='ADM0_CODE', how='left')

# Ref system
ADM0.crs = {'proj': 'latlong', 'ellps': 'WGS84', 'datum': 'WGS84', 'no_defs': True}

#Export shp
ADM0.to_file("ADM0_TH.shp", driver="ESRI Shapefile",  encoding='utf-8')

# Apply corrections to ADM1 and ADM2 names
ADM1 = gpd.read_file(wb_gdb, driver="FileGDB", encoding='utf-8', layer='g2015_2014_1').drop(['EXP1_YEAR', 'STR1_YEAR'], 1)
ADM1[['UpdtField', 'OrigVal', 'Updated', 'FRE', 'ESP', 'LOCAL']] = pd.DataFrame([[np.nan, np.nan, np.nan, np.nan, np.nan, np.nan]], index=ADM1.index)
ADM2 = gpd.read_file(wb_gdb, driver="FileGDB", encoding='utf-8', layer='g2015_2014_2').drop(['EXP2_YEAR', 'STR2_YEAR'], 1)
ADM2[['UpdtField', 'OrigVal', 'Updated', 'FRE', 'ESP', 'LOCAL']] = pd.DataFrame([[np.nan, np.nan, np.nan, np.nan, np.nan, np.nan]], index=ADM2.index)

corrections = {'Tookyoo': 'Tokyo', 'Tiba': 'Chiba', 'U.K. of Great Britain and Northern Ireland': 'United Kingdom', 'Norfolkshire': 'Norfolk'}
tgt_col = 'ADM1_NAME'
curr_date = datetime.today().strftime('%Y-%m-%d')
for k, v in corrections.items():
    ADM1.loc[ADM1.ADM1_NAME == k, ['UpdtField', 'OrigVal', 'Updated', tgt_col]] = [tgt_col, k, curr_date, v]
    ADM2.loc[ADM2.ADM1_NAME == k, ['UpdtField', 'OrigVal', 'Updated', tgt_col]] = [tgt_col, k, curr_date, v]    
    ADM2.loc[ADM2.ADM2_NAME == k, ['UpdtField', 'OrigVal', 'Updated', tgt_col]] = [tgt_col, k, curr_date, v]

# ADM1 is updated using a patch file (ADM1_patch.shp) which substitute some of the
# existing geometries for zoom purpose (Tokyo, New Zealand)

# Load ADM1 patch shp file
thp1 = gpd.read_file('ADM1_patch.shp')
# Remove Tokyo
for index, row in ADM1.iterrows():
    if row['ADM1_NAME'] == 'Tokyo':
        ADM1.drop(index, inplace=True)
# Remove New Zealand
for index, row in ADM1.iterrows():
    if row['ADM0_NAME'] == 'New Zealand':
        ADM1.drop(index, inplace=True)
# Merge shp files
ADM1 = gpd.GeoDataFrame(pd.concat([ADM1, thp1], ignore_index=True))

# Ref system
ADM1.crs = {'proj': 'latlong', 'ellps': 'WGS84', 'datum': 'WGS84', 'no_defs': True}
ADM2.crs = {'proj': 'latlong', 'ellps': 'WGS84', 'datum': 'WGS84', 'no_defs': True}

#Export shp
ADM1.to_file("ADM1_TH.shp", driver="ESRI Shapefile", encoding='utf-8')
ADM2.to_file("ADM2_TH.shp", driver="ESRI Shapefile", encoding='utf-8')

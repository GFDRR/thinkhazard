#!/usr/bin/env python3
"""
Convert TH_ADM2.csv and TH_URB.csv to flat JSON formats for query builder/autocomplete.
This script processes the CSV files and generates:
1. divisions_flat.json - All administrative divisions in flat format with parent references
2. countries.json - List of countries only
3. urban_areas.json - All urban areas with parent references
"""

import csv
import json
from collections import OrderedDict

def read_csv_data(csv_file):
    """Read and parse the TH_ADM2.csv file."""
    divisions = []
    countries = {}
    adm1_divisions = {}

    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        for row in reader:
            iso3 = row['ISO_A3']
            iso2 = row['ISO_A2']
            country_name = row['NAM_0']
            adm1_name = row['NAM_1']
            adm2_name = row['NAM_2']
            adm1_code = row['COD_1']
            adm2_code = row['COD_2']

            # Store unique countries (ADM0)
            if iso3 not in countries:
                countries[iso3] = {
                    'code': iso3,
                    'name': country_name,
                    'iso2': iso2,
                    'iso3': iso3,
                    'level': 'ADM0',
                    'parent_code': None,
                    'parent_name': None,
                    'country_code': iso3,
                    'country_name': country_name,
                    'full_path': country_name
                }

            # Store unique ADM1 divisions
            if adm1_code not in adm1_divisions:
                adm1_divisions[adm1_code] = {
                    'code': adm1_code,
                    'name': adm1_name,
                    'level': 'ADM1',
                    'parent_code': iso3,
                    'parent_name': country_name,
                    'country_code': iso3,
                    'country_name': country_name,
                    'full_path': f'{country_name} > {adm1_name}'
                }

            # Store ADM2 divisions
            divisions.append({
                'code': adm2_code,
                'name': adm2_name,
                'level': 'ADM2',
                'parent_code': adm1_code,
                'parent_name': adm1_name,
                'country_code': iso3,
                'country_name': country_name,
                'full_path': f'{country_name} > {adm1_name} > {adm2_name}'
            })

    return countries, adm1_divisions, divisions


def generate_flat_json(countries, adm1_divisions, adm2_divisions, output_file):
    """Generate the flat JSON format with all divisions."""
    all_divisions = []

    # Add countries (ADM0)
    all_divisions.extend(sorted(countries.values(), key=lambda x: x['name']))

    # Add ADM1 divisions
    all_divisions.extend(sorted(adm1_divisions.values(), key=lambda x: (x['country_name'], x['name'])))

    # Add ADM2 divisions
    all_divisions.extend(sorted(adm2_divisions, key=lambda x: (x['country_name'], x['parent_name'], x['name'])))

    output = {
        'description': 'Flat format with parent references optimized for search and autocomplete',
        'format': 'Single array with all divisions, each referencing its parent',
        'usage': 'Ideal for: Searchable dropdowns, autocomplete, filtering, client-side queries',
        'total_count': len(all_divisions),
        'divisions': all_divisions
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f'[OK] Generated {output_file} with {len(all_divisions)} divisions')
    print(f'  - ADM0 (Countries): {len(countries)}')
    print(f'  - ADM1 (States/Provinces): {len(adm1_divisions)}')
    print(f'  - ADM2 (Districts): {len(adm2_divisions)}')


def generate_countries_json(countries, output_file):
    """Generate a simple countries-only JSON file."""
    countries_list = sorted(countries.values(), key=lambda x: x['name'])

    # Simplify for countries list
    simple_countries = [
        {
            'code': c['code'],
            'name': c['name'],
            'iso2': c['iso2'],
            'iso3': c['iso3']
        }
        for c in countries_list
    ]

    output = {
        'description': 'Simple country list for initial dropdown selection',
        'format': 'Array of countries with codes and ISO standards',
        'usage': 'Ideal for: First-level country selection dropdown',
        'total_count': len(simple_countries),
        'countries': simple_countries
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f'[OK] Generated {output_file} with {len(simple_countries)} countries')


def read_urban_csv_data(csv_file):
    """Read and parse the TH_URB.csv file."""
    urban_areas = []

    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        for row in reader:
            urban_code = row['COD_URB']
            urban_name = row['NAM_URB']
            iso3 = row['ISO_A3']
            country_name = row['NAM_0']
            adm1_name = row['NAM_1']
            adm1_code = row['COD_1']

            # Create urban area entry
            urban_areas.append({
                'code': f'URB{urban_code}',  # Prefix to distinguish from ADM codes
                'name': urban_name,
                'level': 'URB',
                'parent_code': adm1_code,
                'parent_name': adm1_name,
                'country_code': iso3,
                'country_name': country_name,
                'full_path': f'{country_name} > {adm1_name} > {urban_name}'
            })

    return urban_areas


def generate_urban_json(urban_areas, output_file):
    """Generate the urban areas JSON file."""
    sorted_urban = sorted(urban_areas, key=lambda x: (x['country_name'], x['parent_name'], x['name']))

    output = {
        'description': 'Urban areas with parent references optimized for search and autocomplete',
        'format': 'Array with all urban areas, each referencing its parent administrative division',
        'usage': 'Ideal for: Searchable dropdowns, autocomplete, filtering, client-side queries',
        'total_count': len(sorted_urban),
        'urban_areas': sorted_urban
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f'[OK] Generated {output_file} with {len(sorted_urban)} urban areas')


def main():
    import os

    # Determine the correct path for CSV files
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Try current directory first, then _static
    adm_csv = 'TH_ADM2.csv'
    urb_csv = 'TH_URB.csv'

    if not os.path.exists(adm_csv):
        adm_csv = os.path.join(script_dir, '_static', 'TH_ADM2.csv')
        urb_csv = os.path.join(script_dir, '_static', 'TH_URB.csv')

    # Process administrative divisions
    print(f'Reading {adm_csv}...')
    countries, adm1_divisions, adm2_divisions = read_csv_data(adm_csv)

    print(f'\nGenerating administrative divisions JSON files...')
    generate_flat_json(countries, adm1_divisions, adm2_divisions, 'divisions_flat.json')
    generate_countries_json(countries, 'countries.json')

    # Process urban areas
    if os.path.exists(urb_csv):
        print(f'\nReading {urb_csv}...')
        urban_areas = read_urban_csv_data(urb_csv)

        print(f'\nGenerating urban areas JSON file...')
        generate_urban_json(urban_areas, 'urban_areas.json')
    else:
        print(f'\nWarning: {urb_csv} not found, skipping urban areas')

    print(f'\n[OK] Conversion complete!')
    print(f'\nGenerated files:')
    print(f'  - divisions_flat.json: Complete flat list of administrative divisions')
    print(f'  - countries.json: Countries only (for initial dropdown)')
    if os.path.exists(urb_csv):
        print(f'  - urban_areas.json: Complete list of urban areas')


if __name__ == '__main__':
    main()

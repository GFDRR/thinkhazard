# API Reference

## Overview

The ThinkHazard! API provides programmatic access to hazard assessments, recommendations, and related information for administrative divisions worldwide. Use this API to integrate hazard data into your applications, tools, and workflows.

**Base URL:** `http://thinkhazard.org/en`

**Response Format:** JSON

## Authentication

No authentication is required to access the ThinkHazard! API.

## Reference Data

### Division Codes

Administrative divisions are identified by standard codes.
For easier integration into web applications and query builders, JSON formatted versions are available:

| Level | Description | JSON Reference | Size |
|-------|-------------|----------------|------|
| ADM0 | Countries list | [countries.json](/countries.json) | 245 countries |
| ADM2 | Flat list with parent references | [divisions_flat.json](/divisions_flat.json) | 43,202 divisions |
| URB | Urban areas list | [urban_areas.json](/urban_areas.json) | 2,919 urban areas |

**File Statistics:**
- Total administrative divisions: 43,202
  - Countries (ADM0): 245
  - States/Provinces (ADM1): 3,589
  - Districts (ADM2): 39,368
- Total urban areas (URB): 2,919

### Hazard Types

| Code | Hazard Type |
|------|-------------|
| `EQ` | Earthquake |
| `VA` | Volcano |
| `TS` | Tsunami |
| `TC` | Tropical Cyclones |
| `FL` | River Flood |
| `PF` | Pluvial Flood |
| `CF` | Coastal Flood |
| `LS` | Landslide |
| `EH` | Extreme Heat |
| `WF` | Wildfire |
| `DG` | Water Scarcity |

### Hazard Levels

| Code | Level |
|------|-------|
| `VLO` | Very Low |
| `LOW` | Low |
| `MED` | Medium |
| `HIG` | High |

## Endpoints

### Get Hazard Summary for Division

Retrieve hazard levels for all hazard types in a specific administrative division.

```http
GET /report/{division_code}.json
```

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `division_code` | string | Yes | Administrative division code (e.g., `PAK`, `AFG015`) |

#### Response

Returns an array of hazard assessments for the specified division.

**Response Schema:**

```json
[
  {
    "hazardlevel": {
      "mnemonic": "string",
      "title": "string"
    },
    "hazardtype": {
      "mnemonic": "string",
      "hazardtype": "string"
    }
  }
]
```

#### Example Request

```bash
curl http://thinkhazard.org/en/report/PAK.json
```

#### Example Response

```json
[
  {
    "hazardlevel": {
      "mnemonic": "HIG",
      "title": "High"
    },
    "hazardtype": {
      "mnemonic": "FL",
      "hazardtype": "River flood"
    }
  },
  {
    "hazardlevel": {
      "mnemonic": "MED",
      "title": "Medium"
    },
    "hazardtype": {
      "mnemonic": "EQ",
      "hazardtype": "Earthquake"
    }
  }
]
```

#### Additional Examples

- Country (Pakistan): [http://thinkhazard.org/en/report/PAK.json](http://thinkhazard.org/en/report/PAK.json)
- District (Kandahar, Afghanistan): [http://thinkhazard.org/en/report/AFG015.json](http://thinkhazard.org/en/report/AFG015.json)

---

### Get Complete Hazard Report

Retrieve comprehensive hazard information for a specific hazard type and division, including recommendations, data sources, resources, and contacts.

```http
GET /report/{division_code}/{hazard_type}.json
```

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `division_code` | string | Yes | Administrative division code (e.g., `PAK`) |
| `hazard_type` | string | Yes | Two-letter hazard code (e.g., `FL`, `EQ`) |

#### Response

Returns detailed hazard report including hazard category, recommendations, data sources, resources, and contact information.

**Response Schema:**

```json
{
  "hazard_category": {
    "general_recommendation": "string",
    "hazard_level": "string",
    "hazard_type": "string"
  },
  "recommendations": [
    {
      "text": "string",
      "detail": "string | null"
    }
  ],
  "sources": [
    {
      "id": "string",
      "owner_organization": "string",
      "detail_url": "string"
    }
  ],
  "resources": [
    {
      "text": "string",
      "url": "string"
    }
  ],
  "contacts": [
    {
      "name": "string",
      "email": "string",
      "phone": "string",
      "url": "string"
    }
  ],
  "climate_change_recommendation": "string"
}
```

#### Example Request

```bash
curl http://thinkhazard.org/en/report/PAK/FL.json
```

#### Example Response

```json
{
  "hazard_category": {
    "general_recommendation": "In the area you have selected name of location earthquake hazard is classified as **high** according to the information that is currently available. This means that there is approximately 0.4% chance per year of potentially-damaging earthquake shaking in your project area (about 18% chance in the next 50 years). Based on this information, the impact of earthquake **must be considered** in all phases of the project, in particular during design and construction. Risk studies, project planning decisions, project design, and construction methods **must take into account** the level of earthquake hazard. Further detailed information should be obtained to adequately account for the level of hazard.",
    "hazard_level": "High",
    "hazard_type": "River flood"
  },
  "recommendations": [
    {
      "text": "Find out if the exact project location is in a hazardous zone by using local data, e.g. by collecting local information either from river flood hazard maps, by interviewing local governmental organizations, or by hiring international expertise.",
      "detail": null
    }
  ],
  "sources": [
    {
      "id": "FL-GLOBAL-GLOFRIS",
      "owner_organization": "GLOFRIS",
      "detail_url": "http://45.55.174.20/layers/hazard%3Ainunmask_world_stream_6tthres_2_t_50"
    }
  ],
  "resources": [
    {
      "text": "Cities and Flooding: A Guide to Integrated Urban Flood Risk Management for the 21st Century",
      "url": "http://45.55.174.20/documents/162"
    }
  ],
  "contacts": [
    {
      "name": "Disaster Risk Management Knowledge Centre (DRMKC)",
      "email": "drmkc@jrc.ec.europa.eu",
      "phone": "",
      "url": "http://drmkc.jrc.ec.europa.eu/#news/432/list"
    }
  ],
  "climate_change_recommendation": "Climate change impacts: Model projections are inconsistent in changes in rainfall."
}
```

---

### Search Administrative Divisions

Search for administrative divisions by name or code to find the correct division code for API requests.

```http
GET /divisions/search?q={query}&level={level}
```

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | Yes | Search query (name or code) |
| `level` | string | No | Filter by administrative level: `ADM0`, `ADM1`, or `ADM2` |
| `limit` | integer | No | Maximum results to return (default: 20, max: 100) |

#### Response

Returns an array of matching divisions with their codes and hierarchy.

**Response Schema:**

```json
[
  {
    "code": "string",
    "name": "string",
    "level": "string",
    "country_code": "string",
    "country_name": "string",
    "parent_code": "string | null",
    "parent_name": "string | null"
  }
]
```

#### Example Request

```bash
curl "http://thinkhazard.org/en/divisions/search?q=pakistan&level=ADM0"
```

#### Example Response

```json
[
  {
    "code": "PAK",
    "name": "Pakistan",
    "level": "ADM0",
    "country_code": "PAK",
    "country_name": "Pakistan",
    "parent_code": null,
    "parent_name": null
  }
]
```

---

### Get Country List

Retrieve a complete list of all countries (ADM0 level divisions).

```http
GET /divisions/countries
```

#### Response

Returns an array of all countries with their codes.

**Response Schema:**

```json
[
  {
    "code": "string",
    "name": "string",
    "iso2": "string",
    "iso3": "string"
  }
]
```

#### Example Request

```bash
curl http://thinkhazard.org/en/divisions/countries
```

#### Example Response

```json
[
  {
    "code": "AFG",
    "name": "Afghanistan",
    "iso2": "AF",
    "iso3": "AFG"
  },
  {
    "code": "PAK",
    "name": "Pakistan",
    "iso2": "PK",
    "iso3": "PAK"
  }
]
```

---

### Get Subdivisions

Retrieve all subdivisions (states/provinces or districts) for a specific administrative division.

```http
GET /divisions/{parent_code}/subdivisions
```

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `parent_code` | string | Yes | Parent division code (e.g., `PAK` for country, `PAK-PB` for province) |

#### Response

Returns an array of subdivisions within the specified parent division.

**Response Schema:**

```json
[
  {
    "code": "string",
    "name": "string",
    "level": "string"
  }
]
```

#### Example Request

```bash
curl http://thinkhazard.org/en/divisions/AFG/subdivisions
```

#### Example Response

```json
[
  {
    "code": "AFG001",
    "name": "Badakhshan",
    "level": "ADM1"
  },
  {
    "code": "AFG002",
    "name": "Badghis",
    "level": "ADM1"
  },
  {
    "code": "AFG015",
    "name": "Kandahar",
    "level": "ADM1"
  }
]
```

---

### Get Hazard Category Information

Retrieve general information and technical recommendations for a specific hazard type and level combination.

```http
GET /hazardcategory/{hazard_type}/{hazard_level}.json
```

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `hazard_type` | string | Yes | Two-letter hazard code (e.g., `EQ`, `FL`) |
| `hazard_level` | string | Yes | Three-letter hazard level code (e.g., `HIG`, `MED`) |

#### Response

Returns general recommendations and technical guidance for the specified hazard type and level.

**Response Schema:**

```json
{
  "hazard_category": {
    "hazard_type": "string",
    "hazard_level": "string",
    "general_recommendation": "string",
    "technical_recommendations": [
      {
        "text": "string",
        "detail": "string | null"
      }
    ]
  }
}
```

#### Example Request

```bash
curl http://thinkhazard.org/en/hazardcategory/EQ/HIG.json
```

#### Example Response

```json
{
  "hazard_category": {
    "hazard_type": "Earthquake",
    "hazard_level": "High",
    "general_recommendation": "In the area you have selected name of location earthquake hazard is classified as **high** according to the information that is currently available. This means that there is more than a 20% chance of potentially-damaging earthquake shaking in your project area in the next 50 years. Based on this information, the impact of earthquake **must be considered** in all phases of the project, in particular during design and construction. **Project planning decisions, project design, and construction methods should take into account the level of earthquake hazard**. Further detailed information should be obtained to adequately account for the level of hazard.",
    "technical_recommendations": [
      {
        "text": "Consider the effect that collapse (or destruction) or serious damage to buildings and infrastructure associated with the planned project could have on the local population and environment.",
        "detail": null
      }
    ]
  }
}
```

## Query Builder

To find administrative division codes or urban area codes for API requests, use the interactive Query Builder tool:

**[→ Open Query Builder](/query_builder.html)**

The Query Builder provides:
- **Two search modes:** Administrative Divisions and Urban Areas
- Real-time search across 43,202 administrative divisions + 2,919 urban areas
- Search by name, code, or full hierarchical path
- Instant API endpoint generation for each location
- Copy-paste ready URLs for all hazard types

### Alternative: Direct JSON Access

For programmatic access, download the complete data:
- **[divisions_flat.json](/divisions_flat.json)** - All 43,202 administrative divisions (12 MB)
- **[urban_areas.json](/urban_areas.json)** - All 2,919 urban areas (143 KB)
- **[countries.json](/countries.json)** - Countries only (27 KB)

## Support

For questions or issues with the API, please visit the [ThinkHazard! GitHub repository](https://github.com/GFDRR/thinkhazard).


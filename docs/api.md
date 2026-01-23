# API Documentation

## Extracting and re-using content

The ThinkHazard! APIs enable the extraction of hazard levels, recommendations, further information and contacts, into json files for re-use in other tools.

## Reference

* Division codes: [ADM0](https://github.com/GFDRR/thinkhazardmethods/blob/master/source/download/ADM0_TH.csv) [ADM1](https://github.com/GFDRR/thinkhazardmethods/blob/master/source/download/ADM1_TH.csv) [ADM2](https://github.com/GFDRR/thinkhazardmethods/blob/master/source/download/ADM2_TH.csv)
* **Hazard type**: EQ = EarthQuake; VO = Vocalno; TS = Tsunami; CY = Cyclones; FL = Floods; UF = Urban Floods; CF = Coastal Floods; LS = Landslides; EH = Extreme Heat; WF = WildFires; DR = Drought
* **Hazard level**: LOW = Low; VLO = Very Low; MED = Medium; HIG = High

## List of hazard types and levels for a division

**GET** `/report/{division_code}.json`

To download all hazards ranks for one Administrative unit as json, use only the division code.

Example for Pakistan:

* ADM0 (Pakistan): <http://thinkhazard.org/en/report/188.json>
* ADM2 (Kandahar district): <http://thinkhazard.org/en/report/3598.json>

Returns the levels for all the hazard types for a division, e.g.

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
  ...
]
```

## Complete report for a division for a hazard type

**GET** `/report/{division_code}/{hazard_type}.json`

To download the full information for a specific hazard whithin the desired unit, including the ranking and the text description, use the hazard code after the unit code, e.g. for floods in Pakistan:

* <http://thinkhazard.org/en/report/188/FL.json>

Returns the report for a division and a hazard type. Information includes: Data source, Hazard category and description, Recommendations and climate change statement, List of further resources, and Contact Information.

```json
{
  "sources": [
    {
      "detail_url": "http://45.55.174.20/layers/hazard%3Ainunmask_world_stream_6tthres_2_t_50",
      "id": "FL-GLOBAL-GLOFRIS",
      "owner_organization": "GLOFRIS"
    },
    ...
  ],
  "contacts": [
    {
      "url": "http://drmkc.jrc.ec.europa.eu/#news/432/list",
      "phone": "",
      "name": "Disaster Risk Management Knowledge Centre (DRMKC)",
      "email": "drmkc@jrc.ec.europa.eu "
    },
    ...
  ],
  "recommendations": [
    {
      "text": "Find out if the exact project location is in a hazardous zone by using local data, e.g. by collecting local information either from river flood hazard maps, by interviewing local governmental organizations, or by hiring international expertise.",
      "detail": null
    },
    ...
  ],
  "hazard_category": {
    "general_recommendation": "In the area you have selected name of location river flood hazard is classified as **high** according to the information that is currently available to this tool. This means that there is a chance of more than 10% that potentially damaging and life-threatening floods occur in the coming 10 years. **Project planning decisions, project design, and construction methods must take into account the level of river flood hazard**. The following is a list of recommendations that could be followed in different phases of the project to help reduce the risk to your project. Please note that these recommendations are generic and not project-specific.",
    "hazard_level": "High",
    "hazard_type": "River flood"
  },
  "resources": [
    {
      "url": "http://45.55.174.20/documents/162",
      "text": "Cities and Flooding: A Guide to Integrated Urban Flood Risk Management for the 21st Century"
    },
    ...
  ],
  "climate_change_recommendation": "Climate change impacts: Model projections are inconsistent in changes in rainfall."
}
```

## Hazard category

**GET** `/hazardcategory/{hazard_type}/{hazard_level}.json`

Returns the general information for a given hazard type and level.

```json
{
  "hazard_category": {
    "general_recommendation": "In the area you have selected name of location earthquake hazard is classified as **high** according to the information that is currently available. This means that there is more than a 20% chance of potentially-damaging earthquake shaking in your project area in the next 50 years. Based on this information, the impact of earthquake **must be considered** in all phases of the project, in particular during design and construction. **Project planning decisions, project design, and construction methods should take into account the level of earthquake hazard**. Further detailed information should be obtained to adequately account for the level of hazard.",
    "hazard_level": "High",
    "hazard_type": "Earthquake",
    "technical_recommendations": [
      {
        "text": "Consider the effect that collapse (or destruction) or serious damage to buildings and infrastructure associated with the planned project could have on the local population and environment.",
        "detail": null
      },
      ...
    ]
  }
}
```


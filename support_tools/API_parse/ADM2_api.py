import grequests
import pandas as pd
from collections import defaultdict

"""
Instructions:

You will need to install requests, grequests, and pandas if you have not already done so.

conda install -c conda-forge requests grequests pandas

OR 

pip install requests grequests pandas
"""


def parse_response(url, resp, df):
    """Parse JSON response and insert into dataframe."""

    # Because we send the requests asynchronously, results may not
    # be returned in the order we sent it, so we get
    # the country code from the URL
    country_code = int(r.url.rsplit("/",1)[1].split(".")[0])

    row = {}
    for hazard in resp:
        # Hazard type
        haztype = hazard['hazardtype']['mnemonic']

        # Hazard Level
        hazlevel = hazard['hazardlevel']['mnemonic']
        row[haztype] = hazlevel
    # End for

    # Have to loop over columns to ensure values are put in the correct position
    for col in df.columns:
        df.loc[df.index == country_code, col] = row[col]
# End for


target_url = "http://thinkhazard.org/en/report/{}.json"
file_loc = "ADM2_TH.csv"
code_data = pd.read_csv(file_loc, sep=';')

ADM2_codes = code_data['ADM2_CODE'].tolist()
ADM2_urls = [target_url.format(adm_code) for adm_code in ADM2_codes]

# List of things to do asynchronously
url_responses = []
for url in ADM2_urls:
    url_responses.append(grequests.get(url))

# Send out asynchronous requests
responses = grequests.map(url_responses)

result_df = pd.DataFrame(columns=['FL', 'UF', 'CF', 'EQ', 'LS', 'TS', 'VA', 'CY', 'DG', 'EH', 'WF'],
                         index=ADM2_codes)
result_df.index.name = 'country_code'


for r in responses:
    if r.status_code != 200:
        print("Warning! Request for {} failed!".format(r.url))
        continue

    parse_response(url, r.json(), result_df)

# End for

print(result_df)
result_df.to_csv('TH_ADM2_ext.csv', sep=';')

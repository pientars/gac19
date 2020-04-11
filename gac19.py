import datetime as dt
from flask import Flask, render_template
import json
import numpy as np
from os.path import isfile
import pandas as pd
from pandas.io.json import json_normalize
import requests


app = Flask(__name__)

@app.route("/")
def index():

  date = str(dt.date.today())
  daily_cache_file = 'gac19_' + date +'.json'

  if not isfile(daily_cache_file):
    url_states = "https://covidtracking.com/api/v1/states/daily.json"
    r_states = requests.get(url = url_states)
    url_us = "https://covidtracking.com/api/v1/us/daily.json"
    r_us = requests.get(url = url_us)
    filter_data(r_states.json(), r_us.json(), daily_cache_file)

  vis_data = json.load(open(daily_cache_file, 'r'))
  topo_json, county_df = load_county_data()
  return render_template("index.html",
                         vis_data=vis_data,
                         topo_json=topo_json)



def filter_data(state_data, us_data, daily_cache_file ):
  data = { 'pos_plot':[]}
  # Run GA Data
  cols = state_data[0].keys()
  df = pd.DataFrame(state_data, columns=cols)
  ga_df = df[ df['state'] == 'GA' ]
  ga_df_subset = ga_df[ ['date', 'positive', 'negative', 'totalTestResults', 'hospitalized', 'death'] ]

  # Run US data
  us_cols = us_data[0].keys()
  us_df = pd.DataFrame(us_data, columns=us_cols)
  us_df_subset = us_df[ ['date', 'positive', 'negative', 'totalTestResults', 'hospitalized', 'death'] ]
  us_df_subset.rename(columns = {'positive':'positive_us',
                       'negative':'negative_us',
                       'totalTestResults':'totalTestResults_us',
                       'hospitalized':'hospitalized_us',
                       'death':'death_us' },
                      inplace=True)
  merged_df = us_df_subset.merge(ga_df_subset, on='date')

  # Calculate differences
  us_positive_diff = np.zeros(merged_df.shape[0],)
  ga_positive_diff = np.zeros(merged_df.shape[0],)
  # We will be off by one in length, skip that last one.
  us_positive_diff[:-1] = -1 * np.diff(merged_df['positive_us'].to_numpy())
  ga_positive_diff[:-1] = -1 * np.diff(merged_df['positive'].to_numpy())
  merged_df['positive_diff_us'] = us_positive_diff
  merged_df['positive_diff'] = ga_positive_diff


  # Calculate normalized
  # us_pop = 331.002651
  # ga_pop = 10.617423
  # merged_df['positive_us_pop_norm'] = merged_df['positive_us'].map(lambda x: x/us_pop)
  # merged_df['positive_ga_pop_norm'] = merged_df['positive_us'].map(lambda x: x/ga_pop)
  merged_df.fillna('NaN', inplace=True)

  final_data = {'us':[], 'ga':[]}
  for index, row in merged_df.iterrows():
    final_data['us'].append({'date':int(row['date']),
                             'positive':row['positive_us'],
                             'negative':row['negative_us'],
                             'tested':row['totalTestResults_us'],
                             'hospitalized':row['hospitalized_us'],
                             'death':row['death_us'],
                             'positive_diff':row['positive_diff_us']})

    final_data['ga'].append({'date':int(row['date']),
                             'positive':row['positive'],
                             'negative':row['negative'],
                             'tested':row['totalTestResults'],
                             'hospitalized':row['hospitalized'],
                             'death':row['death'],
                             'positive_diff':row['positive_diff']})


  # Cache file
  json.dump(final_data, open(daily_cache_file, 'w'))

def load_county_data():
  county_df = pd.read_csv('data/ga_county_data.csv')
  # print(county_df)
  # topo_json = json.load(open('data/counties-albers-10m.json'))
  topo_json = json.load(open('data/counties-10m.json'))
  # topo_json = json.load(open('data/raw_us.json'))
  # print(topo_json['objects'])

  return topo_json, county_df



if __name__ == "__main__":
    app.run(debug=True)

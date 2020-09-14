import datetime as dt
from flask import Flask, render_template
import io
import json
import numpy as np
from os.path import isfile
import pandas as pd
import pickle
from pandas.io.json import json_normalize
import requests


app = Flask(__name__)

@app.route("/")
def index():

  date = str(dt.date.today())
  daily_cache_file = "data/gac19_" + date +".json"

  if not isfile(daily_cache_file):
    url_states = "https://covidtracking.com/api/v1/states/daily.json"
    r_states = requests.get(url = url_states)
    url_us = "https://covidtracking.com/api/v1/us/daily.json"
    r_us = requests.get(url = url_us)
    filter_data(r_states.json(), r_us.json(), daily_cache_file)

  vis_data = json.load(open(daily_cache_file, "r"))
  topo_json, ga_county_json = load_county_data()
  return render_template("index.html",
                         vis_data=vis_data,
                         county_json=ga_county_json,
                         topo_json=topo_json)


def filter_data(state_data, us_data, daily_cache_file):
  data = { "pos_plot":[]}
  # Run GA Data
  cols = state_data[0].keys()
  df = pd.DataFrame(state_data, columns=cols)
  ga_df = df[ df["state"] == "GA" ]
  ga_df_subset = ga_df[ ["date", "positive", "negative", "totalTestResults", "hospitalized", "death"] ]

  # Run US data
  us_cols = us_data[0].keys()
  us_df = pd.DataFrame(us_data, columns=us_cols)
  us_df_subset = us_df[ ["date", "positive", "negative", "totalTestResults", "hospitalized", "death"] ]
  us_df_subset.rename(columns = {"positive":"positive_us",
                       "negative":"negative_us",
                       "totalTestResults":"totalTestResults_us",
                       "hospitalized":"hospitalized_us",
                       "death":"death_us" },
                      inplace=True)
  merged_df = us_df_subset.merge(ga_df_subset, on="date")

  # Calculate differences
  us_positive_diff = np.zeros(merged_df.shape[0],)
  ga_positive_diff = np.zeros(merged_df.shape[0],)
  ga_death_diff = np.zeros(merged_df.shape[0],)
  ga_hosp_diff = np.zeros(merged_df.shape[0],)
  ga_test_diff = np.zeros(merged_df.shape[0],)
  # We will be off by one in length, skip that last one.
  us_positive_diff[:-1] = np.absolute(np.diff(merged_df["positive_us"].to_numpy()))
  ga_positive_diff[:-1] = np.absolute(np.diff(merged_df["positive"].to_numpy()))
  ga_death_diff[:-1] = np.absolute(np.diff(merged_df["death"].to_numpy()))
  ga_hosp_diff[:-1] = np.absolute(np.diff(merged_df["hospitalized"].to_numpy()))
  ga_test_diff[:-1] = np.absolute(np.diff(merged_df["totalTestResults"].to_numpy()))
  merged_df["positive_diff_us"] = us_positive_diff
  merged_df["positive_diff"] = ga_positive_diff
  merged_df["death_diff"] = ga_death_diff
  merged_df["hospitalized_diff"] = ga_hosp_diff
  merged_df["tested_diff"] = ga_test_diff

  # Calculate rolling averages
  merged_df["positive_diff_us_ma"] = merged_df["positive_diff_us"].iloc[::-1].rolling(window=7).mean().iloc[::-1]
  merged_df["positive_diff_ma"] = merged_df["positive_diff"].iloc[::-1].rolling(window=7).mean().iloc[::-1]
  merged_df["positive_diff_ma_fortnight"] = merged_df["positive_diff"].iloc[::-1].rolling(window=14).mean().iloc[::-1]
  merged_df["death_diff_ma"] = merged_df["death_diff"].iloc[::-1].rolling(window=7).mean().iloc[::-1]
  merged_df["death_diff_ma_fortnight"] = merged_df["death_diff"].iloc[::-1].rolling(window=14).mean().iloc[::-1]
  merged_df["hospitalized_diff_ma"] = merged_df["hospitalized_diff"].iloc[::-1].rolling(window=7).mean().iloc[::-1]
  merged_df["hospitalized_diff_ma_fortnight"] = merged_df["hospitalized_diff"].iloc[::-1].rolling(window=14).mean().iloc[::-1]
  merged_df["tested_diff_ma"] = merged_df["tested_diff"].iloc[::-1].rolling(window=7).mean().iloc[::-1]
  merged_df["tested_diff_ma_fortnight"] = merged_df["tested_diff"].iloc[::-1].rolling(window=14).mean().iloc[::-1]
  # Use string of NaN which we will use in JS for float NaNs
  merged_df.fillna("NaN", inplace=True)

  # Package data into a d3-friendly version
  final_data = {"us":[], "ga":[]}
  for index, row in merged_df.iterrows():
    final_data["us"].append({"date":int(row["date"]),
                             "positive":row["positive_us"],
                             "negative":row["negative_us"],
                             "tested":row["totalTestResults_us"],
                             "hospitalized":row["hospitalized_us"],
                             "death":row["death_us"],
                             "positive_diff":row["positive_diff_us"],
                             "positive_diff_ma":row["positive_diff_us_ma"]})

    final_data["ga"].append({"date":int(row["date"]),
                             "positive":row["positive"],
                             "negative":row["negative"],
                             "tested":row["totalTestResults"],
                             "hospitalized":row["hospitalized"],
                             "death":row["death"],
                             "positive_diff":row["positive_diff"],
                             "positive_diff_ma_fortnight":row["positive_diff_ma_fortnight"],
                             "positive_diff_ma":row["positive_diff_ma"],
                             "death_diff":row["death_diff"],
                             "death_diff_ma_fortnight":row["death_diff_ma_fortnight"],
                             "death_diff_ma":row["death_diff_ma"],
                             "hospitalized_diff":row["hospitalized_diff"],
                             "hospitalized_diff_ma_fortnight":row["hospitalized_diff_ma_fortnight"],
                             "hospitalized_diff_ma":row["hospitalized_diff_ma"],
                             "tested_diff":row["tested_diff"],
                             "tested_diff_ma_fortnight":row["tested_diff_ma_fortnight"],
                             "tested_diff_ma":row["tested_diff_ma"]
                             })

  # Cache file
  json.dump(final_data, open(daily_cache_file, "w"))


def load_county_data():
  date = str(dt.date.today())
  daily_county_cache_file = "data/gac19_county_" + date +".json"
  # Nab newest data from usafacts
  if not isfile(daily_county_cache_file):
    url_counties = "https://usafactsstatic.blob.core.windows.net/public/data/covid-19/covid_confirmed_usafacts.csv"
    r_counties = requests.get(url = url_counties).content
    df_counties = pd.read_csv(io.StringIO(r_counties.decode("utf-8")))
    df_ga = df_counties[ df_counties["State"] == "GA" ]
    ga_max_pos = df_ga.iloc[:, 4:].max(numeric_only=True)
    new_row_dict = ga_max_pos.to_dict()
    new_row_dict['State'] = "GA"
    new_row_dict['stateFIPS'] = 13
    new_row_dict['countyFIPS'] = -1
    new_row_dict['County Name'] = "max"
    df_ga = df_ga.append(new_row_dict, ignore_index=True)
    df_ga.to_json(daily_county_cache_file, orient="records")

  # Load fresh json
  ga_county_json = json.load(open(daily_county_cache_file, 'r'))

  # Load county shape data
  topo_json = json.load(open("data/maps/counties-10m.json"))
  return topo_json, ga_county_json



if __name__ == "__main__":
    app.run(debug=True)

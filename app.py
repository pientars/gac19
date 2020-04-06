import datetime as dt
from flask import Flask, render_template
import json
import pandas as pd
from os.path import isfile
from pandas.io.json import json_normalize
import requests

app = Flask(__name__)

@app.route("/")
def index():


  date = str(dt.date.today())
  daily_cache_file = 'gac19_' + date +'.json'

  if not isfile(daily_cache_file):
    url_states = "https://covidtracking.com/api/v1/states/daily.json?state=GA"
    r_states = requests.get(url = url_states)
    # url_us = "https://covidtracking.com/api/v1/us/daily.json"
    # r_us = requests.get(url = url_us)
    # us_hist_data = r_us.json()
    us_hist_data = []
    filter_data(r_states.json(), [], daily_cache_file)

  vis_data = open(daily_cache_file, 'r').readlines();
  return render_template("index.html", vis_data=vis_data[0])



def filter_data(state_data, us_data, daily_cache_file ):
  data = { 'pos_plot':[]}
  cols = state_data[0].keys()
  df = pd.DataFrame(state_data, columns=cols)
  ga_df = df[ df['state'] == 'GA' ]
  ga_df_subset = ga_df[ ['date', 'positive', 'negative', 'totalTestResults', 'hospitalized', 'death'] ]
  ga_df_subset.to_json(daily_cache_file, orient='records');







if __name__ == "__main__":
    app.run(debug=True)

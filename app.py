from flask import Flask, render_template
import pandas as pd
import requests

app = Flask(__name__)

@app.route("/")
def index():
  # api-endpoint
  URL = "https://covidtracking.com/api/v1/states/daily.json"
  # PARAMS = {'address':location}

  # sending get request and saving the response as response object
  r = requests.get(url = URL)

  # extracting data in json format
  data = r.json()
  print(data)

  return render_template("index.html", data=data)


if __name__ == "__main__":
    app.run(debug=True)

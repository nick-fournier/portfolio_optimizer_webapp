import pandas as pd
import seaborn as sns

import matplotlib.pyplot as plt
from optimizer import prediction
from io import BytesIO
import base64
import datetime

import plotly.express as px
from plotly.offline import plot

pd.options.plotting.backend = "plotly"


def pct_change(close):
    return close.pct_change(1)
    # return 100*(close - close.iloc[0])/close.iloc[0]

def create_plots(plot_data=None):
    if not plot_data:
        plot_data = prediction.get_analysis_data()

    df = plot_data.dropna()

    plots = {}
    # plots['pct_date'] = sns.lineplot(data=df.dropna(), x="date", y="pct_chg", hue="security_id")
    # plots = {k: encode_plot(v) for k, v in plots.items()}

    # plots['pct_date'] = df.plot.scatter(x="date", y="pct_chg")
    plots['pct_date'] = px.scatter(df, x="date", y="pct_chg", color="security_id")

    plots = {k: plot(fig, output_type="div") for k, fig in plots.items()}

    return plots

def encode_plot(plot):
    plot_file = BytesIO()
    plot.figure.savefig(plot_file, format='png')
    encoded_file = base64.b64encode(plot_file.getvalue()).decode('ascii')
    return encoded_file

import pandas as pd

from portfolio_optimizer.optimizer import optimization
from io import BytesIO
import base64

import plotly.express as px
from plotly.offline import plot

pd.options.plotting.backend = "plotly"


def create_plots(plot_data=None):
    if not plot_data:
        plot_data = optimization.get_analysis_data()
    df = plot_data

    plots = {}
    # plots['pct_date'] = sns.lineplot(data=df.dropna(), x="date", y="pct_chg", hue="security_id")
    # plots = {k: encode_plot(v) for k, v in plots.items()}

    # plots['pct_date'] = df.plot.scatter(x="date", y="pct_chg")
    plots['pct_date'] = px.line(df, x="date", y="cum_pct_chg", color="security_id")

    plots = {k: plot(fig, output_type="div") for k, fig in plots.items()}

    return plots

def encode_plot(plot):
    plot_file = BytesIO()
    plot.figure.savefig(plot_file, format='png')
    encoded_file = base64.b64encode(plot_file.getvalue()).decode('ascii')
    return encoded_file

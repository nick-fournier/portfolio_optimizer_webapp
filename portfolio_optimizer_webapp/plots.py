from portfolio_optimizer_webapp.models import Portfolio, SecurityPrice#, Scores
import pandas as pd
from io import BytesIO
import base64

import plotly.express as px
from plotly.offline import plot

pd.options.plotting.backend = "plotly"


def calc_yield():
    pass

def compare_ytd():
    # Get portfolio
    portfolio_qry = Portfolio.objects.filter(allocation__gt=0)
    portfolio_df = pd.DataFrame(portfolio_qry.values('security_id', 'security__symbol', 'allocation'))

    if portfolio_df.empty:
        return

    # Get symbols and IDs 
    symbol_list = portfolio_df.security__symbol.to_list() + ['^GSPC']

    # Get price data
    prices_qry = SecurityPrice.objects.filter(security__symbol__in=symbol_list)
    prices_df = pd.DataFrame(prices_qry.values('security_id', 'security__symbol', 'date', 'close'))

    # calculate yield as % change since t=0
    prices_df.sort_values(['security_id', 'date'], inplace=True)
    prices_df.close = prices_df.close.astype(float)

    prices_grper = prices_df.groupby('security_id', group_keys=False)
    
    prices_df['cum_pct_chg'] = prices_grper.close.apply(lambda x: x.div(x.iloc[0]).subtract(1).mul(100))

    # cast price to wide rows x cols = date x symbol
    prices_wide = prices_df.pivot(index='date', columns='security__symbol', values='cum_pct_chg')

    # The weight vector
    w = portfolio_df.set_index('security__symbol').allocation.astype(float).to_numpy()

    # dot product of yield and weight, sort columns to match the weight vector
    folio_prices = prices_wide[portfolio_df.security__symbol].dot(w)
    assert isinstance(folio_prices, pd.Series)

    # SP500 Index
    SPX_prices = prices_wide['^GSPC']

    # compare df
    compare_df = pd.concat([SPX_prices.to_frame('SP500'), folio_prices.to_frame('portfolio')], axis=1)
    compare_df = compare_df.melt(ignore_index=False)

    fig = px.line(compare_df.reset_index(), x="date", y="value", color="variable")
    fig.layout.yaxis.tickformat = ',.0%'

    return plot(fig, output_type='div')


def get_analysis_data():
    score_cols = ['security_id', 'date', 'security__symbol', 'fiscal_year',
                  'pf_score', 'pf_score_weighted', 'eps', 'pe_ratio', 'roa', 'cash', 'cash_ratio',
                  'delta_cash', 'delta_roa', 'accruals', 'delta_long_lev_ratio',
                  'delta_current_lev_ratio', 'delta_shares', 'delta_gross_margin', 'delta_asset_turnover']

    # financials = models.Fundamentals.objects.all().values('security_id', 'date')
    prices_qry = SecurityPrice.objects.all().values('security_id', 'date', 'close')
    scores_qry = Scores.objects.all().values(*score_cols)

    # As dataframe
    # financials = pd.DataFrame(financials)
    prices = pd.DataFrame(prices_qry)
    df = pd.DataFrame(scores_qry).rename(columns={'security__fundamentals__fiscal_year': 'year'})

    pd.DataFrame(Scores.objects.all().values('security_id', 'date', 'security__fundamentals__fiscal_year'))

    # Aggregate price data annually
    prices.close = prices.close.astype(float)
    prices.date = pd.to_datetime(prices.date)

    col_names = {'date': 'year', 'last': 'yearly_close', 'var': 'variance'}
    prices_year = prices.groupby([prices.date.dt.year, 'security_id']).close\
        .agg(['last', 'mean', 'var']).reset_index()\
        .rename(columns=col_names)

    # Add year and merge prices
    df.date = pd.to_datetime(df.date)
    df.rename(columns={'fiscal_year': 'year'}, inplace=True)
    df = df.merge(prices_year, on=['security_id', 'year'])

    # df.yearly_close = df.yearly_close.astype(float)
    df.pe_ratio = df.pe_ratio.astype(float)
    df = df.sort_values(['security_id', 'date'])

    return df


def create_plots(plot_data=None):
    if not plot_data:
        plot_data = get_analysis_data()
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

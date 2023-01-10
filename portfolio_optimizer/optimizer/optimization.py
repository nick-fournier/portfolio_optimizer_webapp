
"""
 - compare % change in close price versus PF-score of previous year
 This is to see if there's a correlation between price change and score

 - Also compare % change in close price vs % Change in PF-score
 This is to see if there's a correlation between price change and score change

"""

from portfolio_optimizer.webframe import models
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import scipy.stats as stats
from pypfopt.efficient_frontier import EfficientFrontier
from pypfopt.risk_models import CovarianceShrinkage
from pypfopt.discrete_allocation import DiscreteAllocation

def pct_change_from_first(x):
    return (x - x.iloc[0])/x.iloc[0]

def rescore(z, mean, sd):
    return z * sd + mean

def minmax(v):
    return (v - v.min()) / (v.max() - v.min())

def get_analysis_data():
    scores = models.Scores.objects.all().values()
    financials = models.Fundamentals.objects.all().values('security_id', 'date')

    # Merged scores & price
    df = pd.DataFrame(scores).merge(pd.DataFrame(financials), on=['security_id', 'date'])
    df.date = pd.to_datetime(df.date)
    df.yearly_close = df.yearly_close.astype(float)
    df.PE_ratio = df.PE_ratio.astype(float)
    df = df.sort_values(['security_id', 'date'])

    # Grouper
    grps = df.groupby('security_id', group_keys=False)

    # Some quick calcs
    df['order'] = grps.date.rank().astype(int)
    df['pct_chg'] = grps['yearly_close'].apply(lambda x: x.pct_change(1))
    df['cum_pct_chg'] = grps['yearly_close'].apply(pct_change_from_first)

    # df['norm_close'] = df.groupby('security_id', group_keys=False)['yearly_close'].apply(lambda x: minmax(x))

    return df

def forecast_expected_returns(company_df):

    x_cols = ['ROA', 'cash_ratio', 'delta_cash', 'delta_ROA', 'accruals', 'delta_long_lev_ratio',
              'delta_current_lev_ratio', 'delta_shares', 'delta_gross_margin', 'delta_asset_turnover']
    grp_cols = ['security_id']

    company_df.date = pd.to_datetime(company_df.date)
    df = company_df.set_index(['date', 'security_id'])
    df = df[x_cols + ['yearly_close']].fillna(0)

    # Get lagged value of features from t-1
    df['lag_close'] = df.groupby(grp_cols, group_keys=False)['yearly_close'].shift(-1)
    df_t0 = df[df.lag_close.isnull()]
    df = df[~df.lag_close.isnull()]

    # Normalize close price within group since that's company-level feature, all else are high level
    df_grps = df.groupby(grp_cols, group_keys=False)
    df['norm_lag_close'] = df_grps['lag_close'].apply(stats.zscore)
    df[x_cols].apply(stats.zscore)


    # Store mean and std dev for later
    grp_stats = df_grps['lag_close'].agg(mean=np.mean, std=np.std)

    # Assemble matrices
    y = df['norm_lag_close'].to_numpy()
    X = df[x_cols].to_numpy()

    # Estimate model
    model = LinearRegression().fit(X, y)
    print(f'R^2 = {model.score(X, y)}')
    print(pd.Series(list(model.coef_), index=x_cols))

    # Make predictions
    yhat = pd.DataFrame(model.predict(df_t0[x_cols]), index=df_t0.index, columns=['yhat']).join(grp_stats)
    yhat['next_close'] = yhat.apply(lambda row: rescore(row['yhat'], row['mean'], row['std']), axis=1)

    # Calculate returns
    expected_returns = df_t0.join(yhat).apply(lambda x: (x.next_close - x.yearly_close)/x.yearly_close, axis=1)
    expected_returns.name = 'expected_returns'

    return expected_returns


def optimize():
    # Forecast expected returns
    company_df = get_analysis_data()
    expected_returns = forecast_expected_returns(company_df)

    # Some formatting
    prices = models.SecurityPrice.objects.filter(security_id__in=company_df.security_id)
    prices = pd.DataFrame(prices.values('security_id', 'date', 'close'))
    prices.date = pd.to_datetime(prices.date)
    prices.close = prices.close.astype(float)

    # Get price data to wide
    prices_wide = prices.pivot(index='date', columns='security_id', values='close').dropna()

    # Calculate covariance matrix
    prices_cov = CovarianceShrinkage(prices_wide).ledoit_wolf()

    # Optimize efficient frontier of Mean Variance
    ef = EfficientFrontier(np.array(expected_returns), prices_cov)
    # ef.add_objective(objective_functions.L2_reg)  # add a secondary objective

    # Get the allocation weights
    weights = ef.min_volatility()

    # Discrete allocation from portfolio value
    latest_prices = prices.loc[prices.groupby('security_id').date.idxmax()].set_index('security_id')
    disc_allocation, cash = DiscreteAllocation(weights,
                                         latest_prices.close,
                                         total_portfolio_value=10000,
                                         short_ratio=None).greedy_portfolio()

    # Format into dataframe
    df_allocation = pd.concat([
        pd.Series(weights, name='allocation'),
        pd.Series(disc_allocation, name='shares')
    ], axis=1)
    df_allocation.index.name = 'security_id'
    df_allocation.reset_index(inplace=True)
    df_allocation = df_allocation.fillna(0)

    # Send to database
    if not df_allocation.empty:
        if models.Portfolio.objects.exists():
            models.Portfolio.objects.all().delete()
        models.Portfolio.objects.bulk_create(
            models.Portfolio(**vals) for vals in df_allocation.to_dict('records')
        )




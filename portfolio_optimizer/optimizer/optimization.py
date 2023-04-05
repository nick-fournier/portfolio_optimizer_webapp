
"""
 - compare % change in close price versus PF-score of previous year
 This is to see if there's a correlation between price change and score

 - Also compare % change in close price vs % Change in PF-score
 This is to see if there's a correlation between price change and score change

"""

from ..webframe import models
from . import piotroski_fscore
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
    score_cols = ['security_id', 'date', 'security__symbol', 'fiscal_year', 'pf_score',
                  'pf_score_weighted', 'eps', 'pe_ratio', 'roa', 'cash', 'cash_ratio',
                  'delta_cash', 'delta_roa', 'accruals', 'delta_long_lev_ratio',
                  'delta_current_lev_ratio', 'delta_shares', 'delta_gross_margin', 'delta_asset_turnover']

    # financials = models.Fundamentals.objects.all().values('security_id', 'date')
    prices_qry = models.SecurityPrice.objects.all().values('security_id', 'date', 'close')
    scores_qry = models.Scores.objects.all().values(*score_cols)

    # As dataframe
    # financials = pd.DataFrame(financials)
    prices = pd.DataFrame(prices_qry)
    df = pd.DataFrame(scores_qry)

    # update scores
    # pfobject = piotroski_fscore.GetFscore()
    # pfobject.save_scores()

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

class OptimizePorfolio:
    def __init__(self, investment_amount=10000, backcast=False):
        data = get_analysis_data()
        expected_returns = self.forecast_expected_returns(data, backcast)
        self.portfolio = self.optimize(expected_returns, investment_amount)
        # self.save_portfolio()

    def forecast_expected_returns(self, company_df, backcast=False):

        x_cols = ['roa', 'cash_ratio', 'delta_cash', 'delta_roa', 'accruals', 'delta_long_lev_ratio',
                  'delta_current_lev_ratio', 'delta_shares', 'delta_gross_margin', 'delta_asset_turnover']

        model_df = company_df.set_index(['security_id', 'year'])
        model_df = model_df[x_cols + ['yearly_close']].fillna(0)

        # Get lagged value of features from t-1
        model_df['lag_close'] = model_df.groupby('security_id', group_keys=False)['yearly_close'].shift(-1)

        # Normalize close price within group since that's company-level feature, all else are high level
        df_grps = model_df[~model_df.lag_close.isnull()].groupby('security_id', group_keys=False)
        model_df.loc[~model_df.lag_close.isnull(), 'norm_lag_close'] = df_grps['lag_close'].apply(stats.zscore)
        # df_t[x_cols].apply(stats.zscore)

        # Store mean and std dev for later
        grp_stats = df_grps['lag_close'].agg(mean=np.mean, std=np.std)

        # temporary fy column to groupby on easily...
        model_df['fy'] = model_df.index.get_level_values('year')

        # Initalize DF to join to
        i = model_df.fy.min() + 1

        if not backcast:
            i = model_df.fy.max()

        while i <= model_df.fy.max():
            # Model matrix for time<i
            df_t = model_df[model_df.fy < i]
            # Drop any missing years
            df_t = df_t[~df_t.lag_close.isna()]
            # Prediction matrix for time i
            df_t0 = model_df[model_df.fy == i]

            # Assemble matrices
            y = df_t['norm_lag_close'].to_numpy()
            x = df_t[x_cols].astype(float).to_numpy()

            # Estimate model
            model = LinearRegression().fit(x, y)
            print(f'R^2 = {model.score(x, y)}')
            print(pd.Series(list(model.coef_), index=x_cols))

            # Make predictions
            yhat = pd.DataFrame(model.predict(df_t0[x_cols]), index=df_t0.index, columns=['yhat']).join(grp_stats)
            yhat['next_close'] = yhat.apply(lambda row: rescore(row['yhat'], row['mean'], row['std']), axis=1)

            # Calculate returns
            model_df.loc[yhat.index, yhat.columns] = yhat
            i += 1

        # Expected returns as percent change
        expected_returns = model_df.apply(lambda x: (x.next_close - x.yearly_close)/x.yearly_close, axis=1)
        expected_returns.name = 'expected_returns'

        return expected_returns

    def optimize(self, expected_returns, investment_amount=10000):

        # Check type
        investment_amount = float(investment_amount)

        # # Forecast expected returns
        returns_df = expected_returns[~expected_returns.isna()]

        # Some formattingsymbol
        security_ids = returns_df.index.get_level_values('security_id').unique()
        prices = models.SecurityPrice.objects.filter(security_id__in=security_ids)
        prices = pd.DataFrame(prices.values('security_id', 'date', 'close'))
        prices.date = pd.to_datetime(prices.date)
        prices['year'] = prices.date.dt.year
        prices.close = prices.close.astype(float)

        # Get price data to wide
        prices = prices.drop_duplicates()
        prices_wide = {yr: df.pivot(index='date', columns='security_id', values='close').dropna() for yr, df in prices.groupby('year')}
        # prices_wide = prices.pivot(index='date', columns='security_id', values='close').dropna()

        weights_dict = {}
        for year, exp_df in returns_df.groupby(level='year'):

            # Get prices for available stocks
            security_ids = exp_df.index.get_level_values('security_id').unique()
            these_prices = prices_wide[year][security_ids]

            # Calculate covariance matrix
            prices_cov = CovarianceShrinkage(these_prices).ledoit_wolf()

            # Optimize efficient frontier of Mean Variance
            ef = EfficientFrontier(exp_df.to_numpy(), prices_cov)
            # ef.add_objective(objective_functions.L2_reg)  # add a secondary objective

            # Get the allocation weights
            weights_dict[year] = ef.min_volatility()

        # Discrete allocation from portfolio value
        portfolio_year = max(weights_dict.keys())
        latest_weights = weights_dict[portfolio_year]
        # Only do this for current year. Everything prior can be unitless
        latest_prices = prices.loc[prices.groupby('security_id').date.idxmax()].set_index('security_id')
        disc_allocation, cash = DiscreteAllocation(latest_weights,
                                                   latest_prices.close,
                                                   total_portfolio_value=investment_amount,
                                                   short_ratio=None).greedy_portfolio()

        # Format into dataframe
        df_allocation = pd.concat([
            pd.Series(latest_weights, name='allocation'),
            pd.Series(disc_allocation, name='shares')
        ], axis=1)
        df_allocation.index.name = 'security_id'
        df_allocation.reset_index(inplace=True)
        df_allocation = df_allocation.fillna(0)

        # Reindex for all 0% stocks
        all_security_ids = models.SecurityList.objects.all().values_list('pk', flat=True)
        df_allocation = df_allocation.set_index('security_id').reindex(all_security_ids).fillna(0).reset_index()

        # Add allocation year
        df_allocation['year'] = portfolio_year

        return df_allocation
    def save_portfolio(self):
        # Send to database
        if not self.portfolio.empty:
            if models.Portfolio.objects.exists():
                models.Portfolio.objects.all().delete()
            models.Portfolio.objects.bulk_create(
                models.Portfolio(**vals) for vals in self.portfolio.to_dict('records')
            )




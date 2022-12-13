
"""
 - compare % change in close price versus PF-score of previous year
 This is to see if there's a correlation between price change and score

 - Also compare % change in close price vs % Change in PF-score
 This is to see if there's a correlation between price change and score change

"""

import pandas as pd
import seaborn as sns
import numpy as np
from webframe import models
from sklearn.linear_model import LinearRegression
from statsmodels.tsa.api import VAR
import pandas as pd
import numpy as np
import plotly.express as px
from sklearn.linear_model import LinearRegression
from statsmodels.tsa.api import VAR
from optimizer import prediction
import scipy.stats as stats

def rescore(z, mean, sd):
    return z * sd + mean

def minmax(v):
    return (v - v.min()) / (v.max() - v.min())

def get_analysis_data():
    scores = models.Scores.objects.all().values()
    financials = models.Financials.objects.all().values('security_id', 'date')

    # Merged scores & price
    df = pd.DataFrame(scores).merge(pd.DataFrame(financials), on=['security_id', 'date'])
    df.date = pd.to_datetime(df.date)
    df.yearly_close = df.yearly_close.astype(float)
    df.PE_ratio = df.PE_ratio.astype(float)
    df = df.sort_values(['security_id', 'date'])
    df['order'] = df.groupby('security_id').date.rank().astype(int)
    df['pct_chg'] = df.groupby('security_id', group_keys=False)['yearly_close'].apply(lambda x: x.pct_change(1))

    # df['norm_close'] = df.groupby('security_id', group_keys=False)['yearly_close'].apply(lambda x: minmax(x))

    return df

def expected_returns():
    df = get_analysis_data()

    x_cols = ['ROA', 'cash_ratio', 'delta_cash', 'delta_ROA', 'accruals', 'delta_long_lev_ratio',
              'delta_current_lev_ratio', 'delta_shares', 'delta_gross_margin', 'delta_asset_turnover']
    grp_cols = ['security_id']

    # df.date = pd.to_datetime(df.date).dt.year
    df.date = pd.to_datetime(df.date)
    df = df.set_index(['date', 'security_id'])

    # Get lagged value of fefatures from t-1
    df['lag_close'] = df.groupby(grp_cols, group_keys=False)['yearly_close'].shift(-1)
    df_t0 = df[df.lag_close.isnull()]
    df.dropna(inplace=True)

    # Normalize close price within group since that's company-level feature, all else are high level
    df_grps = df.groupby(grp_cols, group_keys=False)
    df['norm_lag_close'] = df_grps['lag_close'].apply(stats.zscore)
    df[x_cols] = df[x_cols].apply(stats.zscore, axis=0)

    # Store mean and std dev for later
    grp_stats = df_grps['lag_close'].agg(mean=np.mean, std=np.std)

    # Assemble matrices
    y = df['norm_lag_close'].to_numpy()
    X = df[x_cols].to_numpy()

    # Estimate model
    model = LinearRegression().fit(X, y)
    print(f'R^2 = {model.score(X, y)}')

    # Make predictions
    yhat = pd.DataFrame(model.predict(df_t0[x_cols]), index=df_t0.index, columns=['yhat']).join(grp_stats)
    yhat['next_close'] = yhat.apply(lambda row: rescore(row['yhat'], row['mean'], row['std']), axis=1)

    # Calculate returns
    exp_returns = df_t0.join(yhat).apply(lambda x: (x.next_close - x.yearly_close)/x.yearly_close, axis=1)
    exp_returns.name = 'expected_returns'

    return exp_returns


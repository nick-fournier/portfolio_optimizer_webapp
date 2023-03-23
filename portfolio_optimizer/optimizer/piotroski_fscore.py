from ..webframe import models
from django.db.models import Q

import pandas as pd
import numpy as np


### Profitability
# ROA = Net Income / Total Assets
# Operating Cash Flow = Total Cash From Operating Activities |cash
# Change in ROA = Delta ROA
# Accruals = (Total Assets - Cash) - (Total Liab - Total Debt)
### Leverage, Liquidity and Source of Funds
# Change in long term leverage = delta Total Liab / Total Assets
# Change in current lev = delta Total Current Liabilities / Total Current Assets
# Change in shares = delta Common Stock
### Operating Efficiency
# Change in Gross Margin = delta Gross Profit / Total Revenue
# Change in Asset Turnover Ratio = delta Total Revenue / (Beginning Total Assets + Ending Total Assets)/2)

### EPS & P/E ratio
# EPS = (Net Income - Preferred Dividends) / Common Stock
# P/E = Price / EPS

def calc_delta(series, as_percent = False):
    delta = series - series.shift(-1)
    if as_percent:
        delta /= series.shift(-1)

    return delta

def calc_pf_score(df, weighted=False):

    # 1 point if positive
    pos_cols = ['roa', 'delta_cash', 'delta_roa', 'accruals',
                'delta_current_lev_ratio', 'delta_gross_margin', 'delta_asset_turnover']

    # 1 point if negative
    neg_cols = ['delta_long_lev_ratio']

    # 1 point if less than or equal to 0
    leq_cols = ['delta_shares']

    # Sum up the score
    scores = pd.concat([df[pos_cols] > 0, df[neg_cols] < 0, df[leq_cols] <= 0], axis=1).astype(int)

    if weighted:
        weights = df[pos_cols + neg_cols + leq_cols].abs() + 1
        scores = scores * weights

    # Set first date as NA because there is no previous to calc delta on
    scores = scores.sum(axis=1)

    return scores

class GetFscore:

    def __init__(self, fundamentals_df=None):

        if fundamentals_df is None and models.Fundamentals.objects.exists():
            self.data = self.get_data()
        else:
            self.data = fundamentals_df

        self.scores = self.calc_scores()
        # self.save_scores()

    def get_data(self):
        data = pd.DataFrame(models.Fundamentals.objects.all().values()).drop(columns='id')
        float_cols = list(set(data.columns).difference(['security_id', 'date']))
        data[float_cols] = data[float_cols].astype(float)

        return data

    def calc_scores(self):
        df_measures = []

        for _, df in self.data.groupby('security_id'):
            df = df.sort_values('date', ascending=False)

            # Initialize clean dataframe to build on
            measures = pd.DataFrame(df[['security_id', 'date']])

            ### Profitability ###
            # ROA = Net Income / Total Assets | 1 if positive
            measures['roa'] = df['net_income'] / df['current_assets']
            # Cash Flow | 1 if positive
            measures['delta_cash'] = calc_delta(df['cash'], as_percent=True)
            # Change in ROA | 1 if positive (greater than last year)
            measures['delta_roa'] = calc_delta(df['net_income'] / df['current_assets'])
            # Accruals | Score 1 if CFROA > ROA
            measures['accruals'] = df['cash'] / df['current_assets']

            ### Leverage, Liquidity and Source of Funds ###
            # Long term leverage ratio | 1 if negative (lower than last year)
            measures['delta_long_lev_ratio'] = calc_delta(df['total_liabilities'] / df['total_assets'])
            # Current leverage ratio | 1 point if positive (higher than last year)
            measures['delta_current_lev_ratio'] = calc_delta(
                df['current_liabilities'] / df['current_assets']
            )
            # Change in shares | 1 if no no shares (<=0)
            measures['delta_shares'] = calc_delta(df['shares_outstanding'], as_percent=True)

            ### Operating Efficiency ###
            # Gross margin | 1 if positive (higher than last year)
            measures['delta_gross_margin'] = calc_delta(df['gross_profit'] / df['total_revenue'])
            # Asset turnover | 1 if positive (higher than last year)
            measures['delta_asset_turnover'] = calc_delta(
                (df['total_revenue'] / (df['total_assets'] + df['total_assets'].shift(-1)) / 2)
            )

            ### Other metrics ###
            measures['cash'] = df['cash']
            measures['cash_ratio'] = df['cash'] / df['current_liabilities']
            measures['eps'] = df['net_income_common_stockholders'] / df['shares_outstanding']

            # TODO will need to update these after prices are downloaded for select stocks
            # # Get close price and PE
            # prices = models.SecurityPrice.objects.filter(security_id__in=measures.security_id)
            # prices = pd.DataFrame(prices.values('date', 'security_id', 'close'))
            # prices = prices.rename(columns={'close': 'yearly_close'})
            # prices.yearly_close = prices.yearly_close.astype(float)
            #
            # # Calc variance
            # prices.index = pd.to_datetime(prices.date).dt.year
            # var = prices.groupby(level=0).yearly_close.std()**2
            # var = var.reset_index().rename(columns={'yearly_close': 'yearly_variance'}).set_index('date')
            # prices = prices.join(var).reset_index(drop=True)
            # measures = measures.merge(prices, on=['security_id', 'date'], how='left')
            #
            # # calc PE
            # measures['PE_ratio'] = measures['yearly_close'] / measures['EPS']

            # add to list
            df_measures.append(measures)

        # Concat into df
        df_measures = pd.concat(df_measures, axis=0).fillna(np.nan)

        # Calculate PF Score
        df_measures['pf_score'] = calc_pf_score(df_measures, weighted=False)
        df_measures['pf_score_weighted'] = calc_pf_score(df_measures, weighted=True)

        # old_date = df.date
        # df.date = pd.to_datetime(df.date)
        # scores.iloc[df.groupby('security_id').date.idxmin()] = 0
        # df.date = old_date

        # Final cleanup
        df_measures.replace([-np.inf, np.inf], np.nan, inplace=True)

        return df_measures

    def save_scores(self):
        rnd_cols = list(set(self.scores.columns).difference(['security_id', 'date', 'pf_score', 'cash']))
        new_scores = self.scores
        new_scores[rnd_cols] = new_scores[rnd_cols].astype(float).round(6)
        new_scores['cash'] = new_scores['cash']
        new_scores['pf_score'] = new_scores['pf_score'].astype(int)
        new_scores = new_scores.replace([np.NaN, np.inf, -np.inf], None)

        # Check for existing scores in DB
        old_scores = models.Scores.objects.filter(
                Q(security_id__in=new_scores['security_id']) &
                Q(date__in=new_scores['date'])
            ).values('id', 'security_id', 'date')

        if old_scores.exists():
            old_scores = pd.DataFrame(old_scores).merge(
                new_scores, on=['security_id', 'date']
            )

            new_scores = new_scores[
                ~(new_scores.date.isin(old_scores.date) &
                  new_scores.security_id.isin(old_scores.security_id))
                ]

            old_scores = old_scores.to_dict('records')

            # Grab the actual queryset to preserve pk
            old_scores_update = []
            for score in old_scores:
                score_set = models.Scores.objects.get(id=score['id'])
                for k, v in score.items():
                    setattr(score_set, k, v)
                old_scores_update.append(score_set)

            models.Scores.objects.bulk_update(
                old_scores_update,
                #old_scores.to_dict('records'),
                fields=list(new_scores.columns)
            )

        models.Scores.objects.bulk_create(
            models.Scores(**vals) for vals in new_scores.to_dict('records')
        )


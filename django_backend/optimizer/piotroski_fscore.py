from webframe.models import Financials, BalanceSheet, Scores
from django.db.models import Q

import pandas as pd
import numpy as np
from datetime import date

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

def calc_delta(series):
    return (series - series.shift(-1)) / series.shift(-1)

def calc_ratio(numer, denom):
    return numer / denom

def PF_score(row):
    pos_cols = ['ROA', 'cash', 'delta_ROA', 'accruals',
                'delta_current_lev_ratio', 'delta_gross_margin', 'delta_asset_turnover']
    neg_cols = ['delta_long_lev_ratio']
    leq_cols = ['delta_shares']

    oriented = pd.concat([row[pos_cols], -1 * row[neg_cols]])
    oriented = oriented.dropna()

    # 1 if > 0 and 1 if >= 0
    score = sum([1 for x in oriented if x > 0])
    if row[leq_cols].item() <= 0:
        score += 1

    return score

def PF_score_weighted(row):
    pos_cols = ['ROA', 'delta_cash', 'delta_ROA', 'accruals',
                'delta_current_lev_ratio', 'delta_gross_margin', 'delta_asset_turnover']
    neg_cols = ['delta_long_lev_ratio']
    leq_cols = ['delta_shares']

    oriented = pd.concat([row[pos_cols], -1 * row[neg_cols]])
    oriented = oriented.dropna()
    score_weighted = sum([(1 + x) for x in list(oriented + row[leq_cols].item()) if x > 0])

    return score_weighted

class GetFscore:

    def __init__(self):
        if Financials.objects.exists() and BalanceSheet.objects.exists():
            self.year = date.today().year
            self.data = self.get_data()
            self.scores = self.calc_scores()
            self.save_scores()

    def get_data(self):
        financials = pd.DataFrame(Financials.objects.all().values()).drop(columns='id')
        balancesheet = pd.DataFrame(BalanceSheet.objects.all().values()).drop(columns='id')
        data = balancesheet.merge(financials, on=['date', 'security_id'])
        float_cols = list(set(data.columns).difference(['security_id', 'date']))
        data[float_cols] = data[float_cols].astype(float)

        return data

    def calc_scores(self):
        df_measures = []
        for x in self.data.security_id.unique():
            df = self.data.loc[self.data.security_id == x]

            # Calc the criteria metrics
            measures = pd.DataFrame(df[['security_id', 'date']])
            measures['ROA'] = df['net_income'] / df['total_current_assets']
            measures['cash'] = df['cash']
            # measures['cash_ratio'] = df['cash'] / df['total_current_liabilities']
            measures['delta_cash'] = calc_delta(df['cash'])
            measures['delta_ROA'] = calc_delta(df['net_income'] / df['total_current_assets'])
            measures['accruals'] = df['cash'] / df['total_current_assets']
            measures['delta_long_lev_ratio'] = calc_delta(df['total_liab'] / df['total_assets'])
            measures['delta_current_lev_ratio'] = calc_delta(
                df['total_current_liabilities'] / df['total_current_assets']
            )
            measures['delta_shares'] = calc_delta(df['common_stock'])
            measures['delta_gross_margin'] = calc_delta(df['gross_profit'] / df['total_revenue'])
            measures['delta_asset_turnover'] = calc_delta(
                (df['total_revenue'] / (df['total_assets'] + df['total_assets'].shift(-1))/2)
            )
            measures['EPS'] = df['net_income'] / df['common_stock']
            measures['PE_ratio'] = df['quarterly_close'] / (df['net_income'] / df['common_stock'])

            df_measures.append(measures)

        df_measures = pd.concat(df_measures, axis=0)

        # Fill Nones
        df_measures = df_measures.fillna(np.nan)
        df_measures['PF_score'] = df_measures.apply(PF_score, axis=1)
        df_measures['PF_score_weighted'] = df_measures.apply(PF_score_weighted, axis=1)

        return df_measures

    def save_scores(self):
        rnd_cols = list(set(self.scores.columns).difference(['security_id', 'date', 'PF_score', 'cash']))
        scores_formatted = self.scores
        scores_formatted[rnd_cols] = scores_formatted[rnd_cols].astype(float).round(6)
        scores_formatted['cash'] = scores_formatted['cash']#/1e6
        scores_formatted['PF_score'] = scores_formatted['PF_score'].astype(int)
        scores_formatted = scores_formatted.replace([np.NaN, np.inf, -np.inf], None)

        df_template = pd.DataFrame(columns=['security_id', 'date'])
        old_scores = pd.DataFrame(
            Scores.objects.filter(
                Q(security_id__in=scores_formatted['security_id']) & Q(date__in=scores_formatted['date'])
            ).values('security_id', 'date')
        )

        old_scores = pd.concat([df_template, old_scores], axis=0)

        new_scores = scores_formatted[~(scores_formatted.date.isin(old_scores.date) &
                                        scores_formatted.security_id.isin(old_scores.security_id))]

        if not new_scores.empty:
            Scores.objects.bulk_create(
                Scores(**vals) for vals in new_scores.to_dict('records')
            )

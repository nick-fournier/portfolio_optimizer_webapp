from .models import Financials, BalanceSheet, Scores
from django.db.models import Q

import pandas as pd
import numpy as np
from datetime import date

class GetFscore:

    def __init__(self):
        self.year = date.today().year
        self.data = self.get_data()
        self.scores = self.calc_scores()
        self.save_scores()

    def calc_delta(self, series):
        return (series - series.shift(-1)) / series.shift(-1)

    def calc_ratio(self, numer, denom):
        return numer / denom

    def PF_score(self, row):
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
        # if not math.isnan(row[leq_cols].item()):
        #     if row[leq_cols].item() <= 0:
        #         score += 1

        return score

    def PF_score_weighted(self, row):
        cols = ['ROA', 'delta_cash', 'delta_ROA', 'accruals',
                'delta_current_lev_ratio', 'delta_gross_margin', 'delta_asset_turnover']
        inv_cols = ['delta_long_lev_ratio', 'delta_shares']

        scores = [(1 + x) for x in list(row[inv_cols].dropna() * -1) + list(row[cols].dropna())]
        # scores = list(row[inv_cols].dropna() * -1) + list(row[cols].dropna())
        return sum(scores)

    def get_data(self):
        financials = pd.DataFrame(list(Financials.objects.all().values(
            'security_id', 'date', 'gross_profit', 'total_revenue', 'net_income'
        )))
        balancesheet = pd.DataFrame(list(BalanceSheet.objects.all().values(
            'security_id', 'date', 'total_current_assets', 'total_assets',
            'total_current_liabilities', 'total_liab', 'cash', 'common_stock'
        )))
        data = balancesheet.merge(financials, on=['date', 'security_id'])
        flt_cols = list(set(data.columns).difference(['security_id', 'date']))
        data[flt_cols] = data[flt_cols].astype(float)

        return data

    def calc_measures(self):
        df_measures = pd.DataFrame()
        for x in self.data.security_id.unique():
            df = self.data.loc[self.data.security_id == x]
            # Calc the criteria metrics
            measures = pd.DataFrame(df[['security_id', 'date']])
            measures['ROA'] = df['net_income'] / df['total_current_assets']
            measures['cash'] = df['cash']
            # measures['cash_ratio'] = df['cash'] / df['total_current_liabilities']
            measures['delta_cash'] = self.calc_delta(df['cash'])
            measures['delta_ROA'] = self.calc_delta(df['net_income'] / df['total_current_assets'])
            measures['accruals'] = df['cash'] / df['total_current_assets']
            measures['delta_long_lev_ratio'] = self.calc_delta(df['total_liab'] / df['total_assets'])
            measures['delta_current_lev_ratio'] = self.calc_delta(
                df['total_current_liabilities'] / df['total_current_assets']
            )
            measures['delta_shares'] = self.calc_delta(df['common_stock'])
            measures['delta_gross_margin'] = self.calc_delta(df['gross_profit'] / df['total_revenue'])
            measures['delta_asset_turnover'] = self.calc_delta(
                (df['total_revenue'] / (df['total_assets'] + df['total_assets'].shift(-1))/2)
            )
            df_measures = df_measures.append(measures)

        # Fill Nones
        df_measures = df_measures.fillna(np.nan)

        return df_measures

    def calc_scores(self):
        measures = self.calc_measures()
        measures['PF_score'] = measures.apply(self.PF_score, axis=1)
        measures['PF_score_weighted'] = measures.apply(self.PF_score_weighted, axis=1)
        return measures

    def save_scores(self):

        rnd_cols = list(set(self.scores.columns).difference(['security_id', 'date', 'PF_score', 'cash']))

        scores_formatted = self.scores
        scores_formatted[rnd_cols] = scores_formatted[rnd_cols].astype(float).round(6)
        scores_formatted['cash'] = scores_formatted['cash']/1e6
        scores_formatted['PF_score'] = scores_formatted['PF_score'].astype(int)
        scores_formatted = scores_formatted.replace({np.NaN: None})

        old_scores = pd.DataFrame(columns=['security_id', 'date'])
        old_scores = old_scores.append(
            pd.DataFrame(
                Scores.objects.filter(
                    Q(security_id__in=scores_formatted['security_id']) & Q(date__in=scores_formatted['date'])
                ).values('security_id', 'date')
            )
        )

        new_scores = scores_formatted[~(scores_formatted.date.isin(old_scores.date) &
                                        scores_formatted.security_id.isin(old_scores.security_id))]
        if not new_scores.empty:
            Scores.objects.bulk_create(
                Scores(**vals) for vals in new_scores.to_dict('records')
            )

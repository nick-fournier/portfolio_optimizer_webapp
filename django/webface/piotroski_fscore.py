from .models import Financials, BalanceSheet, Scores

import pandas as pd
import math
from datetime import date

class GetFscore:

    def __init__(self):
        self.year = date.today().year
        self.data = self.get_data()
        self.scores = self.calc_scores()

    def calc_delta(self, series):
        return (series - series.shift(-1)) / series.shift(-1)

    def calc_ratio(self, numer, denom):
        return numer / denom

    def PF_score(self, row):
        pos_cols = ['ROA', 'cash', 'delta_ROA', 'accruals',
                    'delta_current_lev_ratio', 'delta_gross_margin', 'delta_asset_turnover']
        neg_cols = ['delta_long_lev_ratio']
        leq_cols = ['delta_shares']

        print(type(row))
        oriented = pd.concat([row[pos_cols], -1 * row[neg_cols]])
        oriented = oriented.dropna()

        print(oriented)
        score = sum([1 for x in oriented if x > 0])
        if not math.isnan(row[leq_cols].item()):
            if row[leq_cols].item() >= 0:
                score += 1

        print(score)

        return score

    def PF_score_weighted(self, row):
        cols = ['ROA', 'cash_ratio', 'delta_ROA', 'accruals',
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
        return balancesheet.merge(financials, on=['date', 'security_id'])

    def calc_measures(self):
        df_measures = pd.DataFrame()
        for x in self.data.security_id.unique():
            df = self.data.loc[self.data.security_id == x]
            # Calc the criteria metrics
            measures = pd.DataFrame(df[['security_id', 'date']])
            measures['ROA'] = df['net_income'] / df['total_current_assets']
            measures['cash'] = df['cash']
            measures['cash_ratio'] = df['cash'] / df['total_current_liabilities']
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

        # round off excess
        # df_measures = df_measures.round(6)
        return df_measures

    def calc_scores(self):
        measures = self.calc_measures()
        measures['PF_score'] = measures.apply(self.PF_score, axis=1)
        measures['PF_score_weighted'] = measures.apply(self.PF_score_weighted, axis=1)
        return measures

    def save_scores(self):
        Scores.objects.bulk_create(
            Scores(**vals) for vals in self.scores.to_dict('records')
        )
        # security_id = {'security_id': security_id}
        # Database.objects.bulk_create(
        #     Database(**{**security_id, **vals}) for vals in data.to_dict('records')
        # )


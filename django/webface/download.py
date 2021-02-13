from django.apps import apps
from .models import DataSettings, SecurityMeta, Financials, BalanceSheet, Dividends, SecurityPrice
from django.db.models import Q

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import date


def date_query(date_list):
    dlist = [d.strftime('%Y-%m-%d') for d in date_list]
    query = ""
    for val in dlist:
        if (query == ""):
            query = Q(date__range=val)
        else:
            query |= Q(date__range=val)
    return query

def date_range(date_list):
    min = date_list.min()
    max = date_list.max()
    return [d.strftime('%Y-%m-%d') for d in [min, max]]

class DownloadData:

    def __init__(self, tickers, get_prices=False):
        self.start_date = DataSettings.objects.first().start_date
        self.end_date = date.today().strftime("%Y-%m-%d")
        self.get_prices = get_prices
        self.DB_ref = {'financials': Financials,
                       'balancesheet': BalanceSheet,
                       'dividends': Dividends,
                       'prices': SecurityPrice}

        # Get field names from model, remove related model names
        meta_fields = [field.name for field in SecurityMeta._meta.get_fields()]
        self.meta_fields = [x for x in meta_fields if x not in list(apps.all_models['webface'].keys()) + ['id']]

        self.existing_ids = pd.DataFrame(columns=['security_id', 'symbol'])
        self.existing_ids = self.existing_ids.append(pd.DataFrame(
            SecurityMeta.objects.filter(symbol__in=tickers).values('id', 'symbol')
        ).rename(columns={'id': 'security_id'}))

        # Get existing symbols, remove existing from list
        self.all_tickers = tickers
        self.new_tickers = list(set(tickers).difference(self.existing_ids['symbol']))

        # if not empty, get data
        if self.all_tickers:
            self.get_data()

        # If any new, add to meta data
        if self.new_tickers:
            self.set_meta()

        # Add the data
        for key in ['financials', 'balancesheet', 'dividends']:
            self.set_data(db_name=key)
        if self.get_prices:
            self.set_data(db_name='prices')


    def get_data(self):
        # Get data for securities, and add prices to data
        self.stock_data = {t: yf.Ticker(t) for t in self.all_tickers}
        # Get price data if requested
        if self.get_prices:
            prices = yf.download(self.all_tickers,
                                 group_by='ticker',
                                 start=self.start_date,
                                 end=self.end_date)
            # Convert to multilevel if single ticker
            if len(self.all_tickers) == 1:
                midx = tuple((self.all_tickers[0], x) for x in prices.columns)
                prices.columns = pd.MultiIndex.from_tuples(midx)

            # Attach to the stock_data
            for t in self.all_tickers:
                self.stock_data[t].prices = prices[t]

    def set_meta(self):
        renames = {'longbusinesssummary': 'business_summary',
                   'fulltimeemployees': 'fulltime_employees'}

        # Get NEW meta data into data frame
        meta = pd.DataFrame([self.stock_data[x].info for x in self.new_tickers])

        meta.columns = [x.lower().replace(' ', '_') for x in meta.columns]
        meta.columns = [renames[x] if x in renames.keys() else x for x in meta.columns]

        # # Add Null to any missing
        for field in meta.columns:
            if field not in meta.keys():
                meta[field] = None

        # Subset select columns & add security id
        meta = meta.loc[:, self.meta_fields]
        meta['fulltime_employees'] = meta['fulltime_employees'].fillna(-1)
        meta['fulltime_employees'] = meta['fulltime_employees'].astype(int)
        meta['fulltime_employees'] = meta['fulltime_employees'].replace({-1: None})

        if not meta.empty:
            SecurityMeta.objects.bulk_create(
                SecurityMeta(**vals) for vals in meta.to_dict('records')
            )


    def set_data(self, db_name):
        Database = self.DB_ref[db_name]
        data = pd.DataFrame()
        for t in self.all_tickers:
            if db_name in ['financials', 'balancesheet']:
                df = getattr(self.stock_data[t], db_name).T.reset_index().rename(columns={"": "date"})
            else:
                df = getattr(self.stock_data[t], db_name).reset_index().dropna()
            df['security_id'] = int(self.existing_ids.loc[self.existing_ids['symbol'] == t, 'security_id'])
            data = data.append(df)
        # data = data.fillna(value=np.nan)

        # Column names to lowercase
        data.columns = [x.lower().replace(' ', '_') for x in data.columns]

        old_data = pd.DataFrame(columns=['security_id', 'date'])
        old_data = old_data.append(
            pd.DataFrame(
                Database.objects.filter(
                    Q(security_id__in=data['security_id']) & Q(date__in=data['date'])
                ).values('security_id', 'date')
            )
        )

        new_data = data[~(data.date.isin(old_data.date) & data.security_id.isin(old_data.security_id))]
        if not new_data.empty:
            Database.objects.bulk_create(
                Database(**vals) for vals in new_data.to_dict('records')
            )
        # # Update existing entries
        # if len(old_ids) > 0:
        #     for vals in data[data['security_id'].isin(old_ids)].to_dict('records'):
        #         Database.objects.bulk_update(
        #             Existing(**vals),
        #             vals.keys()
        #         )
        # # Create new entries
        # Database.objects.bulk_create(
        #     Database(**vals) for vals in data[~data['security_id'].isin(old_ids)].to_dict('records')
        # )

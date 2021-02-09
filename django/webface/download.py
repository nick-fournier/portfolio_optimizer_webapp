from django.apps import apps
from .models import DataSettings, SecurityMeta, Financials, BalanceSheet, Dividends, SecurityPrice
from django.db.models import Q

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
    def __init__(self, ticker):
        start_date = DataSettings.objects.first().start_date
        end_date = date.today().strftime("%Y-%m-%d")

        self.ticker = ticker
        self.stock_data = yf.Ticker(ticker)
        self.stock_data.prices = yf.download(ticker, start=start_date, end=end_date)
        self.DB_ref = {'financials': Financials,
                       'balancesheet': BalanceSheet,
                       'dividends': Dividends,
                       'prices': SecurityPrice}
        # Get the data
        self.get_meta()
        for key in self.DB_ref.keys():
            self.get_data(db_name=key)

    def get_meta(self):
        if not SecurityMeta.objects.filter(symbol=self.ticker).exists():
            meta = self.stock_data.info
            # Get field names from model, remove related model names
            model_fields = [field.name for field in SecurityMeta._meta.get_fields()]
            model_fields = [x for x in model_fields if x not in list(apps.all_models['webface'].keys()) + ['id']]
            renames = {'longbusinesssummary': 'business_summary', 'fulltimeemployees': 'fulltime_employees'}

            new_keys = [x.lower().replace(' ', '_') for x in meta.keys()]
            meta = dict(zip(new_keys, meta.values()))

            # Add Null to any missing
            for field in model_fields:
                if field not in meta.keys():
                    meta[field] = None

            # Rename any as needed
            for key in renames.keys():
                if key in meta.keys():
                    meta[renames[key]] = meta.pop(key)

            # Remove extra
            meta = {key: meta[key] for key in model_fields}
            model = SecurityMeta(**meta)
            model.save()

    def get_data(self, db_name):
        # Extract the target data and determine orientation
        data = getattr(self.stock_data, db_name)
        Database = self.DB_ref[db_name]


        if isinstance(data, pd.Series) | isinstance(data.index, pd.DatetimeIndex):
            data = data.reset_index()
        elif isinstance(data.columns, pd.DatetimeIndex):
            data = data.T.reset_index()
            data.rename(columns={"": "date"}, inplace=True)

        # Column names to lowercase
        data.columns = [x.lower().replace(' ', '_') for x in data.columns]
        dates = [d.strftime('%Y-%m-%d') for d in data['date']]

        #Check if data already downloaded
        if not Database.objects.filter(date__in=dates).exists():
            security_id = {'security_id': SecurityMeta.objects.get(symbol=self.ticker).id}
            Database.objects.bulk_create(
                Database(**{**security_id, **vals}) for vals in data.to_dict('records')
            )

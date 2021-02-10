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
    def __init__(self, tickers, update=False):
        # Get the data
        start_date = DataSettings.objects.first().start_date
        end_date = date.today().strftime("%Y-%m-%d")

        # Get existing symbols, remove existing from list if update = False
        db_symbol_list = list(SecurityMeta.objects.values_list('symbol', flat=True))
        if not update:
            tickers = set(tickers).difference(db_symbol_list)

        #Get data for securities, and add prices to data
        self.stock_data = {t: yf.Ticker(t) for t in tickers}
        prices = yf.download(tickers, group_by='ticker', start=start_date, end=end_date)
        for t in tickers:
            self.stock_data[t].prices = prices[t]

        self.DB_ref = {'financials': Financials,
                       'balancesheet': BalanceSheet,
                       'dividends': Dividends,
                       'prices': SecurityPrice}

        for t in tickers:
            print(t)
            for key in self.DB_ref.keys():
                self.set_meta(ticker=t)
                self.set_data(db_name=key, ticker=t)

    def set_meta(self, ticker):
        # TODO
        # Get list of db id's to replace and get list of new id's, updated and creating separately
        # model = SecurityMeta.objects.filter(symbol__in=tickers)
        if not SecurityMeta.objects.filter(symbol=ticker).exists():
            meta = self.stock_data[ticker].info
            # meta = [self.stock_data['meta'][x].info for x in tickers]

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

            # Remove extra fields
            meta = {key: meta[key] for key in model_fields}
            model = SecurityMeta(**meta)
            model.save()

    def set_data(self, db_name, ticker):
        # TODO
        # Get list of db id's to replace and get list of new id's, updated and creating separately

        # Extract the target data and determine orientation
        data = getattr(self.stock_data[ticker], db_name)
        Database = self.DB_ref[db_name]
        security_id = SecurityMeta.objects.get(symbol=ticker).id

        if isinstance(data, pd.Series) | isinstance(data.index, pd.DatetimeIndex):
            data = data.reset_index()
            data = data.dropna()
        elif isinstance(data.columns, pd.DatetimeIndex):
            data = data.T.reset_index()
            data.rename(columns={"": "date"}, inplace=True)

        # Column names to lowercase
        data.columns = [x.lower().replace(' ', '_') for x in data.columns]

        # Get dates & find missing
        db_dates = Database.objects.filter(security_id=security_id).values_list('date', flat=True)
        new_dates = [d.strftime('%Y-%m-%d') for d in data['date']]
        db_dates = [d.strftime('%Y-%m-%d') for d in db_dates]
        new_dates = set(new_dates).difference(db_dates)

        #Check if data already downloaded
        if new_dates:
            security_id = {'security_id': security_id}
            Database.objects.bulk_create(
                Database(**{**security_id, **vals}) for vals in data.to_dict('records')
            )

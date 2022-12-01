
from django.apps import apps
from optimizer.models import DataSettings, SecurityMeta, Financials, BalanceSheet, Dividends, SecurityPrice, SecurityList
from django.db.models import Q

import numpy as np
import pandas as pd
import yfinance as yf
import datetime
from datetime import date

from progressbar import ProgressBar
from itertools import islice
from urllib import request
import json

def get_latest_snp():
    # Fetch S&P500 list
    url = 'https://pkgstore.datahub.io/core/s-and-p-500-companies/362/datapackage.json'
    response = request.urlopen(url)
    package = json.loads(response.read())

    # Path of current listing
    path = [x['path'] for x in package['resources'] if x['datahub']['type'] == 'derived/json'].pop()

    # Fetch the list as JSOn with Name, Sector, and Symbols fields
    response = request.urlopen(path)
    snp = json.loads(response.read())

    return snp

def chunked_iterable(iterable, size):
    it = iter(iterable)
    while True:
        chunk = list(islice(it, size))
        if not chunk:
            break
        yield chunk

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

def get_id_table(tickers):
    id_table = pd.DataFrame(columns=['security_id', 'symbol'])

    # if missing from security list, add it
    db_syms = SecurityList.objects.filter(symbol__in=tickers).values_list('symbol', flat=True)
    missing = list(set(tickers).difference(db_syms))
    if missing:
        SecurityList.objects.bulk_create(
            SecurityList(**{'symbol': vals}) for vals in missing
        )
    # Make id table either way
    id_table = id_table.append(pd.DataFrame(
        SecurityList.objects.filter(symbol__in=tickers).values('id', 'symbol')
    ).rename(columns={'id': 'security_id'}))

    return id_table

def get_missing(_id_table, proposed_tickers, prices_too=False):
    # For the proposed tickers, get the matching security_id
    proposed_ids = list(_id_table[_id_table.symbol.isin(proposed_tickers)].security_id)

    # Check if any ids are missing from any database
    DB_ref = [SecurityMeta, Financials, BalanceSheet, Dividends]
    if prices_too:
        DB_ref = [*DB_ref, *[SecurityPrice]]

    missing_ids = []
    for DB in DB_ref:
        missing_ids.extend(
            list(set(proposed_ids).difference(DB.objects.all().values_list('security_id', flat=True)))
        )
    missing_sym = list(_id_table[_id_table.security_id.isin(missing_ids)].symbol)

    return missing_sym

def flatten_prices(prices, tickers):
    # Convert to multilevel if single ticker
    if len(tickers) == 1:
        midx = tuple((tickers[0], x) for x in prices.columns)
        prices.columns = pd.MultiIndex.from_tuples(midx)

    # Flatten out so that symbol is column
    prices = prices.stack(0).reset_index().rename(columns={'level_1': 'symbol'})

    return prices

class DownloadCompanyData:
    def __init__(self, tickers, update_all=False):
        # Initialize empty dict
        self.data = {'meta': pd.DataFrame(),
                     'financials': pd.DataFrame(),
                     'balancesheet': pd.DataFrame(),
                     'dividends': pd.DataFrame()}

        # Parameters
        self.all_tickers = [tickers] if isinstance(tickers, str) else tickers
        self.id_table = get_id_table(self.all_tickers)
        self.start_date = DataSettings.objects.first().start_date
        self.end_date = date.today().strftime("%Y-%m-%d")
        self.DB_ref = {'financials': Financials,
                       'balancesheet': BalanceSheet,
                       'dividends': Dividends}

        # Get existing symbols, remove existing from list
        if update_all:
            self.the_tickers = self.all_tickers
        else:
            self.the_tickers = get_missing(self.id_table, self.all_tickers)

        # get data
        if self.the_tickers:
            self.get_data()
        if self.the_tickers:
            self.set_meta()
            self.set_data()
        else:
            print('No new tickers to update.')

    def get_data(self):
        print('Downloading stock data for:')
        for c in chunked_iterable(self.the_tickers, 25):
            print(' '.join(c))

        stock_data = yf.Tickers(self.the_tickers)
        pbar = ProgressBar()
        for t in pbar(stock_data.symbols):
            s_id = int(self.id_table.loc[self.id_table['symbol'] == t].security_id.item())
            df_dict = {}
            try:
                obj = getattr(stock_data.tickers, t)
                # info, financials, balancesheet, dividends = attrgetter('info', 'quarterly_financials', 'quarterly_balancesheet', 'dividends')(obj)

                df_dict['meta'] = pd.DataFrame([obj.info])
                df_dict['financials'] = obj.quarterly_financials.T.reset_index().rename(columns={"": "date"})
                df_dict['balancesheet'] = obj.quarterly_balancesheet.T.reset_index().rename(columns={"": "date"})
                df_dict['dividends'] = obj.dividends.reset_index().dropna()
                # df_dict['dividends'] = yf.Ticker(t).dividends.reset_index().dropna()
                for dfn in df_dict.keys():
                    # If any are totally empty, just add a filler None, to avoid redownloading later
                    if df_dict[dfn].empty:
                        df_dict[dfn] = df_dict[dfn].append(pd.Series(), ignore_index=True).replace({np.NaN: None})
                    # Add security id
                    df_dict[dfn]['security_id'] = s_id
                    self.data[dfn] = self.data[dfn].append(df_dict[dfn])

            except:
                print("Couldn't get " + t + ', removing from list.')
                SecurityList.objects.filter(id=s_id).delete()
                self.the_tickers = set(self.the_tickers).difference([t])

        # Attach quarterly prices to financials
        print("Downloading quarterly prices")
        dates = self.data['financials'].date.dropna()
        prices = yf.download(self.all_tickers,
                             start=datetime.datetime(dates.min().year, 1, 1).strftime("%Y-%m-%d"),
                             end=dates.max().strftime('%Y-%m-%d'),
                             group_by='ticker')

        prices = flatten_prices(prices, self.all_tickers)
        prices_quarterly = prices.groupby([prices.Date.dt.quarter, 'symbol']).Close\
            .agg(['last', 'var']).reset_index()\
            .rename(columns={'Date': 'quarter', 'last': 'quarterly_close', 'var': 'quarterly_variance'})\
            .merge(self.id_table, on='symbol').drop('symbol', axis=1)

        self.data['financials'] = self.data['financials'].merge(
            prices_quarterly,
            left_on=[self.data['financials'].date.dt.quarter, 'security_id'],
            right_on=['quarter', 'security_id']).drop('quarter', axis=1)

    def set_meta(self):
        ids_in_meta = SecurityMeta.objects.all().values_list('symbol', flat=True)
        if list(set(self.the_tickers).difference(ids_in_meta)):
            print('Updating meta data...')
            # Get field names from model, remove related model names
            exclude = list(apps.all_models['optimizer'].keys()) + ['id'] + ['security']
            meta_fields = [field.name for field in SecurityMeta._meta.get_fields()]
            meta_fields = [x for x in meta_fields if x not in exclude]
            renames = {'longbusinesssummary': 'business_summary',
                       'fulltimeemployees': 'fulltime_employees'}

            # Get NEW meta data into data frame
            meta = self.data['meta']
            meta.columns = [x.lower().replace(' ', '_') for x in meta.columns]
            meta.columns = [renames[x] if x in renames.keys() else x for x in meta.columns]

            # Add Null to any missing
            missing = list(set(meta_fields).difference(meta.columns))
            meta[missing] = None

            # Subset select columns & add security id
            meta = meta[meta_fields]
            meta['fulltime_employees'] = meta['fulltime_employees'].fillna(-1).astype(int).replace({-1: None})

            # Merge security id
            meta = meta.merge(self.id_table, on='symbol')

            if not meta.empty:
                SecurityMeta.objects.bulk_create(
                    SecurityMeta(**vals) for vals in meta.to_dict('records')
                )
        else:
            print('Meta data already up to date')

    def set_data(self):
        for db_name in self.DB_ref.keys():
            Database = self.DB_ref[db_name]
            data = self.data[db_name]
            data.columns = [x.lower().replace(' ', '_') for x in data.columns]
            data = data.replace({pd.NaT: None})

            Qfilter = Q(security_id__in=data['security_id']) & Q(date__in=data['date'])
            old_data = pd.DataFrame(columns=['security_id', 'date'])
            old_data = old_data.append(pd.DataFrame(Database.objects.filter(Qfilter).values('security_id', 'date')))
            new_data = data[~(data.date.isin(old_data.date) & data.security_id.isin(old_data.security_id))]

            if not new_data.empty:
                print('Updating ' + db_name + ' data...')
                Database.objects.bulk_create(Database(**vals) for vals in new_data.to_dict('records'))
            else:
                print(db_name + ' already up to date')
        print('Database update complete')

class DownloadStockData:
    def __init__(self, tickers, updates=True):
        # Initialize dataframes
        self.prices = pd.DataFrame()

        # Parameters
        self.id_table = get_id_table(tickers)
        self.start_date = DataSettings.objects.first().start_date
        self.end_date = date.today().strftime("%Y-%m-%d")

        # Get existing symbols, remove existing from list
        self.all_tickers = tickers
        if updates:
            self.the_tickers = tickers
        else:
            self.the_tickers = get_missing(self.id_table, tickers)

        # get data
        if self.the_tickers:
            self.get_data()
            self.set_data()
        else:
            print('No new tickers to update.')

    def get_data(self):
        print('Downloading stock data for:')
        for c in chunked_iterable(self.the_tickers, 25):
            print(' '.join(c))

        # Get price data if requested
        print('Downloading price data...')
        price_data = yf.download(self.the_tickers,
                             group_by='ticker',
                             start=self.start_date,
                             end=self.end_date)

        #Flatten out so that symbol is column
        self.price_data = flatten_prices(price_data, self.all_tickers)

    def set_data(self):
        self.price_data.columns = [x.lower().replace(' ', '_') for x in self.price_data.columns]
        self.price_data = self.price_data.replace({pd.NaT: None})

        Qfilter = Q(security_id__in=self.price_data['security_id']) & Q(date__in=self.price_data['date'])
        old_data = pd.DataFrame(columns=['security_id', 'date'])
        old_data = old_data.append(pd.DataFrame(SecurityPrice.objects.filter(Qfilter).values('security_id', 'date')))
        new_data = self.price_data[~(self.price_data.date.isin(old_data.date) & self.price_data.security_id.isin(old_data.security_id))]

        if not new_data.empty:
            print('Updating stock price data...')
            SecurityPrice.objects.bulk_create(SecurityPrice(**vals) for vals in new_data.to_dict('records'))
        else:
            print('Stock price data already up to date')
        print('Database update complete')


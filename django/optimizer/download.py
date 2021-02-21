
from django.apps import apps
from webface.models import DataSettings, SecurityMeta, Financials, BalanceSheet, Dividends, SecurityPrice, SecurityList
from django.db.models import Q

import numpy as np
import pandas as pd
import yfinance as yf
import datetime
from datetime import date

from operator import attrgetter
from progressbar import ProgressBar
from itertools import islice

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

def get_missing(_id_table, proposed_tickers):
    # For the proposed tickers, get the matching security_id
    proposed_ids = list(_id_table[_id_table.symbol.isin(proposed_tickers)].security_id)

    # Check if any ids are missing from any database
    current_ids = SecurityPrice.objects.all().values_list('security_id', flat=True)
    missing_ids = set(proposed_ids).difference(current_ids)

    # Get the symbol for any missing ids
    missing_sym = list(_id_table[_id_table.security_id.isin(missing_ids)].symbol)

    return missing_sym

class DownloadCompanyData:
    def __init__(self, tickers, updates=True):
        # Initialize dataframes
        self.meta = pd.DataFrame()
        self.financials = pd.DataFrame()
        self.balancesheet = pd.DataFrame()
        self.dividends = pd.DataFrame()

        # Parameters
        self.id_table = get_id_table(tickers)
        self.start_date = DataSettings.objects.first().start_date
        self.end_date = date.today().strftime("%Y-%m-%d")
        self.DB_ref = {'financials': Financials,
                       'balancesheet': BalanceSheet,
                       'dividends': Dividends}

        # Get existing symbols, remove existing from list
        self.all_tickers = list(tickers)
        if updates:
            self.the_tickers = tickers
        else:
            self.the_tickers = get_missing(self.id_table, tickers)

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
                info, financials, balancesheet = attrgetter('info',
                                                            'quarterly_financials',
                                                            'quarterly_balancesheet')(obj)

                df_dict['meta'] = pd.DataFrame([info])
                df_dict['financials'] = financials.T.reset_index().rename(columns={"": "date"})
                df_dict['balancesheet'] = balancesheet.T.reset_index().rename(columns={"": "date"})
                df_dict['dividends'] = yf.Ticker(t).dividends.reset_index().dropna()

                for dfn in df_dict.keys():
                    # If any are totally empty, just add a filler None, to avoid redownloading later
                    if df_dict[dfn].empty:
                        df_dict[dfn] = df_dict[dfn].append(pd.Series(), ignore_index=True).replace({np.NaN: None})

                    # Add security id
                    df_dict[dfn]['security_id'] = s_id

                self.meta = self.meta.append(df_dict['meta'])
                self.financials = self.financials.append(df_dict['financials'])
                self.balancesheet = self.balancesheet.append(df_dict['balancesheet'])
                self.dividends = self.dividends.append(df_dict['dividends'])
            except:
                print("Couldn't get " + t + ', removing from list.')
                SecurityList.objects.filter(id=s_id).delete()
                self.the_tickers = set(self.the_tickers).difference([t])

        # Attach quarterly prices to financials
    # def get_quarterly_prices(self):
        dates = self.financials.date
        prices = yf.download(self.all_tickers,
                             start=datetime.datetime(dates.min().year, 1, 1).strftime("%Y-%m-%d"),
                             end=dates.max().strftime('%Y-%m-%d'),
                             group_by='ticker')

        prices_quarterly = prices.groupby(prices.index.quarter).Close.agg(['last', 'var'])
        prices_quarterly = prices_quarterly.rename(columns = {'last': 'quarterly_close', 'var': 'quarterly_variance'})

        self.financials = self.financials.merge(
            prices_quarterly,
            on=self.financials.date.dt.quarter
        ).drop('key_0', axis=1)

    def set_meta(self):
        ids_in_meta = SecurityMeta.objects.all().values_list('symbol', flat=True)
        if list(set(self.the_tickers).difference(ids_in_meta)):
            print('Updating meta data...')
            # Get field names from model, remove related model names
            exclude = list(apps.all_models['webface'].keys()) + ['id'] + ['security']
            meta_fields = [field.name for field in SecurityMeta._meta.get_fields()]
            meta_fields = [x for x in meta_fields if x not in exclude]
            renames = {'longbusinesssummary': 'business_summary',
                       'fulltimeemployees': 'fulltime_employees'}

            # Get NEW meta data into data frame
            meta = self.meta
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
        db_list = set(self.DB_ref).difference(['prices'])
        for db_name in db_list:
            Database = self.DB_ref[db_name]
            data = getattr(self, db_name)
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

        # Convert to multilevel if single ticker
        if len(self.the_tickers) == 1:
            midx = tuple((self.the_tickers[0], x) for x in price_data.columns)
            price_data.columns = pd.MultiIndex.from_tuples(midx)

        #Flatten out so that symbol is column
        self.price_data = price_data.stack(0).reset_index().rename(columns={'level_1': 'symbol'})

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


from django.apps import apps
from webframe import models
import piotroski_fscore
from django.db.models import Q

from optimizer import utils
import pandas as pd
import yfinance as yf
import datetime

from progressbar import ProgressBar

class DownloadCompanyData:
    def __init__(self, tickers):
        # Initialize empty dict
        self.data = {}

        # Parameters
        self.the_tickers = [tickers] if isinstance(tickers, str) else tickers
        self.the_tickers = utils.get_missing(self.the_tickers)

        self.start_date = models.DataSettings.objects.first().start_date
        self.end_date = datetime.date.today().strftime("%Y-%m-%d")
        self.DB_ref = {'financials': models.Financials,
                       'balancesheet': models.BalanceSheet,
                       'dividends': models.Dividends}

        # Cleanup any incomplete records before we do anything
        utils.clean_records()

        # get data
        if self.the_tickers:
            # Generate ID for new security if missing
            self.id_table = utils.get_id_table(self.the_tickers, add_missing=True)
            self.get_data()
            self.set_meta()
            self.set_data()
            piotroski_fscore.GetFscore


        else:
            print('No new tickers to update.')


    def get_data(self):
        print('Downloading stock data for:')
        for c in utils.chunked_iterable(self.the_tickers, 25):
            print(' '.join(c))

        stock_data = yf.Tickers(self.the_tickers)
        pbar = ProgressBar()
        data_dict = {k: [] for k in ['meta', 'financials', 'balancesheet', 'dividends']}
        for t in pbar(stock_data.symbols):
            s_id = int(self.id_table.loc[self.id_table['symbol'] == t].security_id.item())
            try:
                obj = stock_data.tickers.get(t)

                df_dict = {}
                df_dict['meta'] = pd.DataFrame([obj.info])
                df_dict['financials'] = obj.quarterly_financials.T.reset_index().rename(columns={"": "date"})
                df_dict['balancesheet'] = obj.quarterly_balancesheet.T.reset_index().rename(columns={"": "date"})
                df_dict['dividends'] = obj.dividends.reset_index().dropna()

                for df_name, df in df_dict.items():
                    # Add security id
                    df['security_id'] = s_id
                    # Add to df list to be concatenated
                    data_dict[df_name].append(df)
            except:
                print("Couldn't get " + t + ', removing from list.')
                models.SecurityList.objects.filter(id=s_id).delete()
                self.the_tickers = set(self.the_tickers).difference([t])

        # Concatenate the final data
        self.data = {k: pd.concat(v, axis=0) for k, v in data_dict.items()}

        # Attach quarterly prices to financials
        print("Downloading quarterly prices")
        dates = self.data['financials'].date.dropna()
        prices = yf.download(self.the_tickers,
                             start=datetime.datetime(dates.min().year, 1, 1).strftime("%Y-%m-%d"),
                             end=dates.max().strftime('%Y-%m-%d'),
                             group_by='ticker')

        prices = utils.flatten_prices(prices, self.the_tickers)
        prices_quarterly = prices.groupby([prices.Date.dt.quarter, 'symbol']).Close\
            .agg(['last', 'var']).reset_index()\
            .rename(columns={'Date': 'quarter', 'last': 'quarterly_close', 'var': 'quarterly_variance'})\
            .merge(self.id_table, on='symbol').drop('symbol', axis=1)

        self.data['financials'] = self.data['financials'].merge(
            prices_quarterly,
            left_on=[self.data['financials'].date.dt.quarter, 'security_id'],
            right_on=['quarter', 'security_id']).drop('quarter', axis=1)

    def set_meta(self):
        ids_in_meta = models.SecurityMeta.objects.all().values_list('symbol', flat=True)
        if list(set(self.the_tickers).difference(ids_in_meta)):
            print('Updating meta data...')
            # Get field names from model, remove related model names
            exclude = list(apps.all_models['webframe'].keys()) + ['id'] + ['security']
            meta_fields = [field.name for field in models.SecurityMeta._meta.get_fields()]
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
            meta.loc[:, 'fulltime_employees'] = meta['fulltime_employees'].fillna(-1).astype(int).replace({-1: None})

            # Merge security id
            meta = meta.merge(self.id_table, on='symbol')

            if not meta.empty:
                models.SecurityMeta.objects.bulk_create(
                    models.SecurityMeta(**vals) for vals in meta.to_dict('records')
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
            old_data = pd.DataFrame(Database.objects.filter(Qfilter).values('security_id', 'date'))
            if old_data.empty:
                old_data = pd.DataFrame(columns=['security_id', 'date'])

            new_data = data[~(data.date.isin(old_data.date) & data.security_id.isin(old_data.security_id))]

            # Fix NaNs
            new_data = new_data.astype(object).where(new_data.notna(), None)
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
        self.id_table = utils.get_id_table(tickers)
        self.start_date = models.DataSettings.objects.first().start_date
        self.end_date = datetime.date.today().strftime("%Y-%m-%d")

        # Get existing symbols, remove existing from list
        self.the_tickers = utils.get_missing(tickers)

        # get data
        if self.the_tickers:
            self.get_data()
            self.set_data()
        else:
            print('No new tickers to update.')

    def get_data(self):
        print('Downloading stock data for:')
        for c in utils.chunked_iterable(self.the_tickers, 25):
            print(' '.join(c))

        # Get price data if requested
        print('Downloading price data...')
        price_data = yf.download(self.the_tickers,
                             group_by='ticker',
                             start=self.start_date,
                             end=self.end_date)

        #Flatten out so that symbol is column
        self.price_data = utils.flatten_prices(price_data, self.the_tickers)

    def set_data(self):
        self.price_data.columns = [x.lower().replace(' ', '_') for x in self.price_data.columns]
        self.price_data = self.price_data.replace({pd.NaT: None})

        Qfilter = Q(security_id__in=self.price_data['security_id']) & Q(date__in=self.price_data['date'])
        old_data = pd.DataFrame(columns=['security_id', 'date'])
        old_data = old_data.append(pd.DataFrame(models.SecurityPrice.objects.filter(Qfilter).values('security_id', 'date')))
        new_data = self.price_data[~(self.price_data.date.isin(old_data.date) &
                                     self.price_data.security_id.isin(old_data.security_id))]

        if not new_data.empty:
            print('Updating stock price data...')
            models.SecurityPrice.objects.bulk_create(models.SecurityPrice(**vals) for vals in new_data.to_dict('records'))
        else:
            print('Stock price data already up to date')
        print('Database update complete')


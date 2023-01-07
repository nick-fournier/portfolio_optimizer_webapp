
from django.apps import apps
from portfolio_optimizer.webframe import models
from portfolio_optimizer.optimizer import piotroski_fscore
from django.db.models import Q

from portfolio_optimizer.optimizer import utils
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
                       # 'dividends': models.Dividends,
                       'securityprice': models.SecurityPrice
                       }

        # Cleanup any incomplete records before we do anything
        utils.clean_records()
        self.download()

    def download(self):
        # get data
        if self.the_tickers:
            # Generate ID for new security if missing
            self.id_table = utils.get_id_table(self.the_tickers, add_missing=True)

            # Fetch the company data (balance sheet, financials, etc.)
            self.get_company_data()

            # Ensure meta set correctly, rerun clean if not
            incomplete = models.SecurityList.objects.filter(sector__isnull=True)
            if incomplete:
                incomplete.delete()
                utils.clean_records(self.DB_ref)

            if self.data:
                for db_name in self.DB_ref.keys():
                    # TODO save local backup data to csv?
                    self.set_data(db_name)

            piotroski_fscore.GetFscore()
            print('Database update complete')
        else:
            print('No new tickers to update.')


    def get_company_data(self):
        print('Downloading stock data for:')
        for c in utils.chunked_iterable(self.the_tickers, 25):
            print(' '.join(c))

        stock_data = yf.Tickers(self.the_tickers)
        pbar = ProgressBar()
        data_dict = {k: [] for k in ['meta', 'financials', 'balancesheet', 'dividends']}

        for t in pbar(stock_data.symbols):
            s_id = int(self.id_table.loc[self.id_table['symbol'] == t].security_id.item())
            df_dict = {}

            # TODO Check for local data first before scraping
            try:
                obj = stock_data.tickers.get(t)
                df_dict['meta'] = pd.DataFrame([obj.info])
                df_dict['financials'] = obj.financials.T.reset_index().rename(columns={"": "date"})
                df_dict['balancesheet'] = obj.balancesheet.T.reset_index().rename(columns={"": "date"})
                # df_dict['financials'] = obj.quarterly_financials.T.reset_index().rename(columns={"": "date"})
                # df_dict['balancesheet'] = obj.quarterly_balancesheet.T.reset_index().rename(columns={"": "date"})
                # df_dict['dividends'] = obj.dividends.reset_index().dropna()

                # Add shares outstanding to balance sheet
                df_dict['balancesheet'].index = df_dict['balancesheet'].date.dt.year
                df_dict['balancesheet'] = df_dict['balancesheet'].join(obj.shares).rename(
                    columns={'BasicShares': 'shares_outstanding'}
                )

                for df_name, df in df_dict.items():
                    # Add security id
                    df['security_id'] = s_id
                    # Add to df list to be concatenated
                    data_dict[df_name].append(df)

            except:
                print("Couldn't get " + t + ', removing from list.')
                models.SecurityList.objects.filter(id=s_id).delete()
                self.the_tickers = set(self.the_tickers).difference([t])

        # Check if completely empty before proceeding
        if not self.data:
            return

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

        self.get_price_data()
        self.set_meta()


    def get_price_data(self):
        print('Downloading stock data for:')
        for c in utils.chunked_iterable(self.the_tickers, 25):
            print(' '.join(c))

        # Get price data if requested
        print('Downloading price data...')
        price_data = yf.download(self.the_tickers,
                                 group_by='ticker',
                                 start=self.start_date,
                                 end=self.end_date)

        # Flatten out so that symbol is column
        price_data = utils.flatten_prices(price_data, self.the_tickers)

        # Convert symbol to security id
        price_data.columns = price_data.columns.str.lower()
        price_data = self.id_table.merge(price_data, on='symbol').drop(columns='symbol')

        self.data['securityprice'] = price_data

    def set_meta(self):
        incomplete_ids = [k for k, v in models.SecurityList.objects.values_list('symbol', 'sector') if v is None]
        incomplete_ids = list(set(self.the_tickers).intersection(incomplete_ids))

        if incomplete_ids:
            print('Updating meta data...')
            # Get field names from model, remove related model names
            exclude = list(apps.all_models['webframe'].keys()) + ['id', 'security', 'last_updated', 'first_created']
            meta_fields = [field.name for field in models.SecurityList._meta.get_fields()]
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
            meta = meta.astype(object).where(meta.notna(), None)

            # Merge security id
            meta = meta.merge(self.id_table.rename(columns={'security_id': 'pk'}), on='symbol')

            if not meta.empty:
                # models.SecurityMeta.objects.bulk_create(
                #     models.SecurityMeta(**vals) for vals in meta.to_dict('records')
                # )

                # create a list of user objects that need to be updated in bulk update
                meta_bulk_update_list = []
                meta_iter = zip(meta.pk, meta[meta_fields].to_dict(orient='records'))

                for key, values_dict in meta_iter:
                    meta = models.SecurityList.objects.get(id=key)

                    for field, value in values_dict.items():
                        setattr(meta, field, value)

                    meta_bulk_update_list.append(meta)

                # Bulk update
                models.SecurityList.objects.bulk_update(meta_bulk_update_list, meta_fields)


        else:
            print('Meta data already up to date')

    def set_data(self, db_name):
        DB = self.DB_ref[db_name]
        data = self.data[db_name]
        data.columns = [x.lower().replace(' ', '_') for x in data.columns]
        data = data.replace({pd.NaT: None})

        # remove fields we don't have
        if db_name == 'financials':
            data = data.drop(columns=['quarterly_close', 'quarterly_variance'])

        Qfilter = Q(security_id__in=data['security_id']) & Q(date__in=data['date'])
        old_data = pd.DataFrame(DB.objects.filter(Qfilter).values('security_id', 'date'))
        if old_data.empty:
            old_data = pd.DataFrame(columns=['security_id', 'date'])

        new_data = data[~(data.date.isin(old_data.date) & data.security_id.isin(old_data.security_id))]

        # Fix NaNs
        new_data = new_data.astype(object).where(new_data.notna(), None)
        if not new_data.empty:
            print('Updating ' + db_name + ' data...')
            DB.objects.bulk_create(DB(**vals) for vals in new_data.to_dict('records'))
        else:
            print(db_name + ' already up to date')


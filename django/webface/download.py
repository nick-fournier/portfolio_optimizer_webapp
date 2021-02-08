from django.apps import apps
from .models import DataSettings, SecurityMeta, Financials, BalanceSheet, Dividends, SecurityPrice

import pandas as pd
import yfinance as yf
from yahoofinancials import YahooFinancials
from datetime import date


class DownloadData:
    def __init__(self, ticker):
        start_date = DataSettings.objects.first().start_date
        end_date = date.today().strftime("%Y-%m-%d")

        self.ticker = ticker
        self.stock_data = yf.Ticker(ticker)
        self.stock_prices = yf.download(ticker, start=start_date, end=end_date)

        # Get the data
        if not SecurityMeta.objects.filter(symbol=ticker).exists():
            self.get_meta()
        # SecurityMeta.objects.filter(symbol=ticker).value('id')
        # if not Financials.objects.filter(security_id=ticker).exists():
            self.get_financials()


    def get_meta(self):
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

    def get_financials(self):
        financials = self.stock_data.financials.T.reset_index()
        financials.rename(columns={"": "date"}, inplace=True)
        financials.columns = [x.lower().replace(' ', '_') for x in financials.columns]

        # need to add pk from security_id
        financials['security_id'] = SecurityMeta.objects.filter(symbol=self.ticker).values('id')

        Financials.objects.bulk_create(
            Financials(**vals) for vals in financials.to_dict('records')
        )

    def get_balancesheet(self):
        balancesheet = self.stock_data.balancesheet.T.reset_index()
        balancesheet.rename(columns={"": "date"}, inplace=True)
        balancesheet.columns = [x.lower().replace(' ', '_') for x in balancesheet.columns]

        # need to add pk from security_id
        balancesheet['security_id'] = SecurityMeta.objects.filter(symbol=self.ticker).values('id')

        BalanceSheet.objects.bulk_create(
            BalanceSheet(**vals) for vals in balancesheet.to_dict('records')
        )

    # def get_dividends(self):
    #     dividends = self.stock_data.dividends.reset_index()
    #
    # def get_prices(self):
    #     prices = self.stock_prices.reset_index()


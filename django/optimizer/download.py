
# This module downloads ticker and inserts into database

import pandas as pd
import yfinance as yf
from yahoofinancials import YahooFinancials

from ..webface.models import SecurityPrice



cxchange = []
security_meta = []
company = []
security_price = []
stock_adjustment = []



ticker = 'MSFT'
meta = yf.Ticker("MSFT")
data = yf.download('MSFT',
                   start='2019-01-01',
                   end='2020-12-31')


fin2 = yf.Ticker("TSLA").financials.T

SecurityPrice.objects.bulk_create(
    SecurityPrice(**vals) for vals in df.to_dict('records')
)


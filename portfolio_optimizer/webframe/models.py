import datetime

from django.db import models


# TODO Clean up the data fields to be more efficent (e.g., divide by million, as int, etc.
#  Or at least convert int to IntegerFields. May cause issue with NAs?
# TODO user-specific entries?

class DataSettings(models.Model):
    start_date = models.DateField(default=datetime.date(2010, 1, 1))
    investment_amount = models.DecimalField(max_digits=17, null=True, decimal_places=2, default=10000)

class SecurityList(models.Model):
    symbol = models.CharField(default=None, null=True, max_length=12)
    last_updated = models.DateTimeField(auto_now=True)
    first_created = models.DateTimeField(auto_now_add=True)
    # exchange_id = models.ForeignKey(Exchange, on_delete=models.CASCADE)
    # currency = models.CharField(default=None, null=True, max_length=3)
    # longname = models.CharField(default=None, null=True, max_length=100)
    country = models.CharField(default=None, null=True, max_length=100)
    sector = models.CharField(default=None, null=True, max_length=50)
    industry = models.CharField(default=None, null=True, max_length=50)
    logo_url = models.CharField(default=None, null=True, max_length=100)
    fulltime_employees = models.IntegerField(default=None, null=True)
    business_summary = models.CharField(default=None, null=True, max_length=3000)
    has_fundamentals = models.BooleanField(default=False)
    has_securityprice = models.BooleanField(default=False)

    def __str__(self):
        return self.symbol

class Portfolio(models.Model):
    security = models.ForeignKey(SecurityList, on_delete=models.CASCADE)
    allocation = models.DecimalField(max_digits=10, null=True, decimal_places=6)
    shares = models.IntegerField(default=None, null=True)
    year = models.IntegerField(default=None, null=True)

class Scores(models.Model):
    security = models.ForeignKey(SecurityList, on_delete=models.CASCADE)
    date = models.DateField(null=True)
    fiscal_year = models.IntegerField(default=None, null=True)
    pf_score = models.IntegerField(default=None, null=True)
    pf_score_weighted = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    eps = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    pe_ratio = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    roa = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    cash = models.BigIntegerField(default=None, null=True)
    cash_ratio = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    delta_cash = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    delta_roa = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    accruals = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    delta_long_lev_ratio = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    delta_current_lev_ratio = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    delta_shares = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    delta_gross_margin = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    delta_asset_turnover = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    # yearly_close = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    # yearly_variance = models.DecimalField(max_digits=17, null=True, decimal_places=2)

class SecurityPrice(models.Model):
    security = models.ForeignKey(SecurityList, on_delete=models.CASCADE)
    date = models.DateField(null=True)
    open = models.DecimalField(max_digits=10, decimal_places=6)
    high = models.DecimalField(max_digits=10, decimal_places=6)
    low = models.DecimalField(max_digits=10, decimal_places=6)
    close = models.DecimalField(max_digits=10, decimal_places=6)
    adjclose = models.DecimalField(max_digits=10, decimal_places=6)
    # dividends = models.DecimalField(max_digits=10, decimal_places=6)
    # splits = models.IntegerField(default=None, null=True)
    volume = models.IntegerField(default=None, null=True)

class Fundamentals(models.Model):
    security = models.ForeignKey(SecurityList, on_delete=models.CASCADE)
    date = models.DateField(null=True)
    net_income = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    net_income_common_stockholders = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    total_liabilities = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    total_assets = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    current_assets = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    current_liabilities = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    shares_outstanding = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    cash = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    gross_profit = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    total_revenue = models.DecimalField(max_digits=17, null=True, decimal_places=2)

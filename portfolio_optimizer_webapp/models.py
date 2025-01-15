from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
import pandas as pd
import datetime

# TODO Clean up the data fields to be more efficent (e.g., divide by million, as int, etc.
#  Or at least convert int to IntegerFields. May cause issue with NAs?
# TODO user-specific entries?

def get_fiscal_year(date):
    assert date
    # Add fiscal year
    the_date = pd.to_datetime(date)
    fy_dates = {x: pd.to_datetime(f"{x}-12-31") for x in range(the_date.year - 1, datetime.date.today().year)}
    # get all differences with date as values
    cloz_dict = {abs(the_date.timestamp() - fydate.timestamp()): yr for yr, fydate in fy_dates.items()}
    # extracting minimum key using min()
    result = cloz_dict[min(cloz_dict.keys())]
    return result


class DataSettings(models.Model):
    
    class Meta:
        db_table = 'data_settings'
    
    OBJ_CHOICES = [
        ('max_sharpe', 'Maximum Sharpe Ratio'),
        ('min_volatility', 'Minimum Volatility'),
        ('max_quadratic_utility', 'Maximum Quadratic Utility')
    ]
    ESTIMATION_CHOICES = [
        ('nn', 'Neural Net'),
        ('lm', 'Linear Regression')
    ]

    start_date = models.DateField(default=datetime.date(2010, 1, 1))
    investment_amount = models.FloatField(default=10000)
    FScore_threshold = models.IntegerField(default=6)
    objective = models.CharField(default='max_sharpe', choices=OBJ_CHOICES, max_length=24)
    estimation_method = models.CharField(default='max_sharpe', choices=ESTIMATION_CHOICES, max_length=16)
    l2_gamma = models.FloatField(default=2)
    risk_aversion = models.FloatField(
        default=1,
        validators=[MinValueValidator(0.01), MaxValueValidator(1.0)],
        )


class SecurityList(models.Model):
    
    class Meta:
        db_table = 'security_list'

    symbol = models.CharField(max_length=12, primary_key=True)
    last_updated = models.DateTimeField(default=None, null=True)
    # first_created = models.DateTimeField(auto_now_add=True)
    # exchange_id = models.ForeignKey(Exchange, on_delete=models.CASCADE)
    # currency = models.CharField(default=None, null=True, max_length=3)
    name = models.CharField(default=None, null=True)
    country = models.CharField(default=None, null=True)
    sector = models.CharField(default=None, null=True)
    industry = models.CharField(default=None, null=True)
    # logo_url = models.CharField(default=None, null=True, max_length=100)
    fulltime_employees = models.IntegerField(default=None, null=True)
    business_summary = models.TextField(default=None, null=True, max_length=10000)
    # has_fundamentals = models.BooleanField(default=False)
    # has_securityprice = models.BooleanField(default=False)

    def __str__(self):
        return self.symbol

class SecurityPrice(models.Model):
    
    class Meta:
        db_table = 'security_price'
        unique_together = ('symbol', 'date')
    
    symbol = models.ForeignKey(SecurityList, on_delete=models.CASCADE, db_column='symbol')
    date = models.DateField(null=False, default=None)
    open = models.DecimalField(max_digits=16, decimal_places=6, default=None, null=True)
    high = models.DecimalField(max_digits=16, decimal_places=6, default=None, null=True)
    low = models.DecimalField(max_digits=16, decimal_places=6, default=None, null=True)
    close = models.DecimalField(max_digits=16, decimal_places=6, default=None, null=True)
    adjclose = models.DecimalField(max_digits=16, decimal_places=6, default=None, null=True)
    dividends = models.DecimalField(max_digits=10, decimal_places=6, default=None, null=True)
    splits = models.BigIntegerField(default=None, null=True)
    volume = models.BigIntegerField(default=None, null=True)


class Fundamentals(models.Model):
    
    class Meta:
        db_table = 'fundamentals'
        unique_together = ('symbol', 'as_of_date', 'period_type', 'currency_code')
        
    symbol = models.ForeignKey(SecurityList, on_delete=models.CASCADE, db_column='symbol')
    as_of_date = models.DateField()
    # year = models.IntegerField(default=None, null=True)
    # quarter = models.IntegerField(default=None, null=True)
    period_type = models.CharField()
    net_income = models.BigIntegerField(default=None, null=True)
    net_income_common_stockholders = models.BigIntegerField(default=None, null=True)
    total_liabilities_net_minority_interest = models.BigIntegerField(default=None, null=True)
    total_assets = models.BigIntegerField(default=None, null=True)
    current_assets = models.BigIntegerField(default=None, null=True)
    current_liabilities = models.BigIntegerField(default=None, null=True)
    capital_stock = models.BigIntegerField(default=None, null=True)
    cash_and_cash_equivalents = models.BigIntegerField(default=None, null=True)
    gross_profit = models.BigIntegerField(default=None, null=True)
    total_revenue = models.BigIntegerField(default=None, null=True)
    currency_code = models.CharField(default=None, null=True, max_length=3)
    enterprise_value = models.BigIntegerField(default=None, null=True)
    enterprises_value_ebitda_ratio = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    enterprises_value_revenue_ratio = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    forward_pe_ratio = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    market_cap = models.BigIntegerField(default=None, null=True)
    pb_ratio = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    pe_ratio = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    peg_ratio = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    ps_ratio = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)


    def save(self, *args, **kwargs):
        self.fiscal_year = get_fiscal_year(self.as_of_date)
        super(Fundamentals, self).save(*args, **kwargs)


class Portfolio(models.Model):
    
    class Meta:
        db_table = 'portfolio'

    symbol = models.ForeignKey(SecurityList, on_delete=models.CASCADE, db_column='symbol')
    fundamentals = models.OneToOneField(Fundamentals, on_delete=models.CASCADE, primary_key=True)
    allocation = models.DecimalField(max_digits=10, decimal_places=6)
    shares = models.IntegerField()


class Scores(models.Model):
    
    class Meta:
        db_table = 'scores'
        # unique_together = ('symbol', 'as_of_date', 'period_type', 'currency_code')
    
    fundamentals = models.OneToOneField(Fundamentals, on_delete=models.CASCADE, primary_key=True)
    symbol = models.ForeignKey(SecurityList, on_delete=models.CASCADE, db_column='symbol')
    roa = models.FloatField(default=None, null=True)
    delta_cash = models.FloatField(default=None, null=True)
    delta_roa = models.FloatField(default=None, null=True)
    accruals = models.FloatField(default=None, null=True)
    delta_long_lev_ratio = models.FloatField(default=None, null=True)
    delta_current_lev_ratio = models.FloatField(default=None, null=True)
    delta_shares = models.FloatField(default=None, null=True)
    delta_gross_margin = models.FloatField(default=None, null=True)
    delta_asset_turnover = models.FloatField(default=None, null=True)
    cash_ratio = models.FloatField(default=None, null=True)
    eps = models.FloatField(default=None, null=True)
    book_value = models.BigIntegerField(default=None, null=True)
    pf_score = models.IntegerField(default=None, null=True)
    pf_score_weighted = models.FloatField(default=None, null=True)

    
class ExpectedReturns(models.Model):
    
    class Meta:
        db_table = 'expected_returns'
    
    fundamentals = models.OneToOneField(Fundamentals, on_delete=models.CASCADE, primary_key=True)    
    symbol = models.ForeignKey(SecurityList, on_delete=models.CASCADE, db_column='symbol')
    # date = models.DateField()
    last_close = models.DecimalField(max_digits=16, decimal_places=6)
    forecasted_close = models.DecimalField(max_digits=16, decimal_places=6)
    expected_return = models.DecimalField(max_digits=16, decimal_places=6)
    variance = models.FloatField(default=None, null=True)

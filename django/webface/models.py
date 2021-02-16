from django.db import models

# Create your models here.
# https://analyzingalpha.com/create-an-equities-database

# class Exchange(models.Model):
#     name = models.CharField(max_length=50)
#     acronym = models.CharField(max_length=50)

class DataSettings(models.Model):
    start_date = models.DateField()

class SecurityList(models.Model):
    symbol = models.CharField(default=None, null=True, max_length=12)

class SecurityMeta(models.Model):
    # exchange_id = models.ForeignKey(Exchange, on_delete=models.CASCADE)
    security = models.ForeignKey(SecurityList, on_delete=models.CASCADE)
    currency = models.CharField(default=None, null=True, max_length=3)
    symbol = models.CharField(default=None, null=True, max_length=12)
    longname = models.CharField(default=None, null=True, max_length=100)
    country = models.CharField(default=None, null=True, max_length=100)
    sector = models.CharField(default=None, null=True, max_length=50)
    industry = models.CharField(default=None, null=True, max_length=50)
    logo_url = models.CharField(default=None, null=True, max_length=100)
    fulltime_employees = models.IntegerField(default=None, null=True)  # fullTimeEmployees
    business_summary = models.CharField(default=None, null=True, max_length=3000)       # longBusinessSummary

class SecurityPrice(models.Model):
    security = models.ForeignKey(SecurityList, on_delete=models.CASCADE)
    date = models.DateField(null=True)
    open = models.DecimalField(max_digits=10, decimal_places=6)
    high = models.DecimalField(max_digits=10, decimal_places=6)
    low = models.DecimalField(max_digits=10, decimal_places=6)
    close = models.DecimalField(max_digits=10, decimal_places=6)
    adj_close = models.DecimalField(max_digits=10, decimal_places=6)
    volume = models.IntegerField(default=None, null=True)

class Financials(models.Model):
    security = models.ForeignKey(SecurityList, on_delete=models.CASCADE)
    date = models.DateField(null=True)
    research_development = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    effect_of_accounting_charges = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    income_before_tax = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    minority_interest = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    net_income = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    selling_general_administrative = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    gross_profit = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    ebit = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    operating_income = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    other_operating_expenses = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    interest_expense = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    extraordinary_items = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    non_recurring = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    other_items = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    income_tax_expense = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    total_revenue = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    total_operating_expenses = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    cost_of_revenue = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    total_other_income_expense_net = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    discontinued_operations = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    net_income_from_continuing_ops = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    net_income_applicable_to_common_shares = models.DecimalField(max_digits=17, null=True, decimal_places=2)

class BalanceSheet(models.Model):
    security = models.ForeignKey(SecurityList, on_delete=models.CASCADE)
    date = models.DateField(null=True)
    intangible_assets = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    total_liab = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    total_stockholder_equity = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    total_assets = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    total_current_liabilities = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    total_current_assets = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    common_stock = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    other_current_liab = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    other_current_assets = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    other_liab = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    other_stockholder_equity = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    retained_earnings = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    good_will = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    treasury_stock = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    other_assets = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    cash = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    deferred_long_term_asset_charges = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    deferred_long_term_liab = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    property_plant_equipment = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    long_term_debt = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    long_term_investments = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    net_tangible_assets = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    short_long_term_debt = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    short_term_investments = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    net_receivables = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    inventory = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    accounts_payable = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    capital_surplus = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    minority_interest = models.DecimalField(max_digits=17, null=True, decimal_places=2)

class Dividends(models.Model):
    security = models.ForeignKey(SecurityList, on_delete=models.CASCADE)
    date = models.DateField(null=True)
    dividends = models.DecimalField(null=True, max_digits=16, decimal_places=6)

class Scores(models.Model):
    security = models.ForeignKey(SecurityList, on_delete=models.CASCADE)
    date = models.DateField(null=True)
    variance = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    PF_score = models.IntegerField(default=None, null=True)
    PF_score_weighted = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    ROA = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    cash = models.IntegerField(default=None, null=True)
    delta_cash = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    delta_ROA = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    accruals = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    delta_long_lev_ratio = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    delta_current_lev_ratio = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    delta_shares = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    delta_gross_margin = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    delta_asset_turnover = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)

from django.db import models

# Create your models here.
# https://analyzingalpha.com/create-an-equities-database

class Exchange(models.Model):
    name = models.CharField(max_length=50)
    acronym = models.CharField(max_length=50)
    mic = models.CharField(max_length=10)

class SecurityMeta(models.Model):
    # company_id = models.ForeignKey(Company, on_delete=models.CASCADE)
    exchange_id = models.ForeignKey(Exchange, on_delete=models.CASCADE)
    currency = models.CharField(max_length=3)
    ticker = models.CharField(max_length=12)
    name = models.CharField(max_length=200)
    figi = models.CharField(max_length=12)
    composite_figi = models.CharField(max_length=12)
    share_class_figi = models.CharField(max_length=12)
    has_invalid_data = models.BooleanField(default=False)


class Company(models.Model):
    security_id = models.ForeignKey(SecurityMeta, on_delete=models.CASCADE)
    name = models.CharField(max_length=64)
    cik = models.CharField(max_length=10)
    sector = models.CharField(max_length=50)
    industry_category = models.CharField(max_length=50)
    industry_group = models.CharField(max_length=50)
    company_url = models.CharField(max_length=100)
    description = models.CharField(max_length=1000)
    sic = models.CharField(max_length=4)
    employees = models.IntegerField()

class SecurityPrice(models.Model):
    security_id = models.ForeignKey(SecurityMeta, on_delete=models.CASCADE)
    date = models.DateField()
    open = models.DecimalField(max_digits=10, decimal_places=6)
    close = models.DecimalField(max_digits=10, decimal_places=6)
    high = models.DecimalField(max_digits=10, decimal_places=6)
    low = models.DecimalField(max_digits=10, decimal_places=6)
    volume = models.DecimalField(max_digits=10, decimal_places=6)
    adj_open = models.DecimalField(max_digits=10, decimal_places=6)
    adj_high = models.DecimalField(max_digits=10, decimal_places=6)
    adj_low = models.DecimalField(max_digits=10, decimal_places=6)
    adj_volume = models.IntegerField()
    intraperiod = models.BooleanField(default=False)
    frequency = models.CharField(max_length=16)

class StockAdjustment(models.Model):
    security_id = models.ForeignKey(SecurityMeta, on_delete=models.CASCADE)
    date = models.DateField()
    dividend_amount = models.DecimalField(max_digits=10, decimal_places=6)
    split_ratio = models.DecimalField(max_digits=10, decimal_places=6)
    factor = models.DecimalField(max_digits=10, decimal_places=6)

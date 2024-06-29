# Generated by Django 5.0.6 on 2024-06-28 21:41

import datetime
import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='DataSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_date', models.DateField(default=datetime.date(2010, 1, 1))),
                ('investment_amount', models.FloatField(default=10000)),
                ('FScore_threshold', models.IntegerField(default=6)),
                ('objective', models.CharField(choices=[('max_sharpe', 'Maximum Sharpe Ratio'), ('min_volatility', 'Minimum Volatility'), ('max_quadratic_utility', 'Maximum Quadratic Utility')], default='max_sharpe', max_length=24)),
                ('estimation_method', models.CharField(choices=[('nn', 'Neural Net'), ('lm', 'Linear Regression')], default='max_sharpe', max_length=16)),
                ('l2_gamma', models.FloatField(default=2)),
                ('risk_aversion', models.FloatField(default=1, validators=[django.core.validators.MinValueValidator(0.01), django.core.validators.MaxValueValidator(1.0)])),
            ],
            options={
                'db_table': 'data_settings',
            },
        ),
        migrations.CreateModel(
            name='SecurityList',
            fields=[
                ('symbol', models.CharField(max_length=12, primary_key=True, serialize=False)),
                ('last_updated', models.DateTimeField(default=None, null=True)),
                ('name', models.CharField(default=None, max_length=100, null=True)),
                ('country', models.CharField(default=None, max_length=100, null=True)),
                ('sector', models.CharField(default=None, max_length=50, null=True)),
                ('industry', models.CharField(default=None, max_length=50, null=True)),
                ('fulltime_employees', models.IntegerField(default=None, null=True)),
                ('business_summary', models.CharField(default=None, max_length=10000, null=True)),
            ],
            options={
                'db_table': 'security_list',
            },
        ),
        migrations.CreateModel(
            name='Scores',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(null=True)),
                ('fiscal_year', models.IntegerField(default=None, null=True)),
                ('pf_score', models.IntegerField(default=None, null=True)),
                ('pf_score_weighted', models.DecimalField(decimal_places=6, default=None, max_digits=16, null=True)),
                ('eps', models.DecimalField(decimal_places=6, default=None, max_digits=16, null=True)),
                ('pe_ratio', models.DecimalField(decimal_places=6, default=None, max_digits=16, null=True)),
                ('roa', models.DecimalField(decimal_places=6, default=None, max_digits=16, null=True)),
                ('cash', models.BigIntegerField(default=None, null=True)),
                ('cash_ratio', models.DecimalField(decimal_places=6, default=None, max_digits=16, null=True)),
                ('delta_cash', models.DecimalField(decimal_places=6, default=None, max_digits=16, null=True)),
                ('delta_roa', models.DecimalField(decimal_places=6, default=None, max_digits=16, null=True)),
                ('accruals', models.DecimalField(decimal_places=6, default=None, max_digits=16, null=True)),
                ('delta_long_lev_ratio', models.DecimalField(decimal_places=6, default=None, max_digits=16, null=True)),
                ('delta_current_lev_ratio', models.DecimalField(decimal_places=6, default=None, max_digits=16, null=True)),
                ('delta_shares', models.DecimalField(decimal_places=6, default=None, max_digits=16, null=True)),
                ('delta_gross_margin', models.DecimalField(decimal_places=6, default=None, max_digits=16, null=True)),
                ('delta_asset_turnover', models.DecimalField(decimal_places=6, default=None, max_digits=16, null=True)),
                ('symbol', models.ForeignKey(db_column='symbol', on_delete=django.db.models.deletion.CASCADE, to='portfolio_optimizer_webapp.securitylist')),
            ],
            options={
                'db_table': 'scores',
            },
        ),
        migrations.CreateModel(
            name='Portfolio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('allocation', models.DecimalField(decimal_places=6, max_digits=10, null=True)),
                ('shares', models.IntegerField(default=None, null=True)),
                ('fiscal_year', models.IntegerField(default=None, null=True)),
                ('symbol', models.ForeignKey(db_column='symbol', on_delete=django.db.models.deletion.CASCADE, to='portfolio_optimizer_webapp.securitylist')),
            ],
            options={
                'db_table': 'portfolio',
            },
        ),
        migrations.CreateModel(
            name='Fundamentals',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(null=True)),
                ('fiscal_year', models.IntegerField(default=None, null=True)),
                ('net_income', models.IntegerField(default=None, null=True)),
                ('net_income_common_stockholders', models.IntegerField(default=None, null=True)),
                ('total_liabilities', models.IntegerField(default=None, null=True)),
                ('total_assets', models.IntegerField(default=None, null=True)),
                ('current_assets', models.IntegerField(default=None, null=True)),
                ('current_liabilities', models.IntegerField(default=None, null=True)),
                ('shares_outstanding', models.IntegerField(default=None, null=True)),
                ('cash', models.IntegerField(default=None, null=True)),
                ('gross_profit', models.IntegerField(default=None, null=True)),
                ('total_revenue', models.IntegerField(default=None, null=True)),
                ('symbol', models.ForeignKey(db_column='symbol', on_delete=django.db.models.deletion.CASCADE, to='portfolio_optimizer_webapp.securitylist')),
            ],
            options={
                'db_table': 'fundamentals',
            },
        ),
        migrations.CreateModel(
            name='SecurityPrice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(null=True)),
                ('open', models.DecimalField(decimal_places=6, max_digits=10)),
                ('high', models.DecimalField(decimal_places=6, max_digits=10)),
                ('low', models.DecimalField(decimal_places=6, max_digits=10)),
                ('close', models.DecimalField(decimal_places=6, max_digits=10)),
                ('adjclose', models.DecimalField(decimal_places=6, max_digits=10)),
                ('volume', models.IntegerField(default=None, null=True)),
                ('symbol', models.ForeignKey(db_column='symbol', on_delete=django.db.models.deletion.CASCADE, to='portfolio_optimizer_webapp.securitylist')),
            ],
            options={
                'db_table': 'security_price',
            },
        ),
    ]
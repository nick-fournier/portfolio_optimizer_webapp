# Generated by Django 4.1.7 on 2023-04-01 02:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portfolio_optimizer', '0003_rename_has_prices_securitylist_has_securityprice'),
    ]

    operations = [
        migrations.AddField(
            model_name='scores',
            name='fiscal_year',
            field=models.IntegerField(default=None, null=True),
        ),
    ]

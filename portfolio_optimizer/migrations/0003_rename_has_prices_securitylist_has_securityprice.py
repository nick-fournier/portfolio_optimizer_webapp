# Generated by Django 4.1 on 2023-03-19 16:30

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('portfolio_optimizer', '0002_securitylist_has_fundamentals_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='securitylist',
            old_name='has_prices',
            new_name='has_securityprice',
        ),
    ]
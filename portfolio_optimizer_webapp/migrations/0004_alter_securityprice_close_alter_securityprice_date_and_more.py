# Generated by Django 4.2.16 on 2024-11-16 15:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portfolio_optimizer_webapp', '0003_securityprice_dividends_securityprice_splits_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='securityprice',
            name='close',
            field=models.DecimalField(decimal_places=6, default=None, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name='securityprice',
            name='date',
            field=models.DateField(default=None),
        ),
        migrations.AlterField(
            model_name='securityprice',
            name='high',
            field=models.DecimalField(decimal_places=6, default=None, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name='securityprice',
            name='low',
            field=models.DecimalField(decimal_places=6, default=None, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name='securityprice',
            name='open',
            field=models.DecimalField(decimal_places=6, default=None, max_digits=10, null=True),
        ),
        migrations.AlterUniqueTogether(
            name='securityprice',
            unique_together={('symbol', 'date')},
        ),
    ]

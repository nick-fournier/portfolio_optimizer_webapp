# Generated by Django 4.2.16 on 2025-01-15 05:41

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('portfolio_optimizer_webapp', '0013_alter_portfolio_symbol'),
    ]

    operations = [
        migrations.AlterField(
            model_name='scores',
            name='symbol',
            field=models.ForeignKey(db_column='symbol', on_delete=django.db.models.deletion.CASCADE, to='portfolio_optimizer_webapp.securitylist'),
        ),
    ]

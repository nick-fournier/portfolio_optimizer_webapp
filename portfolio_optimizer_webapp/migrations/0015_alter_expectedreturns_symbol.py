# Generated by Django 4.2.16 on 2025-01-15 05:43

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('portfolio_optimizer_webapp', '0014_alter_scores_symbol'),
    ]

    operations = [
        migrations.AlterField(
            model_name='expectedreturns',
            name='symbol',
            field=models.ForeignKey(db_column='symbol', on_delete=django.db.models.deletion.CASCADE, to='portfolio_optimizer_webapp.securitylist'),
        ),
    ]

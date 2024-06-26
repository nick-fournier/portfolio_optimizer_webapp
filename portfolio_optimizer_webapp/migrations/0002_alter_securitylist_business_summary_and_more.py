# Generated by Django 5.0.6 on 2024-06-29 22:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portfolio_optimizer_webapp', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='securitylist',
            name='business_summary',
            field=models.TextField(default=None, max_length=10000, null=True),
        ),
        migrations.AlterField(
            model_name='securitylist',
            name='country',
            field=models.CharField(default=None, null=True),
        ),
        migrations.AlterField(
            model_name='securitylist',
            name='industry',
            field=models.CharField(default=None, null=True),
        ),
        migrations.AlterField(
            model_name='securitylist',
            name='name',
            field=models.CharField(default=None, null=True),
        ),
        migrations.AlterField(
            model_name='securitylist',
            name='sector',
            field=models.CharField(default=None, null=True),
        ),
    ]

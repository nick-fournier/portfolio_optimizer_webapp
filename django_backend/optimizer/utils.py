import json
import datetime
import pandas as pd
from urllib import request
from itertools import islice
from django.db.models import Q
from webframe import models


def get_id_table(tickers, add_missing=False):
    # if missing from security list, add it
    db_syms = models.SecurityList.objects.filter(symbol__in=tickers).values_list('symbol', flat=True)

    missing = list(set(tickers).difference(db_syms))
    if missing and add_missing:
        models.SecurityList.objects.bulk_create(
            models.SecurityList(**{'symbol': vals}) for vals in missing
        )

    # Make id table either way
    query = models.SecurityList.objects.filter(symbol__in=tickers).values('id', 'symbol')
    id_table = pd.DataFrame(query).rename(columns={'id': 'security_id'})
    return id_table


def get_missing(proposed_tickers, DB=models.Financials):

    # First find ones that aren't in database at all
    existing = models.SecurityList.objects.filter(symbol__in=proposed_tickers)
    missing = set(proposed_tickers).difference(existing.values_list('symbol', flat=True))

    # Then find any that are out of date
    start_date = models.DataSettings.objects.values_list('start_date').first()[0]
    existing_todate = DB.objects.filter(Q(security_id__in=existing) & Q(date=start_date))

    # Get the corresponding symbol
    existing_todate = models.SecurityList.objects.filter(id__in=existing_todate).values_list('symbol', flat=True)

    # Find the missing that aren't up to date
    out_of_date = set(proposed_tickers).difference(existing_todate)

    # Add to the set of missing
    missing.update(out_of_date)

    return list(missing)

def clean_records(DB_ref_dict=None):
    # DB Reference dic
    if DB_ref_dict is None:
        DB_ref_dict = {'financials': models.Financials,
                  'balancesheet': models.BalanceSheet,
                  'dividends': models.Dividends,
                  'securityprice': models.SecurityPrice
                  }

    security_ids = models.SecurityList.objects.values_list('id', flat=True)

    incomplete_records = []
    for db_name, DB in DB_ref_dict.items():
        db_ids = DB.objects.values_list('security_id', flat=True)
        incomplete_records.extend(set(security_ids).difference(db_ids))
        incomplete_records.extend(set(db_ids).difference(security_ids))

    incomplete_records = list(set(incomplete_records))

    # Find incomplete records and remove
    if incomplete_records:
        records = models.SecurityList.objects.filter(id__in=incomplete_records)
        records.delete()

        for db_name, DB in DB_ref_dict.items():
            records = DB.objects.filter(security_id__in=incomplete_records)
            if records.exists():
                records.delete()


def get_latest_snp():
    # Fetch S&P500 list
    url = 'https://pkgstore.datahub.io/core/s-and-p-500-companies/362/datapackage.json'
    response = request.urlopen(url)
    package = json.loads(response.read())

    # Path of current listing
    path = [x['path'] for x in package['resources'] if x['datahub']['type'] == 'derived/json'].pop()

    # Fetch the list as JSOn with Name, Sector, and Symbols fields
    response = request.urlopen(path)
    snp = json.loads(response.read())

    return snp


def chunked_iterable(iterable, size):
    it = iter(iterable)
    while True:
        chunk = list(islice(it, size))
        if not chunk:
            break
        yield chunk


def date_query(date_list):
    dlist = [d.strftime('%Y-%m-%d') for d in date_list]
    query = ""
    for val in dlist:
        if (query == ""):
            query = Q(date__range=val)
        else:
            query |= Q(date__range=val)
    return query

def date_range(date_list):
    min = date_list.min()
    max = date_list.max()
    return [d.strftime('%Y-%m-%d') for d in [min, max]]


def flatten_prices(prices, tickers):
    # Convert to multilevel if single ticker
    if len(tickers) == 1:
        midx = tuple((tickers[0], x) for x in prices.columns)
        prices.columns = pd.MultiIndex.from_tuples(midx)

    # Flatten out so that symbol is column
    prices = prices.stack(0).reset_index().rename(columns={'level_1': 'symbol'})

    return prices

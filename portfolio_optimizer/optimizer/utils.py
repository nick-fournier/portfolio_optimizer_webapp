import datetime
import os
import json
import pandas as pd
from datetime import datetime, timedelta
from urllib import request
from itertools import islice
from django.db.models import Q, Max, Count, OuterRef, Subquery
from ..webframe import models


THIS_PATH = os.path.dirname(__file__)

def get_id_table(tickers, add_missing=False):
    # if missing from security list, add it
    in_db = models.SecurityList.objects.filter(symbol__in=tickers).values_list('symbol', flat=True)
    not_in_db = list(set(tickers) - set(in_db))

    if not_in_db and add_missing:
        models.SecurityList.objects.bulk_create(
            models.SecurityList(**{'symbol': vals}) for vals in missing
        )

    # Make id table either way
    query = models.SecurityList.objects.filter(symbol__in=tickers).values('id', 'symbol')
    id_table = pd.DataFrame(query).rename(columns={'id': 'security_id'})
    return id_table


def get_missing(
        proposed_tickers,
        prices_lapse_days=1,
        meta_lapse_days=90
        ):

    # Elapsed time before updating data
    meta_lapse_date =datetime.now() - timedelta(days=meta_lapse_days)
    price_lapse_date = datetime.now() - timedelta(days=prices_lapse_days)
    current_year = datetime.today().year

    # tickers in db of proposed ones
    in_db =  models.SecurityList.objects.filter(symbol__in=proposed_tickers)

    # First find ones that are out of date
    ood_all = in_db.filter(
        # Q(symbol__in=proposed_tickers) & # is in our target list
        Q(last_updated__lte=meta_lapse_date) &  # is out of date
        (Q(sector__isnull=False) | Q(symbol='^GSPC'))  # Is SP500 index and not a previous bad symbol call
    ).values_list('symbol', flat=True)


    # Find ones that aren't in database at all
    not_in_db = set(proposed_tickers) - set(in_db.values_list('symbol', flat=True))
        
    ood_tickers = {'meta': [], 'fundamentals': [], 'securityprice': []}

    # If nothing to update, exit
    if not ood_all and not not_in_db:
        return ood_tickers

    if ood_all:
        # Then find any out of date meta data records
        ood_tickers['metas'] = models.SecurityList.objects.filter(Q(symbol__in=ood_all) & Q(last_updated__lt=price_lapse_date))

        # Find any out of date fundamentals
        sq = models.Fundamentals.objects.filter(security_id=OuterRef('security_id')).order_by('-fiscal_year')
        ood_tickers['fundamentals'] = list(
            models.Fundamentals.objects.filter(
                Q(pk=Subquery(sq.values('pk')[:1])) & Q(security__symbol__in=ood_all) & Q(fiscal_year__lt=current_year)
            ).values_list('security__symbol', flat=True)
        )

        # Find any out of date price records
        sq = models.SecurityPrice.objects.filter(security_id=OuterRef('security_id')).order_by('-date')
        ood_tickers['securityprice'] = list(
            models.SecurityPrice.objects.filter(
                Q(pk=Subquery(sq.values('pk')[:1])) & Q(security__symbol__in=ood_all) & Q(date__lt=price_lapse_date)
            ).values_list('security__symbol', flat=True)
        )

    # Add outright missing to out of date tickers
    ood_tickers = {k: v + not_in_db for k, v in ood_tickers.items()}

    return ood_tickers

def clean_records(DB_ref_dict=None):

    # DB Reference dict
    if DB_ref_dict is None:
        DB_ref_dict = {
            'fundamentals': models.Fundamentals,
            'securityprice': models.SecurityPrice,
        }

    security_ids = models.SecurityList.objects.values_list('id', flat=True)

    # Finds any IDs that are not completely shared, fully mutually inclusive.
    incomplete_records = []
    # Finds IDs the security list does have
    has_records = {}
    for db_name, DB in DB_ref_dict.items():
        db_ids = DB.objects.values_list('security_id', flat=True)

        # Find any missing
        incomplete_records.extend(set(security_ids).difference(db_ids))
        incomplete_records.extend(set(db_ids).difference(security_ids))

        # Check for fundamentals and prices
        has_records['has_' + db_name] = set(security_ids).intersection(db_ids)

        # Remove duplicate rows if any
        unique_fields = ['security_id', 'date']
        duplicates = (
            DB.objects.values(*unique_fields)
            .order_by()
            .annotate(max_id=Max('id'), count_id=Count('id'))
            .filter(count_id__gt=1)
        )

        if duplicates:
            print(f'removing duplicate entries in {db_name}')
        for duplicate in duplicates:
            (
                DB.objects
                .filter(**{x: duplicate[x] for x in unique_fields})
                .exclude(id=duplicate['max_id'])
                .delete()
            )

    incomplete_records = list(set(incomplete_records))

    # Update security list to indicate if it has fundamentals and/or prices
    for field, has_ids in has_records.items():
        SecurityList = models.SecurityList.objects.filter(id__in=has_ids)
        SecurityList.update(**{field: True})

    # # Find incomplete records and remove
    # if incomplete_records:
    #     records = models.SecurityList.objects.filter(id__in=incomplete_records)
    #     print('Incomplete records: ' + ', '.join(records.values_list('symbol', flat=True)))
    #     records.delete()
    #     print('Removing from: ')
    #     for db_name, DB in DB_ref_dict.items():
    #         print(db_name)
    #         records = DB.objects.filter(security_id__in=incomplete_records)
    #         if records.exists():
    #             records.delete()


def get_latest_snp():
    json_path = os.path.join(THIS_PATH, '../fixtures/snp.json')
    today = datetime.today().date()
    timestamp = (datetime.today() - timedelta(days=1)).date()
    # Default timestamp will always fetch data

    if os.path.exists(json_path):
        # Get age of file
        mtime = os.stat(json_path).st_mtime
        timestamp = datetime.fromtimestamp(mtime).date()

    if timestamp < today:
        # Fetch S&P500 list
        url = 'https://pkgstore.datahub.io/core/s-and-p-500-companies/362/datapackage.json'
        response = request.urlopen(url)
        package = json.loads(response.read())

        # Path of current listing
        path = [x['path'] for x in package['resources'] if x['datahub']['type'] == 'derived/json'].pop()

        # Fetch the list as JSOn with Name, Sector, and Symbols fields
        response = request.urlopen(path)
        snp = json.loads(response.read())

        # Serializing pretty json
        json_object = json.dumps(snp, indent=4)

        # Writing to json
        with open(json_path, "w") as f:
            f.write(json_object)
    else:
        # Reading json
        with open(json_path) as f:
            snp = json.load(f)

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

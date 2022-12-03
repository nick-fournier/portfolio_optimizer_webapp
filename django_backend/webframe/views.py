# webframe/views.py


from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.http.response import HttpResponse

from django.views.generic.edit import FormView
from django.views.generic import ListView
from django.shortcuts import render
from rest_framework import viewsets

from django.db.models import Subquery, OuterRef

from webframe import serializers, models, forms
from optimizer import utils, download, piotroski_fscore

from django.utils.decorators import classonlymethod
from asgiref.sync import sync_to_async
import asyncio

import pandas as pd
import json


# Create your views here.
def index(request):
    return render(request, "optimizer/index.html")


class DashboardView(ListView):
    model = models.Scores
    form_class = forms.OptimizeForm
    template_name = 'optimizer/dashboard.html'
    success_url = reverse_lazy('dashboard')

    def post(self, request, *args, **kwargs):
        piotroski_fscore.GetFscore()
        return HttpResponseRedirect(reverse_lazy('dashboard'))

    def get_context_data(self, **kwargs):
        context = super(DashboardView, self).get_context_data(**kwargs)
        context['data_settings'] = models.DataSettings.objects.all()
        context['securities_list'] = models.SecurityList.objects.all().order_by('id')
        context['ticker_list'] = models.SecurityList.objects.all().order_by('symbol')

        #### Table from DF ####
        # Only most recent
        # sq = models.Scores.objects.filter(security_id=OuterRef('security_id')).order_by('-date')
        # scores = models.Scores.objects.filter(pk=Subquery(sq.values('pk'))).order_by('-security_id').values()

        # All
        scores = models.Scores.objects.all().order_by('-security_id').values()

        # scores = models.Scores.objects.filter(pk=Subquery(sq.values('pk')[:1])).order_by('-security_id').values()
        securities = models.SecurityMeta.objects.all().order_by('security_id').values()

        if scores.exists() and securities.exists():

            # Round decimals
            field_dat = models.Scores._meta.get_fields()
            decimal_fields = [x.name for x in field_dat if x.get_internal_type() == 'DecimalField']

            df_scores = pd.DataFrame(scores).astype({x: float for x in decimal_fields})
            df_scores = df_scores.round({x: 3 for x in decimal_fields})
            df_scores.cash = '$' + (df_scores.cash / 1e6).astype(str) + 'm'

            # Merge with other data
            df = df_scores.merge(pd.DataFrame(securities), on='security_id')
            df['date'] = [x.strftime("%Y-%m-%d") for x in df['date']]
            df = df.sort_values(['symbol', 'date', 'PF_score'], ascending=False).reset_index(drop=True)
            df.index += 1

            # parsing the DataFrame in json format.
            json_records = df.reset_index().to_json(orient='records')
            data = list(json.loads(json_records))

            context['score_table'] = data

        return context

class AddDataView(FormView):
    model = models.Scores
    form_class = forms.AddDataForm
    template_name = 'optimizer/add-data.html'
    success_url = reverse_lazy('add-data')
    snp_list = utils.get_latest_snp()
    snp_tickers = [x['Symbol'] for x in snp_list]

    def form_valid(self, form):
        if not models.DataSettings.objects.exists():
            return HttpResponseRedirect(reverse_lazy('add-data'))

        symbols = form.cleaned_data['symbols']

        # If the all symbol * is given
        if symbols == ['*']:
            symbols = self.snp_tickers
        else:
            # Check if symbol is valid SP500
            symbols = [x for x in symbols if x in self.snp_tickers]

        # Get data
        # download.DownloadCompanyData(symbols)
        for chunk in utils.chunked_iterable(symbols, 10):
            download.DownloadCompanyData(chunk)

        return HttpResponseRedirect(reverse_lazy('add-data'))

    def get_context_data(self, **kwargs):
        context = super(AddDataView, self).get_context_data(**kwargs)

        # Get list of snp data
        df_tickers = pd.DataFrame(models.SecurityList.objects.filter(symbol__in=self.snp_tickers).values())
        df_snp = pd.DataFrame(self.snp_list)
        df_snp.columns = df_snp.columns.str.lower()

        # Add last_updated cols from database
        if df_tickers.empty:
            df_snp['start_date'] = None
            snp_data = df_snp
        else:
            # df_tickers.start_date.dt.strftime('%m/%d/%Y')
            snp_data = df_snp.merge(df_tickers, on='symbol', how='left')
        snp_data = snp_data.astype(object).where(snp_data.notna(), None)

        context['snp_list'] = snp_data.to_dict('records')
        context['data_settings'] = models.DataSettings.objects.values('start_date').first()

        return context


class DataSettingsSerializerView(viewsets.ModelViewSet):
    serializer_class = serializers.DataSettingsSerializer
    queryset = models.DataSettings.objects.all()

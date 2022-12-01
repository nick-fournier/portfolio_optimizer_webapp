# optimizer/views.py

from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.views.generic.edit import FormView
from django.shortcuts import render
from .serializers import DataSettingsSerializer
from rest_framework import viewsets

from django.db.models import Subquery, OuterRef
# from background_task import background

from utils.piotroski_fscore import GetFscore
from utils.download import DownloadCompanyData, get_latest_snp
from .models import DataSettings, SecurityMeta, Scores, SecurityList
from .forms import OptimizeForm, AddDataForm, DataSettingsForm
from .multiforms import MultiFormsView

import pandas as pd
import json
from itertools import islice


# Create your views here.
def chunked_iterable(iterable, size):
    it = iter(iterable)
    while True:
        chunk = list(islice(it, size))
        if not chunk:
            break
        yield chunk


# FIXME Update to run on scheduled intervals? background_task is deprecated
# @background(schedule=0)
def fetch_financials():
    tickers = SecurityList.objects.all().values_list('symbol', flat=True)
    for c in chunked_iterable(tickers, 50):
        DownloadCompanyData(c, update_all=False)

def index(request):
    return render(request, "optimizer/index.html")


class DashboardView(FormView):
    model = Scores
    form_class = OptimizeForm
    template_name = 'optimizer/dashboard.html'
    success_url = reverse_lazy('dashboard')

    def form_valid(self, form):
        GetFscore()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(DashboardView, self).get_context_data(**kwargs)
        context['data_settings'] = DataSettings.objects.all()
        context['securities_list'] = SecurityList.objects.all().order_by('id')
        context['ticker_list'] = SecurityList.objects.all().order_by('symbol')

        #### Table from DF ####
        sq = Scores.objects.filter(security_id=OuterRef('security_id')).order_by('-date')
        scores = Scores.objects.filter(pk=Subquery(sq.values('pk')[:1])).order_by('-security_id').values(
            'security_id', 'date', 'PF_score', 'PF_score_weighted')
        securities = SecurityMeta.objects.all().order_by('security_id').values(
            'security_id', 'symbol', 'longname', 'currency', 'country', 'sector', 'industry', 'logo_url')

        if scores.exists() and securities.exists():
            df = pd.DataFrame(scores).merge(pd.DataFrame(securities), on='security_id')
            df['date'] = [x.strftime("%Y-%m-%d") for x in df['date']]
            df = df.sort_values('PF_score', ascending=False).reset_index(drop=True)
            df.index += 1
            # parsing the DataFrame in json format.
            json_records = df.reset_index().to_json(orient='records')
            data = list(json.loads(json_records))
            context['score_table'] = data

        return context




class AddDataView(FormView):
    model = Scores
    form_class = AddDataForm
    template_name = 'optimizer/add-data.html'
    success_url = reverse_lazy('add-data')


    def form_valid(self, form):
        if not DataSettings.objects.exists():
            return HttpResponseRedirect(reverse_lazy('add-data'))

        symbols = form.cleaned_data['symbols']
        old_symbols = SecurityList.objects.all().values_list('symbol', flat=True)
        new_symbols = set(symbols).difference(old_symbols)
        SecurityList.objects.bulk_create(
            SecurityList(**{'symbol': vals}) for vals in new_symbols
        )
        fetch_financials()
        return HttpResponseRedirect(reverse_lazy('add-data'))

    def get_context_data(self, **kwargs):
        context = super(AddDataView, self).get_context_data(**kwargs)

        # Get list of snp data
        context['snp_list'] = get_latest_snp()
        context['data_settings'] = DataSettings.objects.values('start_date').first()
        context['ticker_list'] = SecurityList.objects.all().order_by('symbol')

        return context


class DataSettingsSerializerView(viewsets.ModelViewSet):
    serializer_class = DataSettingsSerializer
    queryset = DataSettings.objects.all()

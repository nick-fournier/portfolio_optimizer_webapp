# webface/views.py

from django.urls import reverse_lazy
from django.apps import apps
from django.shortcuts import render
from django.views.generic.edit import CreateView, FormView, UpdateView
from django.views.generic import TemplateView
from django.db.models import Max, Subquery, OuterRef

from .piotroski_fscore import GetFscore
from .download import DownloadData
from .models import DataSettings, SecurityMeta, Scores
from .forms import AddDataForm, DataSettingsForm, OptimizeForm

import pandas as pd
import json
import datetime
from itertools import chain
from operator import attrgetter

# Create your views here.
def index(request):
    return render(request, "webface/index.html")


class DashboardView(TemplateView):
    model = Scores
    template_name = 'webface/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super(DashboardView, self).get_context_data(**kwargs)
        context['securities_list'] = SecurityMeta.objects.all().order_by('id')

        #### Table from DF ####
        sq = Scores.objects.filter(security_id=OuterRef('security_id')).order_by('-date')
        scores = pd.DataFrame(
            Scores.objects.filter(pk=Subquery(sq.values('pk')[:1])).order_by('-security_id').values(
                'security_id', 'date', 'PF_score', 'PF_score_weighted'
            )
        )
        securities = pd.DataFrame(SecurityMeta.objects.all().order_by('id').values(
            'id', 'symbol', 'longname', 'currency', 'country', 'sector', 'industry', 'logo_url'
        ))

        df = securities.merge(scores, left_on='id', right_on='security_id')
        df['date'] = [x.strftime("%Y-%m-%d") for x in df['date']]
        df = df.sort_values('PF_score', ascending=False)

        # parsing the DataFrame in json format.
        json_records = df.reset_index().to_json(orient='records')
        data = list(json.loads(json_records))
        context['score_table'] = data

        return context

class DataSettingsView(UpdateView):
    model = DataSettings
    form_class = DataSettingsForm
    template_name = 'webface/data-settings.html'
    success_url = reverse_lazy('dashboard')

    def get_context_data(self, **kwargs):
        context = super(DataSettingsView, self).get_context_data(**kwargs)
        context['data_settings'] = DataSettings.objects.all()
        return context

class OptimizeView(FormView):
    form_class = OptimizeForm
    template_name = 'webface/optimize.html'
    success_url = reverse_lazy('dashboard')

    def form_valid(self, form):
        GetFscore()
        return super().form_valid(form)

class AddDataView(FormView):
    form_class = AddDataForm
    template_name = 'webface/add-data.html'
    success_url = reverse_lazy('dashboard')

    def form_valid(self, form):
        tickers = form.cleaned_data['symbols']
        DownloadData(tickers, get_prices=False)
        return super().form_valid(form)

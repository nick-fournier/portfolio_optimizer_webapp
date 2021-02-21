# webface/views.py

from django.urls import reverse, reverse_lazy
from django.shortcuts import render
from django.http import HttpResponseRedirect

from django.db.models import Subquery, OuterRef
from background_task import background

from optimizer.piotroski_fscore import GetFscore
from optimizer.download import DownloadCompanyData
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


@background(schedule=0)
def fetch_financials():
    tickers = SecurityList.objects.all().values_list('symbol', flat=True)
    # DownloadData(tickers, get_prices=False, updates=False)
    for c in chunked_iterable(tickers, 100):
        DownloadCompanyData(c, updates=False)

def index(request):
    return render(request, "webface/index.html")

def multiple_forms(request):

    if request.method == 'POST':
        optimize_form = OptimizeForm(request.POST)
        add_data_form = AddDataForm(request.POST)
        data_settings_form = DataSettingsForm(request.POST)
        if optimize_form.is_valid() or add_data_form.is_valid() or data_settings_form.is_valid():
            # Do the needful
            return HttpResponseRedirect(reverse('dashboard'))
    else:
        optimize_form = OptimizeForm()
        add_data_form = AddDataForm()
        data_settings_form = DataSettingsForm()

    return render(request, 'pages/multiple_forms.html', {
        'optimize_form': optimize_form,
        'add_data_form': add_data_form,
        'data_settings_form': data_settings_form
    })

def get_initial(self):
    # data_settings_form.fields['date'].initial = '2010-01-01'
    return {'date': '2010-01-01' }

class DashboardView(MultiFormsView):
    template_name = 'webface/optimize.html'
    form_classes = {'optimize': OptimizeForm,
                    'data_settings': DataSettingsForm,
                    'add_data': AddDataForm
                    }

    success_urls = {
        'optimize': reverse_lazy('dashboard'),
        'data_settings': reverse_lazy('dashboard'),
        'add_data': reverse_lazy('dashboard')
    }

    def optimize_form_valid(self, form):
        GetFscore()
        form_name = form.cleaned_data.get('action')
        return HttpResponseRedirect(self.get_success_url(form_name))

    def add_data_form_valid(self, form):
        symbols = form.cleaned_data['symbols']
        old_symbols = SecurityList.objects.all().values_list('symbol', flat=True)
        new_symbols = set(symbols).difference(old_symbols)
        SecurityList.objects.bulk_create(
            SecurityList(**{'symbol': vals}) for vals in new_symbols
        )
        fetch_financials()
        form_name = form.cleaned_data.get('action')
        return HttpResponseRedirect(self.get_success_url(form_name))

    def data_settings_form(self, form):
        form_name = form.cleaned_data.get('action')
        return HttpResponseRedirect(self.get_success_url(form_name))

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


#### Old stuff
# class DataSettingsView(UpdateView):
#     model = DataSettings
#     form_class = DataSettingsForm
#     template_name = 'webface/data-settings.html'
#     success_url = reverse_lazy('dashboard')
#
#     def get_context_data(self, **kwargs):
#         context = super(DataSettingsView, self).get_context_data(**kwargs)
#         context['data_settings'] = DataSettings.objects.all()
#         return context

# class OptimizeView(FormView):
#     model = Scores
#     form_class = OptimizeForm
#     template_name = 'webface/optimize.html'
#     success_url = reverse_lazy('optimize')
#
#     def form_valid(self, form):
#         GetFscore()
#         return super().form_valid(form)
#
#     def get_context_data(self, **kwargs):
#         context = super(OptimizeView, self).get_context_data(**kwargs)
#         context['securities_list'] = SecurityList.objects.all().order_by('id')
#
#         #### Table from DF ####
#         sq = Scores.objects.filter(security_id=OuterRef('security_id')).order_by('-date')
#         scores = Scores.objects.filter(pk=Subquery(sq.values('pk')[:1])).order_by('-security_id').values(
#             'security_id', 'date', 'PF_score', 'PF_score_weighted')
#         securities = SecurityMeta.objects.all().order_by('security_id').values(
#             'security_id', 'symbol', 'longname', 'currency', 'country', 'sector', 'industry', 'logo_url')
#
#         if scores.exists() and securities.exists():
#             df = pd.DataFrame(scores).merge(pd.DataFrame(securities), on='security_id')
#             df['date'] = [x.strftime("%Y-%m-%d") for x in df['date']]
#             df = df.sort_values('PF_score', ascending=False).reset_index(drop=True)
#             df.index += 1
#             # parsing the DataFrame in json format.
#             json_records = df.reset_index().to_json(orient='records')
#             data = list(json.loads(json_records))
#             context['score_table'] = data
#
#         return context

# class AddDataView(FormView):
#     form_class = AddDataForm
#     template_name = 'webface/add-data.html'
#     success_url = reverse_lazy('add-data')
#
#     def get_context_data(self, **kwargs):
#         context = super(AddDataView, self).get_context_data(**kwargs)
#         context['ticker_list'] = SecurityList.objects.all().order_by('symbol')
#         return context
#
#     def form_valid(self, form):
#         symbols = form.cleaned_data['symbols']
#         old_symbols = SecurityList.objects.all().values_list('symbol', flat=True)
#         new_symbols = set(symbols).difference(old_symbols)
#         SecurityList.objects.bulk_create(
#             SecurityList(**{'symbol': vals}) for vals in new_symbols
#         )
#         fetch_financials()
#         return super().form_valid(form)

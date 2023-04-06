# webframe/views.py


from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.db.models import Max, Subquery, OuterRef

from django.views.generic.edit import FormView
from django import views
from django.shortcuts import render
from rest_framework import viewsets

from ..webframe import models, serializers, forms
from ..optimizer import utils, optimization, download, plots

import datetime
import pandas as pd
import json
import random
import re


# Create your views here.
def index(request):
    return render(request, "optimizer/index.html")

# uvicorn config.asgi:application --reload

# class DashboardView(views.generic.ListView):
class DashboardView(views.generic.FormView):
    model = models.Scores
    form_class = forms.OptimizeForm
    template_name = 'optimizer/dashboard.html'
    success_url = reverse_lazy('dashboard')

    # def post(self, request, *args, **kwargs):
    #     optimization.optimize()
    #     return HttpResponseRedirect(reverse_lazy('dashboard'))

    def form_valid(self, form):
        investment_amount = form.cleaned_data['investment_amount']
        optimalPortfolio = optimization.OptimizePorfolio(investment_amount)
        optimalPortfolio.save_portfolio()

        return HttpResponseRedirect(reverse_lazy('dashboard'))

    def get_context_data(self, **kwargs):
        context = super(DashboardView, self).get_context_data(**kwargs)
        context['data_settings'] = models.DataSettings.objects.all()
        context['plots'] = {}

        # Get scores + symbol
        related_fields = ['security__symbol',
                          # 'security__longname',
                          'security__business_summary',
                          'security__portfolio__shares',
                          'security__portfolio__allocation']

        scores_fields = [field.name for field in models.Scores._meta.get_fields()]
        scores_fields += related_fields

        # Only most recent
        scores = models.Scores.objects.values(*scores_fields)

        if scores.exists():
            # context['plots'] = plots.create_plots()

            context['plots']['spx'] = plots.compare_ytd()

            # Round decimals
            field_dat = models.Scores._meta.get_fields() + models.Portfolio._meta.get_fields()
            decimal_fields = [x.name for x in field_dat if x.get_internal_type() == 'DecimalField']

            # Formatting
            df_scores = pd.DataFrame(scores)
            df_scores = df_scores.loc[df_scores.groupby(["security"])["fiscal_year"].idxmax()]

            df_scores = df_scores.astype({x: float for x in decimal_fields if x in df_scores.columns})
            df_scores = df_scores.rename(columns={x: x.split('__')[-1] for x in related_fields})
            df_scores = df_scores.sort_values(['allocation', 'symbol', 'date', 'pf_score'],
                                              ascending=False).reset_index(drop=True)

            df_scores.allocation = round(100 * df_scores.allocation.astype(float), 2).astype(str) + "%"
            df_scores = df_scores.round({x: 3 for x in decimal_fields})
            df_scores.cash = '$' + (df_scores.cash / 1e6).astype(str) + 'm'
            df_scores['date'] = [x.strftime("%Y-%m-%d") for x in df_scores['date']]
            df_scores.index += 1

            # parsing the DataFrame in json format.
            json_records = df_scores.reset_index().to_json(orient='records')
            data = list(json.loads(json_records))

            context['score_table'] = data

        return context

class AddDataView(views.generic.FormView):
    model = models.Scores
    form_class = forms.AddDataForm
    template_name = 'optimizer/add-data.html'
    success_url = reverse_lazy('add-data')
    snp_list = utils.get_latest_snp()
    snp_tickers = [x['Symbol'] for x in snp_list]

    def form_valid(self, form):
        if not models.DataSettings.objects.exists() or not self.request.user.is_authenticated:
            return HttpResponseRedirect(reverse_lazy('add-data'))

        symbol_fieldval = form.cleaned_data['symbols']

        # If the all symbol * is given
        if symbol_fieldval == ['*']:
            symbols = self.snp_tickers
        else:
            symbols = []
            # Check for random arg
            for symb in symbol_fieldval:
                # If random, sample N and add to symbols list
                if 'random' in symb:
                    # Extract N
                    n = re.findall(r'\d+', symb)
                    n = int(n[0]) if isinstance(n, list) and len(n) > 0 else 10

                    # Tickers to sample from, not already selected
                    remaining = [x for x in self.snp_tickers if x not in symbols]

                    # Sample and append to list
                    symbols.extend(random.sample(remaining, n))
                else:
                    symbols.append(symb)

            # Check if symbol is valid SP500
            symbols = [x for x in symbols if x in self.snp_tickers]

        # Get data
        # download.DownloadCompanyData(symbols)
        for chunk in utils.chunked_iterable(symbols, 100):
            print('Updating chunk ' + ', '.join(chunk))
            download.DownloadCompanyData(chunk)

        return HttpResponseRedirect(reverse_lazy('add-data'))

    def get_context_data(self, **kwargs):
        context = super(AddDataView, self).get_context_data(**kwargs)

        # Get list of snp data
        df_tickers = models.SecurityList.objects.filter(symbol__in=self.snp_tickers)
        df_tickers = df_tickers.values('symbol', 'last_updated', 'first_created')
        df_tickers = pd.DataFrame(df_tickers)

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
        if 'last_updated' not in snp_data.columns:
            snp_data['last_updated'] = None

        snp_data = snp_data.sort_values(['last_updated', 'symbol'])

        # Default data settings
        if not models.DataSettings.objects.exists():
            data_settings = models.DataSettings(
                start_date=datetime.date(2010, 1, 1),
                investment_amount=10000
            )
            data_settings.save()

        context['snp_list'] = snp_data.to_dict('records')
        context['data_settings'] = models.DataSettings.objects.values('start_date').first()

        return context


class DataSettingsSerializerView(viewsets.ModelViewSet):
    serializer_class = serializers.DataSettingsSerializer
    queryset = models.DataSettings.objects.all()

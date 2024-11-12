# webframe/views.py


from django.urls import reverse_lazy
from django.views.generic.edit import FormView
from django.views.generic.base import TemplateView

from portfolio_optimizer_webapp.models import Fundamentals as Scores, DataSettings, Portfolio, SecurityList
from portfolio_optimizer_webapp import plots

import datetime
import pandas as pd
import markdown as md
import json
from pathlib import Path


class IndexView(TemplateView):
    template_name = 'optimizer/index.html'
    template_path = Path(__file__).resolve().parent / 'templates/optimizer/index.md'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        with open(self.template_path, 'r') as f:
            text = f.read()
            context["about"] = md.markdown(text)
            
        return context
    
# uvicorn config.asgi:application --reload

class DashboardView(FormView):
    model = Scores
    template_name = 'optimizer/dashboard.html'
    success_url = reverse_lazy('dashboard')

    def get_context_data(self, **kwargs):
        context = {}
        if len(kwargs) > 0:
            context = super(DashboardView, self).get_context_data(**kwargs)
        context['data_settings'] = DataSettings.objects.all()

        # Get scores + symbol
        related_fields = ['security__symbol',
                          # 'security__longname',
                          'security__business_summary',
                          'security__portfolio__shares',
                          'security__portfolio__allocation']

        scores_fields = [field.name for field in Scores._meta.get_fields()]
        scores_fields += related_fields

        # Only most recent
        scores = Scores.objects.values(*scores_fields)

        if scores.exists():
            # context['plots'] = plots.create_plots()
            context['plots']['spx'] = plots.compare_ytd()

            # Round decimals
            field_dat = Scores._meta.get_fields() + Portfolio._meta.get_fields()
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
            context['score_table']  = list(json.loads(json_records))

        return context

class MetaDataView(FormView):
    model = Scores
    template_name = 'optimizer/meta-data.html'
    success_url = reverse_lazy('portfolio-optimizer-meta-data')

    def get_context_data(self, **kwargs):
        context = {}
        if len(kwargs) > 0:
            context = super(MetaDataView, self).get_context_data(**kwargs)

        # Default data settings
        if not DataSettings.objects.exists():
            data_settings = DataSettings(
                start_date=datetime.date(2010, 1, 1),
                investment_amount=10000
            )
            data_settings.save()

        # Get list of snp data
        context['ticker_list'] = SecurityList.objects.values('symbol', 'name', 'sector', 'last_updated', 'first_created')
        context['data_settings'] = DataSettings.objects.values('start_date').first()

        return context

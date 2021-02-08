# webface/views.py

from django.urls import reverse_lazy
from django.apps import apps
from django.shortcuts import render
from django.http import HttpResponse
from django.views.generic.edit import CreateView, FormView, UpdateView
from django.views.generic import TemplateView
from django.views.generic.detail import DetailView
import yfinance as yf

from .models import SecurityMeta, DataSettings
from .forms import AddSecurityForm, DataSettingsForm

# Create your views here.
def index(request):
    return render(request, "webface/index.html")

class DashboardView(TemplateView):
    model = SecurityMeta
    template_name = 'webface/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super(DashboardView, self).get_context_data(**kwargs)
        context['security_list'] = SecurityMeta.objects.all()
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


class AddSecurityView(FormView):
    form_class = AddSecurityForm
    template_name = 'webface/add-security.html'
    success_url = reverse_lazy('dashboard')

    def download_meta(self, symbols):
        # Get field names from model, remove related model names
        model_fields = [field.name for field in SecurityMeta._meta.get_fields()]
        model_fields = [x for x in model_fields if x not in list(apps.all_models['webface'].keys()) + ['id']]
        renames = {'longbusinesssummary': 'business_summary', 'fulltimeemployees': 'fulltime_employees'}

        for ticker in symbols:
            if not SecurityMeta.objects.filter(symbol=ticker).exists():
                # Download stock meta data and flatten to lowercase
                meta = yf.Ticker(ticker).info
                new_keys = [x.lower().replace(' ', '_') for x in meta.keys()]
                meta = dict(zip(new_keys, meta.values()))

                # Add Null to any missing
                for field in model_fields:
                    if field not in meta.keys():
                        meta[field] = None

                # Rename any as needed
                for key in renames.keys():
                    if key in meta.keys():
                        meta[renames[key]] = meta.pop(key)

                # Remove extra
                meta = {key: meta[key] for key in model_fields}
                model = SecurityMeta(**meta)
                model.save()

                # SecurityMeta.objects.bulk_create(
                #     SecurityMeta(**vals) for vals in meta#.to_dict('records')
                # )

    def form_valid(self, form):
        symbols = form.cleaned_data['symbols']
        self.download_meta(symbols)

        return super().form_valid(form)

# webface/views.py

from django.urls import reverse_lazy
from django.apps import apps
from django.shortcuts import render

from django.views.generic.edit import CreateView, FormView, UpdateView
from django.views.generic import TemplateView

from datetime import date
import yfinance as yf

from .download import DownloadData
from .models import DataSettings, SecurityMeta, Financials
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

    def form_valid(self, form):
        tickers = form.cleaned_data['symbols']
        DownloadData(tickers, update=False)

        return super().form_valid(form)

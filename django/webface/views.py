# webface/views.py

from django.urls import reverse_lazy
from django.apps import apps
from django.shortcuts import render
from django.http import HttpResponse
from django.views.generic.edit import CreateView, FormView
from django.views.generic import TemplateView
from django.views.generic.detail import DetailView
import yfinance as yf

from .models import SecurityMeta
from .forms import CommaSeparatedCharField, AddSecurityForm

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

class AddSecurityView(FormView):
    template_name = 'webface/add-security.html'
    form_class = AddSecurityForm
    success_url = reverse_lazy('dashboard')

    def download_meta(self, symbols):
        # Get field names from model, remove related model names
        model_fields = [field.name for field in SecurityMeta._meta.get_fields()]
        model_fields = [x for x in model_fields if x not in list(apps.all_models['webface'].keys()) + ['id']]

        for t in symbols:
            # Extract meta data for security
            meta = yf.Ticker(t).info
            new_keys = [x.lower().replace(' ', '_') for x in meta.keys()]
            meta = dict(zip(new_keys, meta.values()))
            meta['description'] = meta.pop('longbusinesssummary')
            meta['employees'] = meta.pop('fulltimeemployees')
            meta['company_url'] = meta.pop('logo_url')
            meta = {key: meta[key] for key in model_fields}
            model = SecurityMeta(**meta)
            model.save()

            # SecurityMeta.objects.bulk_create(
            #     SecurityMeta(**vals) for vals in meta#.to_dict('records')
            # )

    def form_valid(self, form):
        symbols = form.cleaned_data['symbols']  # <--- Add this line to get email value
        self.download_meta(symbols)

        return super().form_valid(form)

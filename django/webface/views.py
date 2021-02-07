# webface/views.py

from django.shortcuts import render
from django.http import HttpResponse
from django.views.generic.edit import CreateView, FormView
import yfinance as yf

from .models import SecurityMeta
from .forms import CommaSeparatedCharField, AddSecurityForm

# Create your views here.
def index(request):
    return render(request, "webface/index.html")


class AddSecurityView(FormView):
    template_name = 'webface/add-security.html'
    form_class = AddSecurityForm
    success_url = ''

    # def form_valid(self, form):
    #     meta = yf.Ticker("MSFT")
    #     SecurityMeta.objects.bulk_create(
    #         SecurityMeta(**vals) for vals in meta.to_dict('records')
    #     )
    #     return super().form_valid(form)

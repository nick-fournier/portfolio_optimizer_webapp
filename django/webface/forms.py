from django import forms
from django.core import validators
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from django.forms.widgets import DateInput
from .models import SecurityMeta, DataSettings
import yfinance as yf
import datetime


class MinLengthValidator(validators.MinLengthValidator):
    message = 'Ensure this value has at least %(limit_value)d elements (it has %(show_value)d).'

class MaxLengthValidator(validators.MaxLengthValidator):
    message = 'Ensure this value has at most %(limit_value)d elements (it has %(show_value)d).'

class CommaSeparatedCharField(forms.Field):
    def __init__(self, dedup=True, max_length=None, min_length=None, *args, **kwargs):
        self.dedup, self.max_length, self.min_length = dedup, max_length, min_length
        super(CommaSeparatedCharField, self).__init__(*args, **kwargs)
        if min_length is not None:
            self.validators.append(MinLengthValidator(min_length))
        if max_length is not None:
            self.validators.append(MaxLengthValidator(max_length))

    def to_python(self, value):
        if value in validators.EMPTY_VALUES:
            return []

        value = [item.strip() for item in value.split(',') if item.strip()]

        if self.dedup:
            value = list(set(value))
        return value

    def clean(self, value):
        value = self.to_python(value)
        self.validate(value)
        self.run_validators(value)
        return value

# class AddDataForm(forms.Form):
#     symbol = CommaSeparatedCharField()
#
# class OptimizeForm(forms.Form):
#     pass

# class DataSettingsForm(ModelForm):
#     class Meta:
#         model = DataSettings
#         fields = ['start_date']
#         widgets = {
#             'start_date': DateInput(attrs={'type': 'date'}),
#         }

class MultipleForm(forms.Form):
    action = forms.CharField(max_length=60, widget=forms.HiddenInput())

class AddDataForm(MultipleForm):
    symbols = CommaSeparatedCharField()

class OptimizeForm(MultipleForm):
    pass

class DataSettingsForm(ModelForm):
    # start_date = forms.DateField(initial=datetime.datetime(2010, 1, 1))
    start_date = DataSettings.objects.first()
    class Meta:
        model = DataSettings
        fields = ['start_date']
        widgets = {
            'start_date': DateInput(attrs={'type': 'date'}),
        }

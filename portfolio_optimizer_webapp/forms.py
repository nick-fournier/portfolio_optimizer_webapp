from django import forms
from django.core import validators
from .models import DataSettings


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

        assert value is not None
        value = [item.strip() for item in value.split(',') if item.strip()]

        if self.dedup:
            value = list(set(value))
        return value

    def clean(self, value):
        value = self.to_python(value)
        self.validate(value)
        self.run_validators(value)
        return value

class OptimizeForm(forms.ModelForm):
    class Meta:
        model = DataSettings
        fields = ['investment_amount',
                  'FScore_threshold',
                  'objective',
                  'estimation_method',
                  'l2_gamma',
                  'risk_aversion']


class MultipleForm(forms.Form):
    action = forms.CharField(max_length=60, widget=forms.HiddenInput())

class AddDataForm(forms.Form):
    symbols = CommaSeparatedCharField()


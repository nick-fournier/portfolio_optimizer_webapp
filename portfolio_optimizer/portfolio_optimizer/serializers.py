from rest_framework import serializers
from .models import DataSettings, Scores

class DataSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSettings
        fields = ('id', 'start_date')
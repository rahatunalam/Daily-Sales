from rest_framework import serializers

from .models import Denomination, MfsAccount


class MfsAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = MfsAccount
        fields = ["id", "name", "account"]

    def validate_name(self, value):
        value = value.strip()
        qs = MfsAccount.objects.filter(name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("This wallet already exists.")
        return value


class DenominationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Denomination
        fields = ["id", "value"]

    def validate_value(self, value):
        if value <= 0:
            raise serializers.ValidationError("Enter a note or coin value.")
        if Denomination.objects.filter(value=value).exists():
            raise serializers.ValidationError("This value already exists.")
        return value

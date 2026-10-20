from django.conf import settings
from rest_framework import serializers

from .models import User


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name", "role", "designation"]


class LoginSerializer(serializers.Serializer):
    name = serializers.CharField()
    password = serializers.CharField(trim_whitespace=False)

    def validate(self, attrs):
        user = User.objects.filter(name__iexact=attrs["name"].strip()).first()
        if user is None or not user.check_password(attrs["password"]):
            raise serializers.ValidationError("Wrong name or password.")
        if not user.is_active:
            raise serializers.ValidationError("This user is inactive. Ask the owner to activate it.")
        attrs["user"] = user
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    """BR-14: current must be right, new >= 4 chars, new != current, new == confirm."""

    current_password = serializers.CharField(trim_whitespace=False)
    new_password = serializers.CharField(trim_whitespace=False)
    confirm_password = serializers.CharField(trim_whitespace=False)

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.check_password(attrs["current_password"]):
            raise serializers.ValidationError("Current password is wrong.")
        if len(attrs["new_password"]) < settings.MIN_PASSWORD_LENGTH:
            raise serializers.ValidationError(
                f"New password must be at least {settings.MIN_PASSWORD_LENGTH} characters."
            )
        if attrs["new_password"] == attrs["current_password"]:
            raise serializers.ValidationError("New password must be different from the current one.")
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError("New password and confirm password do not match.")
        return attrs


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, trim_whitespace=False)

    class Meta:
        model = User
        fields = ["id", "name", "role", "designation", "is_active", "password", "created_at"]
        read_only_fields = ["id", "is_active", "created_at"]

    def validate_name(self, value):
        value = value.strip()
        qs = User.objects.filter(name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A user with this name already exists.")
        return value

    def validate_password(self, value):
        if value and len(value) < settings.MIN_PASSWORD_LENGTH:
            raise serializers.ValidationError(
                f"Password must be at least {settings.MIN_PASSWORD_LENGTH} characters."
            )
        return value

    def validate(self, attrs):
        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError({"password": "Password is required."})
        return attrs

    def create(self, validated):
        password = validated.pop("password")
        return User.objects.create_user(password=password, **validated)

    def update(self, instance, validated):
        password = validated.pop("password", "")
        for k, v in validated.items():
            setattr(instance, k, v)
        if password:  # blank keeps the old password
            instance.set_password(password)
        instance.save()
        return instance

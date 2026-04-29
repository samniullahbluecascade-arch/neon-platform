from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password  = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model  = User
        fields = ["email", "password", "password2", "full_name", "company"]

    def validate(self, data):
        if data["password"] != data.pop("password2"):
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return data

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserProfileSerializer(serializers.ModelSerializer):
    jobs_remaining = serializers.IntegerField(read_only=True)
    tier_limits    = serializers.DictField(read_only=True)

    class Meta:
        model  = User
        fields = [
            "id", "email", "full_name", "company", "avatar_url",
            "tier", "jobs_used_this_month", "jobs_remaining", "tier_limits",
            "api_key", "email_verified", "created_at",
        ]
        read_only_fields = [
            "id", "email", "tier", "jobs_used_this_month",
            "jobs_remaining", "tier_limits", "api_key",
            "email_verified", "created_at",
        ]


class APIKeySerializer(serializers.Serializer):
    api_key = serializers.CharField(read_only=True)

from djoser.serializers import UserSerializer as BaseUserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from users.models import CustomUser, Follow
from recipes.serializers import CompactRecipeSerializer


class CustomUserSerializer(BaseUserSerializer):
    """Расширенный сериализатор пользователя с изображением профиля и статусом подписки."""
    profile_image = Base64ImageField(required=False)
    is_subscribed = serializers.SerializerMethodField()

    class Meta(BaseUserSerializer.Meta):
        model = CustomUser
        fields = BaseUserSerializer.Meta.fields + (
            'profile_image',
            'is_subscribed',
        )
        read_only_fields = ('is_subscribed',)

    def get_is_subscribed(self, obj):
        """Проверка, подписан ли текущий пользователь на этого пользователя."""
        request = self.context.get('request')
        return (
            request and request.user.is_authenticated
            and Follow.objects.filter(
                follower=request.user,
                following=obj
            ).exists()
        )


class BasicUserSerializer(CustomUserSerializer):
    """Компактный пользовательский сериализатор с подсчетом рецептов."""
    recipes_count = serializers.IntegerField(
        source='created_dishes.count',
        read_only=True
    )

    class Meta(CustomUserSerializer.Meta):
        fields = CustomUserSerializer.Meta.fields + ('recipes_count',)


class FollowSerializer(BasicUserSerializer):
    """Сериализатор для пользовательских подписок с ограниченным количеством рецептов."""
    recipes = serializers.SerializerMethodField()
    recipes_limit = serializers.IntegerField(
        write_only=True,
        required=False,
        default=None
    )

    class Meta(BasicUserSerializer.Meta):
        fields = BasicUserSerializer.Meta.fields + ('recipes',)
        extra_kwargs = {
            'recipes_limit': {'write_only': True}
        }

    def get_recipes(self, obj):
        """Получение ограниченного количества авторских рецептов."""
        request = self.context.get('request')
        limit = int(request.query_params.get('recipes_limit', 10**10)) if request else None
        recipes = obj.created_dishes.all()[:limit] if limit else obj.created_dishes.none()
        return CompactRecipeSerializer(recipes, many=True).data
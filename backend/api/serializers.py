from djoser.serializers import UserSerializer as DjoserUserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from recipes.models import (
    Ingredient,
    Recipe,
    IngredientAmount,
    Favorite,
    ShoppingList,
)
from users.models import CustomUser, Follow


class IngredientAmountWriteSerializer(serializers.ModelSerializer):
    """Сериализатор записи ингредиентов в рецепт."""
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source="ingredient"
    )

    class Meta:
        model = IngredientAmount
        fields = ("id", "amount")


class IngredientAmountReadSerializer(serializers.ModelSerializer):
    """Сериализатор чтения ингредиентов из рецепта."""
    id = serializers.ReadOnlyField(source="ingredient.id")
    name = serializers.ReadOnlyField(source="ingredient.name")
    measurement_unit = serializers.ReadOnlyField(
        source="ingredient.measurement_unit")

    class Meta:
        model = IngredientAmount
        fields = ("id", "name", "measurement_unit", "amount")


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор ингредиентов (только чтение)."""
    class Meta:
        model = Ingredient
        fields = ("id", "name", "measurement_unit")
        read_only_fields = fields


class RecipesLimitQuerySerializer(serializers.Serializer):
    """Параметр recipes_limit из query-параметров запроса."""
    recipes_limit = serializers.IntegerField(
        required=False, min_value=1,
        error_messages={
            'invalid': 'recipes_limit должен быть числом',
            'min_value': 'recipes_limit должен быть больше 0'
        }
    )


class PublicUserSerializer(DjoserUserSerializer):
    """Публичная информация о пользователе."""
    avatar = Base64ImageField(required=False)
    is_subscribed = serializers.SerializerMethodField()

    class Meta(DjoserUserSerializer.Meta):
        fields = (*DjoserUserSerializer.Meta.fields, "avatar", "is_subscribed")

    def get_is_subscribed(self, object):
        request = self.context.get("request")
        return (
            request
            and request.user.is_authenticated
            and object.followers.filter(follower=request.user).exists()
        )


class SubscribedAuthorSerializer(PublicUserSerializer):
    """Пользователь с рецептами для списка подписок."""
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(
        source="recipes.count", read_only=True
    )

    class Meta(PublicUserSerializer.Meta):
        fields = (
            *PublicUserSerializer.Meta.fields,
            "recipes",
            "recipes_count")

    def get_recipes(self, author):
        request = self.context.get("request")
        if not request:
            return []

        query_serializer = RecipesLimitQuerySerializer(
            data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        limit = query_serializer.validated_data.get("recipes_limit", 10**10)

        queryset = author.recipes.all()[:limit]
        return CompactRecipeSerializer(queryset, many=True).data


class CompactRecipeSerializer(serializers.ModelSerializer):
    """Краткое представление рецепта (в избранном и корзине)."""

    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")
        read_only_fields = fields


class RecipeSerializer(serializers.ModelSerializer):
    """Полное представление рецепта."""
    ingredients = IngredientAmountWriteSerializer(
        source="components_amounts", many=True, write_only=True
    )
    read_only_ingredients = IngredientAmountReadSerializer(
        source="components_amounts", many=True, read_only=True
    )
    image = Base64ImageField(required=True)
    author = PublicUserSerializer(read_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            "id", "name", "text", "cooking_time", "image",
            "author", "ingredients", "read_only_ingredients",
            "is_favorited", "is_in_shopping_cart"
        )
        read_only_fields = ("author", "is_favorited", "is_in_shopping_cart")

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError(
                "Добавьте хотя бы один ингредиент.")
        return value

    def _bulk_save_ingredients(self, recipe, items):
        IngredientAmount.objects.bulk_create([
            IngredientAmount(
                recipe=recipe,
                ingredient=item["ingredient"],
                amount=item["amount"]
            ) for item in items
        ])

    def _is_related_to_user(self, model, recipe):
        request = self.context.get("request")
        return (
            request and request.user.is_authenticated
            and model.objects.filter(user=request.user, recipe=recipe).exists()
        )

    def get_is_favorited(self, object):
        return self._is_related_to_user(Favorite, object)

    def get_is_in_shopping_cart(self, object):
        return self._is_related_to_user(ShoppingList, object)

    def create(self, validated_data):
        ingredients = validated_data.pop("components_amounts", [])
        recipe = Recipe.objects.create(**validated_data)
        self._bulk_save_ingredients(recipe, ingredients)
        return recipe

    def update(self, instance, validated_data):
        ingredients = validated_data.pop("components_amounts", [])
        instance = super().update(instance, validated_data)
        instance.components_amounts.all().delete()
        self._bulk_save_ingredients(instance, ingredients)
        return instance


class ProfileImageSerializer(serializers.ModelSerializer):
    profile_image = Base64ImageField(required=False)

    class Meta:
        model = CustomUser
        fields = ['profile_image']

from django.conf import settings
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

    def validate_amount(self, value):
        if value < settings.MIN_INGREDIENT_QUANTITY:
            raise serializers.ValidationError("Количество должно быть больше нуля.")
        elif value > settings.MIN_INGREDIENT_AMOUNT:
            raise serializers.ValidationError("Слишком большое количество ингредиента.")
        return value

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

        try:
            limit = int(request.query_params.get("recipes_limit", 10**10))
            if limit < 1:
                raise ValueError
        except (ValueError, TypeError):
            raise serializers.ValidationError("recipes_limit должен быть положительным числом")

        queryset = author.recipes.all()[:limit]
        return CompactRecipeSerializer(queryset, many=True).data


class CompactRecipeSerializer(serializers.ModelSerializer):
    """Краткое представление рецепта (в избранном и корзине)."""

    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")
        read_only_fields = fields


class RecipeWriteSerializer(serializers.ModelSerializer):
    """Сериализатор для создания и редактирования рецепта."""
    ingredients = IngredientAmountWriteSerializer(
        source="components_amounts", many=True
    )
    image = Base64ImageField(required=True)

    class Meta:
        model = Recipe
        fields = (
            "id", "name", "text", "cooking_time", "image",
            "ingredients"
        )

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


class RecipeReadSerializer(serializers.ModelSerializer):
    """Сериализатор для чтения рецепта (GET-запросы)."""
    ingredients = IngredientAmountReadSerializer(
        source="components_amounts", many=True, read_only=True
    )
    image = Base64ImageField()
    author = PublicUserSerializer(read_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            "id", "name", "text", "cooking_time", "image",
            "author", "ingredients",
            "is_favorited", "is_in_shopping_cart"
        )

    def _is_related_to_user(self, model, recipe):
        request = self.context.get("request")
        return (
            request and request.user.is_authenticated
            and model.objects.filter(user=request.user, recipe=recipe).exists()
        )

    def get_is_favorited(self, obj):
        return self._is_related_to_user(Favorite, obj)

    def get_is_in_shopping_cart(self, obj):
        return self._is_related_to_user(ShoppingList, obj)

class ProfileImageSerializer(serializers.ModelSerializer):
    profile_image = Base64ImageField(required=False)

    class Meta:
        model = CustomUser
        fields = ['profile_image']

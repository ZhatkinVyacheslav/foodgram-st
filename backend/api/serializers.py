from django.core.validators import MinValueValidator, MaxValueValidator
from djoser.serializers import UserSerializer as DjoserUserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from recipes.models import (
    Ingredient,
    Dish,
    IngredientAmount,
    Favorite,
    ShoppingList,
)
from users.models import Follow


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ['id', 'name', 'measurement_unit']


class IngredientAmountSerializer(serializers.ModelSerializer):
    """Связка «ингредиент — количество» для рецепта."""

    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source="ingredient",
    )
    name = serializers.CharField(
        source="ingredient.name",
        read_only=True,
    )
    measurement_unit = serializers.CharField(
        source="ingredient.measurement_unit",
        read_only=True,
    )
    amount = serializers.IntegerField(
        source="quantity",
        validators=[MinValueValidator(1, "Минимум 1")],
    )

    class Meta:
        model = IngredientAmount
        fields = ("id", "name", "measurement_unit", "amount")


class ShortRecipeSerializer(serializers.ModelSerializer):
    """Облегчённый рецепт (для списков)."""
    name = serializers.CharField(source="title")
    cooking_time = serializers.IntegerField()

    class Meta:
        model = Dish
        fields = ("id", "name", "image", "cooking_time")


class PublicUserSerializer(DjoserUserSerializer):
    """Публичный пользователь + аватар + флаг подписки."""
    avatar = Base64ImageField(required=False)
    is_subscribed = serializers.SerializerMethodField()

    class Meta(DjoserUserSerializer.Meta):
        fields = (*DjoserUserSerializer.Meta.fields, "avatar", "is_subscribed")

    def get_is_subscribed(self, obj):
        req = self.context.get("request")
        return (
            req
            and req.user.is_authenticated
            and Follow.objects.filter(
                follower=req.user,
                following=obj,
            ).exists()
        )


class SubscribedAuthorSerializer(PublicUserSerializer):
    """Пользователь‑автор с урезанным набором рецептов."""
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(
        source="recipes.count",
        read_only=True,
    )

    class Meta(PublicUserSerializer.Meta):
        fields = (
            *PublicUserSerializer.Meta.fields,
            "recipes",
            "recipes_count",
        )

    def get_recipes(self, author):
        limit = int(
            self.context["request"].query_params.get("recipes_limit", 10**10)
        )
        qs = author.recipes.all()[:limit]
        return ShortRecipeSerializer(qs, many=True).data


# ----------------------------------------------------------- MAIN DISH
class RecipeSerializer(serializers.ModelSerializer):
    """Полная карточка рецепта."""

    name = serializers.CharField(required=True)
    text = serializers.CharField(required=True)
    cooking_time = serializers.IntegerField(
        required=True,
        validators=[
            MinValueValidator(1, "Минимум 1 минута"),
            MaxValueValidator(600, "Максимум 600 минут")
        ]
    )

    ingredients = IngredientAmountSerializer(
        source="components_amounts",
        many=True,
        required=True
    )
    image = Base64ImageField(required=True)

    author = PublicUserSerializer(read_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Dish
        fields = (
            "id",
            "name",
            "text",
            "cooking_time",
            "image",
            "author",
            "ingredients",
            "is_favorited",
            "is_in_shopping_cart",
        )

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError("Добавьте хотя бы один ингредиент")
        return value

    @staticmethod
    def _bulk_save_ingredients(dish, items):
        IngredientAmount.objects.bulk_create(
            IngredientAmount(
                recipe=dish,
                ingredient=item["ingredient"],
                quantity=item["quantity"],
            )
            for item in items
        )

    def _flag(self, model, dish):
        req = self.context.get("request")
        return (
            req
            and req.user.is_authenticated
            and model.objects.filter(user=req.user, recipe=dish).exists()
        )

    def get_is_favorited(self, obj):
        return self._flag(Favorite, obj)

    def get_is_in_shopping_cart(self, obj):
        return self._flag(ShoppingList, obj)

    def create(self, validated_data):
        ingredients = validated_data.pop("components_amounts", [])
        dish = Dish.objects.create(**validated_data)
        self._bulk_save_ingredients(dish, ingredients)
        return dish

    def update(self, instance, validated_data):
        ingredients = validated_data.pop("components_amounts", [])
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        instance.components_amounts.all().delete()
        self._bulk_save_ingredients(instance, ingredients)
        return instance
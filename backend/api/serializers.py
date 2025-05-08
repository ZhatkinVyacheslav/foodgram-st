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


class IngredientAmountWriteSerializer(serializers.ModelSerializer):
    """Запись игредиентов"""
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source="ingredient"
    )
    amount = serializers.IntegerField(
        source="quantity",
    )

    class Meta:
        model = IngredientAmount
        fields = ("id", "amount")


class IngredientAmountReadSerializer(serializers.ModelSerializer):
    """Чтение игредиентов"""
    id = serializers.ReadOnlyField(source="ingredient.id")
    name = serializers.ReadOnlyField(source="ingredient.name")
    measurement_unit = serializers.ReadOnlyField(source="ingredient.measurement_unit")
    amount = serializers.ReadOnlyField(source="quantity")

    class Meta:
        model = IngredientAmount
        fields = ("id", "name", "measurement_unit", "amount")


class PublicUserSerializer(DjoserUserSerializer):
    avatar = Base64ImageField(required=False)
    is_subscribed = serializers.SerializerMethodField()

    class Meta(DjoserUserSerializer.Meta):
        fields = (*DjoserUserSerializer.Meta.fields, "avatar", "is_subscribed")

    def get_is_subscribed(self, obj):
        request = self.context.get("request")
        return (
            request
            and request.user.is_authenticated
            and obj.followers.filter(follower=request.user).exists()
        )


class SubscribedAuthorSerializer(PublicUserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(
        source="recipes.count", read_only=True
    )

    class Meta(PublicUserSerializer.Meta):
        fields = (*PublicUserSerializer.Meta.fields, "recipes", "recipes_count")

    def get_recipes(self, author):
        request = self.context.get("request")

        if request is None:
            return []

        query_serializer = RecipesLimitQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)

        limit = query_serializer.validated_data.get("recipes_limit", 10**10)
        qs = author.recipes.all()[:limit]
        return CompactRecipeSerializer(qs, many=True).data


class RecipeSerializer(serializers.ModelSerializer):
    ingredients = IngredientAmountWriteSerializer(
        source="components_amounts", many=True, write_only=True
    )
    ingredients_data = IngredientAmountReadSerializer(
        source="components_amounts", many=True, read_only=True
    )
    image = Base64ImageField(required=True)
    author = PublicUserSerializer(read_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Dish
        fields = (
            "id", "name", "text", "cooking_time", "image",
            "author", "ingredients", "ingredients_data",
            "is_favorited", "is_in_shopping_cart"
        )
        read_only_fields = ("author", "is_favorited", "is_in_shopping_cart")

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError("Добавьте хотя бы один ингредиент.")
        return value

    def _bulk_save_ingredients(self, dish, items):
        IngredientAmount.objects.bulk_create(
            IngredientAmount(
                recipe=dish,
                ingredient=item["ingredient"],
                quantity=item["quantity"]
            ) for item in items
        )

    def _flag(self, model, dish):
        req = self.context.get("request")
        return (
            req and req.user.is_authenticated
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
        instance = super().update(instance, validated_data)
        instance.components_amounts.all().delete()
        self._bulk_save_ingredients(instance, ingredients)

        return instance

class RecipesLimitQuerySerializer(serializers.Serializer):
    recipes_limit = serializers.IntegerField(
        required=False, min_value=1,
        error_messages={
            'invalid': 'recipes_limit должен быть числом',
            'min_value': 'recipes_limit должен быть больше 0'
        }
    )


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор данных ингредиентов (только чтение)."""
    class Meta:
        model = Ingredient
        fields = ("id", "name", "measurement_unit")
        read_only_fields = ("id", "name", "measurement_unit")


class CompactRecipeSerializer(serializers.ModelSerializer):
    """Компактный сериализатор для рецептов (для отображения)."""

    class Meta:
        model = Dish
        fields = ("id", "name", "image", "cooking_time")
        read_only_fields = fields
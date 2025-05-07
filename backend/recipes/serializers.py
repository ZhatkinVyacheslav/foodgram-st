from rest_framework import serializers
from recipes.models import Dish, Ingredient


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
from rest_framework import serializers
from drf_extra_fields.fields import Base64ImageField
from django.core.validators import MinValueValidator

from recipes.models import Recipe, Ingredient, RecipeIngredient


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор данных ингредиентов."""

    class Meta:
        model = Ingredient
        fields = ("id", "name", "measurement_unit")
        read_only_fields = ("id", "name", "measurement_unit")


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Сериализатор связи рецепта и ингредиента."""
    id = serializers.PrimaryKeyRelatedField(
        source="ingredient",
        queryset=Ingredient.objects.all()
    )
    name = serializers.CharField(
        source="ingredient.name",
        read_only=True
    )
    measurement_unit = serializers.CharField(
        source="ingredient.measurement_unit",
        read_only=True
    )
    amount = serializers.IntegerField(
        min_value=1,
        validators=[MinValueValidator(1)]
    )

    class Meta:
        model = RecipeIngredient
        fields = ("id", "name", "measurement_unit", "amount")


class RecipeSerializer(serializers.ModelSerializer):
    """Основной сериализатор рецептов."""
    author = serializers.StringRelatedField(read_only=True)
    ingredients = RecipeIngredientSerializer(
        source="recipe_ingredients",
        many=True,
        required=True
    )
    image = Base64ImageField()
    is_favorite = serializers.SerializerMethodField()
    in_shopping_list = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            "id",
            "name",
            "text",
            "image",
            "author",
            "cooking_time",
            "ingredients",
            "is_favorite",
            "in_shopping_list",
        )
        read_only_fields = ("author", "is_favorite", "in_shopping_list")

    def get_is_favorite(self, obj):
        """Проверка наличия рецепта в избранном."""
        request = self.context.get("request")
        return (
            request and request.user.is_authenticated
            and obj.favorited_by.filter(user=request.user).exists()
        )

    def get_in_shopping_list(self, obj):
        """Проверка наличия рецепта в списке покупок."""
        request = self.context.get("request")
        return (
            request and request.user.is_authenticated
            and obj.in_shopping_lists.filter(user=request.user).exists()
        )


class CompactRecipeSerializer(serializers.ModelSerializer):
    """Компактный сериализатор для рецептов."""
    
    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")
        read_only_fields = fields
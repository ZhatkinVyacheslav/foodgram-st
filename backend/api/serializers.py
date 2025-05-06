from django.core.validators import MinValueValidator
from djoser.serializers import UserSerializer as BaseUserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from users.models import Follow

from recipes.models import (
    Ingredient,
    Recipe,
    RecipeComponent,
    Favorite,
    ShoppingList,
)

class CustomBase64Field(Base64ImageField):
    pass

class IngredientMapper(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ("id", "name", "measurement_unit")

class ComponentSerializer(serializers.ModelSerializer):
    ingredient_id = serializers.PrimaryKeyRelatedField(
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
    quantity = serializers.IntegerField(
        validators=[MinValueValidator(1, "Minimum 1 unit")]
    )

    class Meta:
        model = RecipeComponent
        fields = ("ingredient_id", "name", "measurement_unit", "quantity")

class CompactRecipeSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="name")
    prep_duration = serializers.IntegerField(source="cooking_time")

    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "prep_duration")

class ProfileSerializer(BaseUserSerializer):
    profile_image = CustomBase64Field(required=False, source="avatar")
    has_subscription = serializers.SerializerMethodField()

    class Meta(BaseUserSerializer.Meta):
        fields = (*BaseUserSerializer.Meta.fields, "profile_image", "has_subscription")

    def check_subscription_status(self, user_obj):
        request = self.context.get("request")
        return (
            request
            and request.user.is_authenticated
            and Follow.objects.filter(
                follower=request.user,
                following=user_obj,
            ).exists()
        )

class AuthorWithRecipesSerializer(ProfileSerializer):
    recipes = serializers.SerializerMethodField()
    recipe_count = serializers.IntegerField(
        source="created_recipes.count",
        read_only=True,
    )

    class Meta(ProfileSerializer.Meta):
        fields = (*ProfileSerializer.Meta.fields, "recipes", "recipe_count")

    def get_recipes(self, author):
        max_results = int(
            self.context["request"].query_params.get("recipe_limit", 10**10)
        )
        queryset = author.created_recipes.all()[:max_results]
        return CompactRecipeSerializer(queryset, many=True).data

class RecipeDetailSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="name")
    description = serializers.CharField(source="text")
    prep_duration = serializers.IntegerField(source="cooking_time")

    author = ProfileSerializer(source="author", read_only=True)
    components = ComponentSerializer(
        source="components_amounts",
        many=True,
    )
    image = CustomBase64Field()

    in_favorites = serializers.SerializerMethodField()
    in_shopping_list = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            "id",
            "name",
            "description",
            "image",
            "author",
            "prep_duration",
            "components",
            "in_favorites",
            "in_shopping_list",
        )

    @staticmethod
    def _save_components(recipe_instance, components):
        RecipeComponent.objects.bulk_create(
            RecipeComponent(
                recipe=recipe_instance,
                ingredient=component["ingredient"],
                quantity=component["quantity"],
            )
            for component in components
        )

    def _check_status(self, model, recipe):
        request = self.context.get("request")
        return (
            request
            and request.user.is_authenticated
            and model.objects.filter(user=request.user, recipe=recipe).exists()
        )

    def get_in_favorites(self, obj):
        return self._check_status(Favorite, obj)

    def get_in_shopping_list(self, obj):
        return self._check_status(ShoppingList, obj)

    def create(self, validated_data):
        components = validated_data.pop("components_amounts", [])
        recipe = Recipe.objects.create(**validated_data)
        self._save_components(recipe, components)
        return recipe

    def update(self, instance, validated_data):
        components = validated_data.pop("components_amounts", [])
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        instance.components_amounts.all().delete()
        self._save_components(instance, components)
        return instance
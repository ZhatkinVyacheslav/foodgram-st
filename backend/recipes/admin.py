from django.contrib import admin

from recipes.models import (
    Ingredient,
    Dish,
    IngredientAmount,
    Favorite,
    ShoppingList,
)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ("name", "measurement_unit")  # Исправлено на measurement_unit
    list_filter = ("measurement_unit",)  # Исправлено на measurement_unit
    search_fields = ("name__startswith",)
    ordering = ("name",)


@admin.register(Dish)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "author", "favorites_count")
    search_fields = ("name__icontains", "author__username")
    list_filter = ("author", "pub_date")
    ordering = ("id",)

    @admin.display(description="Количество в избранном")
    def favorites_count(self, obj):
        return obj.favorited_by.count()


@admin.register(IngredientAmount)
class RecipeComponentAdmin(admin.ModelAdmin):
    list_display = ("recipe", "ingredient", "quantity")
    search_fields = (
        "recipe__name__icontains",
        "ingredient__name__icontains"
    )
    list_filter = ("ingredient",)


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("user", "recipe")
    list_filter = ("user",)
    search_fields = ("user__email", "recipe__name")


@admin.register(ShoppingList)
class ShoppingListAdmin(admin.ModelAdmin):
    list_display = ("user", "recipe")
    list_filter = ("user",)
    search_fields = ("user__email", "recipe__name")

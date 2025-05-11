import django_filters
from recipes.models import Ingredient, Recipe


class IngredientFilter(django_filters.FilterSet):
    """Фильтрация Ингредиентов"""
    query = django_filters.CharFilter(method='filter_by_name')
    name = django_filters.CharFilter(method='filter_by_name')
    search = django_filters.CharFilter(method='filter_by_name')

    class Meta:
        model = Ingredient
        fields = []

    def filter_by_name(self, queryset, name, value):
        """Фильтрация по начальной букве в имени ингредиента."""
        return queryset.filter(name__istartswith=value.lower())


class RecipeFilter(django_filters.FilterSet):
    """Фильтрация рецептов"""
    bookmarked = django_filters.BooleanFilter(method='filter_bookmarked')
    in_cart = django_filters.BooleanFilter(method='filter_in_cart')

    class Meta:
        model = Recipe
        fields = ['author', 'bookmarked', 'in_cart']

    def filter_bookmarked(self, queryset, name, value):
        """Фильтрация по избранным рецептам."""
        user = self.request.user
        if value and user.is_authenticated:
            return queryset.filter(favorited_by__user=user)
        return queryset

    def filter_in_cart(self, queryset, name, value):
        """Фильтрация по рецептам в корзине покупок."""
        user = self.request.user
        if value and user.is_authenticated:
            return queryset.filter(in_shopping_lists__user=user)
        return queryset

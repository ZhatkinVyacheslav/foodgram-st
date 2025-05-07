import logging
from collections import defaultdict

from django.http import FileResponse
from django.utils import timezone

from djoser.views import UserViewSet as BaseUserController
from djoser.serializers import UserCreateSerializer

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from recipes.models import Ingredient, Dish, Favorite, ShoppingList
from users.models import CustomUser, Follow

from .pagination import CustomPagination
from .serializers import (
    IngredientSerializer,
    RecipeSerializer,
    ShortRecipeSerializer,
    SubscribedAuthorSerializer,
    PublicUserSerializer,
)


class ComponentListView(viewsets.ReadOnlyModelViewSet):
    """Получение списка компонентов."""
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer  # <-- поменяли сериализатор
    pagination_class = None

    def get_queryset(self):
        """Фильтрация ингрединтов по запросу."""
        search_term = (
            self.request.query_params.get("query")
            or self.request.query_params.get("name")
            or self.request.query_params.get("search")
        )
        base_qs = super().get_queryset()
        if search_term:
            return base_qs.filter(name__istartswith=search_term.lower())
        return base_qs


class DishController(viewsets.ModelViewSet):
    """Управление рецептами и связанными действиями."""
    queryset = Dish.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    pagination_class = CustomPagination

    @staticmethod
    def _handle_bookmark(request, recipe_instance, relation_model):
        """Унифицированный метод для добавления/удаления из избранного или корзины."""
        if request.method == "POST":
            entry, created = relation_model.objects.get_or_create(
                user=request.user,
                recipe=recipe_instance,
            )
            if not created:
                raise ValidationError({"error": "Уже добавлено"})
            return Response(
                ShortRecipeSerializer(recipe_instance).data,
                status=status.HTTP_201_CREATED,
            )
        relation_model.objects.filter(
            user=request.user, recipe=recipe_instance
        ).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def filter_queryset(self, queryset):
        """Фильтрация рецептов."""
        filters = self.request.query_params
        filtered_qs = super().filter_queryset(queryset)

        if author_id := filters.get("creator"):
            filtered_qs = filtered_qs.filter(author_id=author_id)

        if filters.get("bookmarked") == "1" and self.request.user.is_authenticated:
            filtered_qs = filtered_qs.filter(favorited_by__user=self.request.user)

        if filters.get("in_cart") == "1" and self.request.user.is_authenticated:
            filtered_qs = filtered_qs.filter(in_shopping_lists__user=self.request.user)

        return filtered_qs

    def perform_create(self, serializer):
        """Сохранение рецепта с указанием автора."""
        try:
            serializer.save(author=self.request.user)
        except Exception as e:
            logger.error(f"Error creating recipe: {str(e)}")
            raise ValidationError({'detail': 'Ошибка при создании рецепта'})

    def create(self, request, *args, **kwargs):
        """Создание Рецепта."""
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as e:
            return Response(
                {"detail": "Проверьте обязательные поля", "errors": e.detail},
                status=status.HTTP_400_BAD_REQUEST
            )
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=["post", "delete"], url_path="favorite")
    def add_to_favorites(self, request, pk=None):
        """Добавление или удаление рецепт из избранного."""
        recipe = get_object_or_404(Dish, pk=pk)
        return self._handle_bookmark(request, recipe, Favorite)

    @action(detail=True, methods=["post", "delete"], url_path="shopping_cart")
    def manage_cart(self, request, pk=None):
        """Добавление или удаление рецепт из корзины покупок."""
        recipe = get_object_or_404(Dish, pk=pk)
        return self._handle_bookmark(request, recipe, ShoppingList)

    @action(detail=False, methods=["get"], url_path="download_shopping_cart")
    def export_shopping_list(self, request):
        """Экспорт списка покупок пользователя в текстовый файл."""
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Требуется авторизация"},
                status=status.HTTP_403_FORBIDDEN,
            )

        ingredient_totals = defaultdict(int)
        recipe_names = set()

        for cart_item in request.user.shopping_lists.select_related("recipe"):
            recipe_names.add(cart_item.recipe.name)
            for component in cart_item.recipe.components_amounts.select_related("ingredient"):
                key = (component.ingredient.name, component.ingredient.measurement_unit)
                ingredient_totals[key] += component.quantity

        current_date = timezone.localdate().strftime("%Y-%m-%d")
        report_lines = [
            f"Список покупок ({current_date}):",
            "Ингредиенты:",
        ]

        for idx, ((name, unit), total) in enumerate(sorted(ingredient_totals.items()), 1):
            report_lines.append(f"{idx}. {name.title()} ({unit}) — {total}")

        report_lines.append("\nИсточники рецептов:")
        for idx, name in enumerate(sorted(recipe_names), 1):
            report_lines.append(f"{idx}. {name}")

        file_content = "\n".join(report_lines)
        return FileResponse(
            file_content,
            content_type="text/plain",
            filename="grocery_list.txt",
        )


class AccountManager(BaseUserController):
    """
    Управление учетными записями и подписками.
    Теперь умеет обрабатывать POST /api/users/ через Djoser‑сериализатор регистрации.
    """
    queryset = CustomUser.objects.all()
    serializer_class = PublicUserSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    pagination_class = CustomPagination

    def create(self, request, *args, **kwargs):
        """Регистарция нового пользователя."""
        create_ser = UserCreateSerializer(data=request.data, context={'request': request})
        create_ser.is_valid(raise_exception=True)
        user = create_ser.save()

        output_ser = PublicUserSerializer(user, context={'request': request})
        return Response(output_ser.data, status=status.HTTP_201_CREATED)

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsAuthenticated],
        url_path="profile"
    )
    def current_profile(self, request):
        """Возврат данных текущего пользователя."""
        return Response(self.get_serializer(request.user).data)

    @action(detail=True, methods=["post", "delete"], url_path="subscribe")
    def follow_author(self, request, id=None):
        """Подписка/отписка."""
        target_user = get_object_or_404(CustomUser, pk=id)

        if target_user == request.user:
            raise ValidationError({"error": "Нельзя подписаться на самого себя"})

        if request.method == "POST":
            subscription, created = Follow.objects.get_or_create(
                follower=request.user,
                following=target_user,
            )
            if not created:
                raise ValidationError({"error": "Вы уже подписаны"})
            return Response(
                {"follower": subscription.follower.username, "following": target_user.username},
                status=status.HTTP_201_CREATED,
            )

        Follow.objects.filter(
            follower=request.user,
            following=target_user,
        ).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], url_path="subscriptions")
    def subscribed_list(self, request):
        """Возврат списка подписок."""
        if not request.user.is_authenticated:
            return Response(
                {"error": "Необходима авторизация"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        subscriptions = request.user.following.select_related("following")
        paginator = PageNumberPagination()
        paginator.page_size = int(request.query_params.get("limit", 6))
        page = paginator.paginate_queryset(subscriptions, request)

        authors = [sub.following for sub in page]
        serializer = SubscribedAuthorSerializer(
            authors,
            many=True,
            context={"request": request},
        )
        return paginator.get_paginated_response(serializer.data)
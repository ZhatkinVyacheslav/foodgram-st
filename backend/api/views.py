from collections import defaultdict

from django.db.models import Prefetch
from django.http import FileResponse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend

from djoser.serializers import UserCreateSerializer
from djoser.views import UserViewSet as BaseUserController

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import (
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response

from recipes.models import Ingredient, Recipe, Favorite, ShoppingList
from users.models import CustomUser, Follow
from .filters import IngredientFilter, RecipeFilter
from .pagination import CustomPagination
from .serializers import (
    IngredientSerializer,
    RecipeSerializer,
    CompactRecipeSerializer,
    SubscribedAuthorSerializer,
    PublicUserSerializer,
    ProfileImageSerializer,
)


class ComponentListController(viewsets.ReadOnlyModelViewSet):
    """Получение списка компонентов."""
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend]
    filterset_class = IngredientFilter


class RecipeController(viewsets.ModelViewSet):
    """Управление рецептами и связанными действиями."""
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    pagination_class = CustomPagination
    filterset_class = RecipeFilter

    def _handle_bookmark(self, request, recipe_instance, relation_model):
        """Унифицированный метод для 
        добавления/удаления из избранного или корзины."""
        if request.method == "POST":
            entry, created = relation_model.objects.get_or_create(
                user=request.user,
                recipe=recipe_instance,
            )
            if not created:
                raise ValidationError({"error": "Уже добавлено"})
            return Response(
                CompactRecipeSerializer(recipe_instance).data,
                status=status.HTTP_201_CREATED,
            )
        relation_model.objects.filter(
            user=request.user, recipe=recipe_instance
        ).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_create(self, serializer):
        """Сохранение рецепта с указанием автора."""
        serializer.save(author=self.request.user)

    @action(detail=True, methods=["post", "delete"],
            url_path="favorite", permission_classes=[IsAuthenticated])
    def add_to_favorites(self, request, pk=None):
        """Добавление или удаление рецепт из избранного."""
        recipe = get_object_or_404(Recipe, pk=pk)
        return self._handle_bookmark(request, recipe, Favorite)

    @action(detail=True, methods=["post", "delete"],
            url_path="shopping_cart", permission_classes=[IsAuthenticated])
    def manage_cart(self, request, pk=None):
        """Добавление или удаление рецепт из корзины покупок."""
        recipe = get_object_or_404(Recipe, pk=pk)
        return self._handle_bookmark(request, recipe, ShoppingList)

    @action(detail=False, methods=["get"], url_path="download_shopping_cart",
            permission_classes=[IsAuthenticated])
    def export_shopping_list(self, request):
        """Экспорт списка покупок пользователя в текстовый файл."""

        ingredient_totals = defaultdict(int)
        recipe_names = set()

        shopping_list = (request.user.shopping_lists
                .select_related("recipe")
                .prefetch_related("recipe__components_amounts__ingredient"))

        for cart_item in shopping_list:
            recipe_names.add(cart_item.recipe.name)
            for component in cart_item.recipe.components_amounts.all():
                key = (
                    component.ingredient.name,
                    component.ingredient.measurement_unit)
                ingredient_totals[key] += component.amount

        current_date = timezone.localdate().strftime("%Y-%m-%d")
        report_lines = [
            f"Список покупок ({current_date}):",
            "Ингредиенты:",
        ]

        for idx, ((name, unit), total) in enumerate(
                sorted(ingredient_totals.items()), 1):
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


class AccountController(BaseUserController):
    """
    Управление учетными записями и подписками.
    """
    queryset = CustomUser.objects.all()
    serializer_class = PublicUserSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    pagination_class = CustomPagination

    def create(self, request, *args, **kwargs):
        """Регистрация нового пользователя."""
        create_ser = UserCreateSerializer(
            data=request.data, context={
                'request': request})
        create_ser.is_valid(raise_exception=True)
        user = create_ser.save()

        output_ser = PublicUserSerializer(user, context={'request': request})
        return Response(output_ser.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"],
            permission_classes=[IsAuthenticated], url_path="profile")
    def current_profile(self, request):
        """Возврат данных текущего пользователя."""
        return Response(self.get_serializer(request.user).data)

    @action(detail=True, methods=["post", "delete"], url_path="subscribe")
    def follow_author(self, request, id=None):
        """Подписка/отписка."""
        target_user = get_object_or_404(CustomUser, pk=id)

        if target_user == request.user:
            raise ValidationError(
                {"error": "Нельзя подписаться на самого себя"})

        if request.method == "POST":
            subscription, created = Follow.objects.get_or_create(
                follower=request.user,
                following=target_user,
            )
            if not created:
                return Response(
                    {"follower": subscription.follower.username,
                        "following": target_user.username},
                    status=status.HTTP_200_OK
                )

            return Response(
                {"follower": subscription.follower.username,
                    "following": target_user.username},
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

        subscriptions = CustomUser.objects.prefetch_related(
            Prefetch(
                "following",
                queryset=Follow.objects.filter(follower=request.user),
                to_attr="subscribed_authors"
            )
        ).filter(following__follower=request.user)
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

    @action(
        detail=False,
        methods=["put"],
        permission_classes=[IsAuthenticated],
        url_path="me/avatar",
        parser_classes=[JSONParser, MultiPartParser, FormParser],
    )
    def update_profile_image (self, request):
        user = CustomUser.objects.get(pk=request.user.pk)
        serializer = ProfileImageSerializer(
            user, data=request.data, partial=True, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

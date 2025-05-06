from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ComponentListView   as IngredientViewSet,
    DishController      as RecipeViewSet,
    AccountManager      as UserViewSet,
)

router = DefaultRouter()
router.register(r"users",       UserViewSet,       basename="users")
router.register(r"ingredients", IngredientViewSet, basename="ingredients")
router.register(r"recipes",     RecipeViewSet,     basename="recipes")

urlpatterns = [
    # — ваши собственные ViewSets:
    path("", include(router.urls)),

    # — Djoser base‑endpoints: реализация POST /api/users/, GET /api/users/me/ и т.д.
    path("", include("djoser.urls")),

    # — Djoser token‑auth: POST /api/token/login/, POST /api/token/logout/
    path("auth/", include("djoser.urls.authtoken")),

    # — короткая ссылка на рецепт
    path(
        "s/<int:pk>/",
        RecipeViewSet.as_view({"get": "get_short_link"}),
        name="recipe-short-link",
    ),
]
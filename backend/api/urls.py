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
    path("", include(router.urls)),

    path("", include("djoser.urls")),

    path("auth/", include("djoser.urls.authtoken")),

    path(
        "s/<int:pk>/",
        RecipeViewSet.as_view({"get": "get_short_link"}),
        name="recipe-short-link",
    ),
]
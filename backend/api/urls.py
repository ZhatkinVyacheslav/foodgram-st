from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ComponentListController   as IngredientViewSet,
    DishController      as RecipeViewSet,
    AccountController      as UserViewSet,
)

router = DefaultRouter()
router.register(r"users",       UserViewSet,       basename="users")
router.register(r"ingredients", IngredientViewSet, basename="ingredients")
router.register(r"recipes",     RecipeViewSet,     basename="recipes")

urlpatterns = [
    path("", include(router.urls)),
    path("auth/", include("djoser.urls.authtoken")),
]
from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator
from django.db import models
from users.models import CustomUser


class Ingredient(models.Model):
    """Модель для хранения данных об ингредиентах."""
    name = models.CharField(
        max_length=128,
        db_index=True,
        verbose_name="Наименование"
    )
    measurement_unit = models.CharField(
        max_length=64,
        verbose_name="Единица измерения"
    )

    class Meta:
        ordering = ("name",)
        verbose_name = "Компонент"
        verbose_name_plural = "Компоненты"
        constraints = [
            models.UniqueConstraint(
                fields=["name", "measurement_unit"],
                name="ingredient_name_unit_unique"
            )
        ]

    def __str__(self):
        return f"{self.name}, {self.measurement_unit}"


class Dish(models.Model):
    """Модель рецептов."""
    name = models.CharField(
        max_length=256,
        verbose_name="Наименование блюда"
    )
    text = models.TextField(verbose_name="Текст рецепта")
    image = models.ImageField(
        upload_to="recipes/images/",
        validators=[FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png"])],
        verbose_name="Изображение"
    )
    author = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="created_dishes",
        verbose_name="Создатель"
    )
    cooking_time = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(600)],
        verbose_name="Время готовки (мин)"
    )
    components = models.ManyToManyField(
        Ingredient,
        through="IngredientAmount",
        related_name="used_in_dishes"
    )
    pub_date = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name="Дата создания"
    )


class IngredientAmount(models.Model):
    """Связующая модель для ингредиентов в рецепте."""
    recipe = models.ForeignKey(
        Dish,
        on_delete=models.CASCADE,
        related_name="components_amounts"
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name="recipes_amounts"
    )
    quantity = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Количество (в единицах измерения ингредиента)"
    )

    class Meta:
        verbose_name = "Ингредиент в рецепте"
        verbose_name_plural = "Ингредиенты в рецептах"
        constraints = [
            models.UniqueConstraint(
                fields=["recipe", "ingredient"],
                name="recipe_ingredient_unique"
            )
        ]

    def __str__(self):
        return f"{self.quantity} {self.ingredient.measurement_unit} {self.ingredient.name}"


class Favorite(models.Model):
    """Модель для избранных рецептов."""
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="favorites"
    )
    recipe = models.ForeignKey(
        Dish,
        on_delete=models.CASCADE,
        related_name="favorited_by"
    )

    class Meta:
        verbose_name = "Избранное"
        verbose_name_plural = "Избранные"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "recipe"],
                name="user_favorite_recipe_unique"
            )
        ]

    def __str__(self):
        return f"{self.user.username} - {self.recipe.name}"


class ShoppingList(models.Model):
    """Модель списка покупок."""
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="shopping_lists"
    )
    recipe = models.ForeignKey(
        Dish,
        on_delete=models.CASCADE,
        related_name="in_shopping_lists"
    )

    class Meta:
        verbose_name = "Список покупок"
        verbose_name_plural = "Списки покупок"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "recipe"],
                name="user_shopping_recipe_unique"
            )
        ]

    def __str__(self):
        return f"Покупки {self.user.username} для {self.recipe.name}"
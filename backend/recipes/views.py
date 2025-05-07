from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from django.shortcuts import get_object_or_404
from recipes.models import Dish, Favorite, ShoppingList
from recipes.serializers import RecipeSerializer, CompactRecipeSerializer
from api.pagination import CustomPagination


class RecipeViewSet(viewsets.ModelViewSet):
    """API endpoint для работы с рецептами."""
    
    queryset = Dish.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = CustomPagination

    def get_queryset(self):
        """Возвращает отфильтрованный список рецептов."""
        queryset = super().get_queryset()
        author_id = self.request.query_params.get('author')
        
        if author_id:
            queryset = queryset.filter(author__id=author_id)
            
        return queryset.select_related('author').prefetch_related(
            'components', 'recipe_ingredients__ingredient'
        )

    def perform_create(self, serializer):
        """Создает рецепт с текущим пользователем в качестве автора."""
        try:
            serializer.save(author=self.request.user)
        except Exception as e:
            logger.error(f"Error creating recipe: {str(e)}")
            raise ValidationError({'detail': 'Ошибка при создании рецепта'})

    @staticmethod
    def _modify_recipe_list(request, recipe, relation_model):
        """Общий метод для управления списками рецептов."""
        if request.method == 'POST':
            if relation_model.objects.filter(
                user=request.user, 
                recipe=recipe
            ).exists():
                raise ValidationError(
                    {'detail': 'Рецепт уже добавлен'},
                    code=status.HTTP_400_BAD_REQUEST
                )
                
            relation_model.objects.create(user=request.user, recipe=recipe)
            return Response(
                CompactRecipeSerializer(recipe).data,
                status=status.HTTP_201_CREATED
            )
            
        relation_model.objects.filter(
            user=request.user,
            recipe=recipe
        ).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticatedOrReadOnly],
        url_path='favorite'
    )
    def favorite_recipe(self, request, pk=None):
        """Добавляет или удаляет рецепт из избранного."""
        recipe = get_object_or_404(Dish, pk=pk)
        return self._modify_recipe_list(request, recipe, Favorite)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticatedOrReadOnly],
        url_path='shopping-list'
    )
    def shopping_list(self, request, pk=None):
        """Добавляет или удаляет рецепт из списка покупок."""
        recipe = get_object_or_404(Dish, pk=pk)
        return self._modify_recipe_list(request, recipe, ShoppingList)
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as e:
            return Response(
                {"detail": "Проверьте обязательные поля", "errors": e.detail},
                status=status.HTTP_400_BAD_REQUEST
            )
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
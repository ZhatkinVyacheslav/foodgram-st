from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly

from users.models import CustomUser, Follow
from users.serializers import (
    CustomUserSerializer,
    FollowSerializer,
    BasicUserSerializer
)


class CustomUserViewSet(viewsets.ModelViewSet):
    """API endpoint для управления профилями пользователей."""
    
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = None

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """Получение данных текущего пользователя."""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['put', 'delete'], url_path='me/avatar')
    def profile_image(self, request):
        """Обновить или удалить изображение профиля пользователя."""
        user = request.user
        
        if request.method == 'PUT':
            serializer = self.get_serializer(
                user,
                data=request.data,
                partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(
                {'profile_image': serializer.data['profile_image']},
                status=status.HTTP_200_OK
            )
        
        # DELETE method
        user.profile_image.delete()
        return Response(
            {'detail': 'Профиль успешно удалён'},
            status=status.HTTP_204_NO_CONTENT
        )

    @action(detail=True, methods=['post', 'delete'], url_path='subscribe')
    def follow(self, request, pk=None):
        """Подписаться или отписаться от других пользователей"""
        following_user = get_object_or_404(CustomUser, pk=pk)
        
        if following_user == request.user:
            raise ValidationError(
                {'detail': 'Вы не можете подписаться на самого себя'}
            )

        if request.method == 'POST':
            if Follow.objects.filter(follower=request.user, following=following_user).exists():
                raise ValidationError(
                    {'detail': 'Вы уже подписаны на этого пользователя'}
                )
                
            Follow.objects.create(follower=request.user, following=following_user)
            return Response(
                BasicUserSerializer(following_user, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )
        
        # DELETE method
        follow = get_object_or_404(
            Follow,
            follower=request.user,
            following=following_user
        )
        follow.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], url_path='subscriptions')
    def following(self, request):
        """Список всех пользователей на которых подписан текущий пользователь."""
        following_users = request.user.following.select_related('following')
        serializer = FollowSerializer(
            [follow.following for follow in following_users],
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)


class BasicUserViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint для базовой информации о пользователе."""
    
    queryset = CustomUser.objects.all()
    serializer_class = BasicUserSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    @action(detail=False, methods=['get'], url_path='me')
    def current_user(self, request):
        """Получение информации о текущем пользователе."""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from users.models import CustomUser, Follow


@admin.register(CustomUser)
class ExtendedUserAdmin(UserAdmin):
    """Расширенная административная панель для пользователей."""
    
    list_display = (
        'pk',
        'email',
        'username',
        'first_name',
        'last_name',
        'is_active',
    )
    search_fields = (
        'email__icontains',
        'username__icontains',
        'first_name__icontains',
        'last_name__icontains'
    )
    list_filter = ('is_active', 'is_staff', 'is_superuser')
    ordering = ('email',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('username', 'first_name', 'last_name')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )


@admin.register(Follow)
class SubscriptionAdmin(admin.ModelAdmin):
    """Администрирование подписок пользователей."""
    
    list_display = ('follower', 'following', 'created_at')
    search_fields = (
        'follower__email',
        'following__email',
        'follower__username',
        'following__username'
    )
    list_filter = ('created_at',)
    readonly_fields = ('created_at',)
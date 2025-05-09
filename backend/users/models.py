from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _


class CustomUser(AbstractUser):
    """Кастомная модель пользователя с дополнительными полями."""

    email = models.EmailField(
        _('email address'),
        unique=True,
        max_length=settings.MAX_LENGHTH_EMAIL,
        help_text=_('Required. 254 characters or fewer.')
    )
    username = models.CharField(
        _('username'),
        max_length=settings.MAX_LENGHTH_NAME,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^[\w.@+-]+\Z',
                message=_('Allowed characters: letters, digits and @/./+/-/_'),
            )
        ],
        help_text=_(
            '150 characters or fewer. Letters, digits and @/./+/-/_ only.')
    )
    first_name = models.CharField(
        _('first name'),
        max_length=settings.MAX_LENGHTH_NAME,
        blank=True
    )
    last_name = models.CharField(
        _('last name'),
        max_length=settings.MAX_LENGHTH_NAME,
        blank=True
    )
    profile_image = models.ImageField(
        _('profile image'),
        upload_to='users/profile_images/',
        blank=True,
        null=True
    )
    registration_date = models.DateTimeField(
        _('registration date'),
        auto_now_add=True
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ('-registration_date',)
        constraints = [
            models.UniqueConstraint(
                fields=['email', 'username'],
                name='unique_email_username'
            )
        ]

    def __str__(self):
        return f'{self.email} ({self.username})'


class Follow(models.Model):
    """Модель для отслеживания подписок пользователей."""

    follower = models.ForeignKey(
        CustomUser,
        related_name='following',
        on_delete=models.CASCADE,
        verbose_name=_('Follower')
    )
    following = models.ForeignKey(
        CustomUser,
        related_name='followers',
        on_delete=models.CASCADE,
        verbose_name=_('Following')
    )
    created_at = models.DateTimeField(
        _('Follow date'),
        auto_now_add=True
    )

    class Meta:
        verbose_name = _('Follow')
        verbose_name_plural = _('Follows')
        constraints = [
            models.UniqueConstraint(
                fields=['follower', 'following'],
                name='unique_follow'
            ),
            models.CheckConstraint(
                check=~models.Q(follower=models.F('following')),
                name='prevent_self_follow'
            )
        ]

    def __str__(self):
        return (
            f'{self.follower.username} '
            f'подписан на {self.following.username}'
        )

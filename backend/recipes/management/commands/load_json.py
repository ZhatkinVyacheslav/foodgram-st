import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Загрузка данных об ингредиентах из JSON файла в БД'

    def handle(self, *args, **kwargs):
        ingredients_file = Path(settings.BASE_DIR) / 'data' / 'ingredients.json'

        if not ingredients_file.is_file():
            self.stderr.write(self.style.ERROR(f'Файл не обнаружен: {ingredients_file}'))
            return

        try:
            with open(ingredients_file, 'r', encoding='utf-8') as f:
                ingredients_data = json.load(f)
        except Exception as error:
            self.stderr.write(self.style.ERROR(f'Ошибка обработки JSON: {error}'))
            return

        ingredient_instances = [Ingredient(**item) for item in ingredients_data]
        saved_items = Ingredient.objects.bulk_create(ingredient_instances)

        items_count = len(saved_items)
        self.stdout.write(self.style.SUCCESS(f"Успешно импортировано {items_count} записей."))

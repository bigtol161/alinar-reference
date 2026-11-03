from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.crypto import get_random_string


class District(models.Model):
    name = models.CharField('Район', max_length=64, unique=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Район'
        verbose_name_plural = 'Районы'

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField('Название', max_length=80)
    short = models.CharField('Короткое имя', max_length=40)
    slug = models.SlugField('Слаг', max_length=40, unique=True)
    icon = models.CharField('Иконка', max_length=20, default='wrench')
    description = models.CharField('Описание', max_length=160, blank=True)
    sort_order = models.PositiveIntegerField('Порядок', default=100)

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

    def __str__(self):
        return self.name


class Master(models.Model):
    name = models.CharField('Имя', max_length=120)
    slug = models.SlugField('Слаг', max_length=160, unique=True)
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name='masters', verbose_name='Категория'
    )
    title = models.CharField('Специализация', max_length=120)
    districts = models.ManyToManyField(
        District, related_name='masters', verbose_name='Районы работы', blank=True
    )
    price_from = models.PositiveIntegerField('Цена от, ₽', default=0)
    rating = models.FloatField('Рейтинг', default=0)
    reviews_count = models.PositiveIntegerField('Отзывов', default=0)
    experience = models.PositiveIntegerField('Опыт, лет', default=0)
    verified = models.BooleanField('Документы подтверждены', default=False)
    online = models.BooleanField('Сейчас онлайн', default=False)
    completed = models.PositiveIntegerField('Выполненных заказов', default=0)
    phone = models.CharField('Телефон', max_length=32)
    about = models.TextField('О себе', blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='master_profile',
        verbose_name='Аккаунт',
    )
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    class Meta:
        ordering = ['-rating', '-reviews_count']
        verbose_name = 'Мастер'
        verbose_name_plural = 'Мастера'

    def __str__(self):
        return '{} — {}'.format(self.name, self.title)

    @property
    def rating_percent(self):
        return max(0, min(100, int(round(self.rating / 5 * 100))))

    @property
    def is_new(self):
        return self.reviews_count == 0


class Service(models.Model):
    master = models.ForeignKey(
        Master, on_delete=models.CASCADE, related_name='services', verbose_name='Мастер'
    )
    name = models.CharField('Услуга', max_length=140)
    price = models.PositiveIntegerField('Цена, ₽', default=0)
    sort_order = models.PositiveIntegerField('Порядок', default=100)

    class Meta:
        ordering = ['sort_order', 'pk']
        verbose_name = 'Услуга'
        verbose_name_plural = 'Услуги'

    def __str__(self):
        return self.name


class Review(models.Model):
    master = models.ForeignKey(
        Master, on_delete=models.CASCADE, related_name='reviews', verbose_name='Мастер'
    )
    author = models.CharField('Автор', max_length=80)
    rating = models.PositiveSmallIntegerField(
        'Оценка', validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    text = models.TextField('Отзыв')
    created_at = models.DateTimeField('Дата', auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'

    def __str__(self):
        return '{} — {}★'.format(self.author, self.rating)


class ServiceRequest(models.Model):
    STATUS_NEW = 'new'
    STATUS_PROGRESS = 'in_progress'
    STATUS_DONE = 'done'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_NEW, 'Новая'),
        (STATUS_PROGRESS, 'В работе'),
        (STATUS_DONE, 'Выполнена'),
        (STATUS_CANCELLED, 'Отменена'),
    ]

    number = models.CharField('Номер', max_length=16, unique=True)
    category = models.ForeignKey(
        Category, null=True, blank=True, on_delete=models.SET_NULL, related_name='requests'
    )
    master = models.ForeignKey(
        Master, null=True, blank=True, on_delete=models.SET_NULL, related_name='requests'
    )
    service = models.CharField('Услуга', max_length=160, blank=True)
    name = models.CharField('Имя', max_length=120)
    phone = models.CharField('Телефон', max_length=32)
    district = models.ForeignKey(
        District, null=True, blank=True, on_delete=models.SET_NULL, related_name='requests'
    )
    desired_date = models.DateField('Желаемая дата', null=True, blank=True)
    budget = models.PositiveIntegerField('Бюджет, ₽', null=True, blank=True)
    comment = models.TextField('Комментарий', blank=True)
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default=STATUS_NEW)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='requests',
        verbose_name='Клиент',
    )
    created_at = models.DateTimeField('Создана', auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Заявка'
        verbose_name_plural = 'Заявки'

    def __str__(self):
        return '{} — {}'.format(self.number, self.service or self.category)

    def save(self, *args, **kwargs):
        if not self.number:
            self.number = 'NT-' + get_random_string(6, '0123456789ABCDEFGHJKMNPQRSTUVWXYZ')
        super().save(*args, **kwargs)

    @property
    def status_display_cls(self):
        return {
            self.STATUS_NEW: 'b-blue',
            self.STATUS_PROGRESS: 'b-amber',
            self.STATUS_DONE: 'b-green',
            self.STATUS_CANCELLED: 'b-grey',
        }.get(self.status, 'b-grey')

import json

from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import MasterForm, RequestForm, ReviewForm, SignInForm, SignUpForm
from .models import Category, District, Master, Review, Service, ServiceRequest
from .utils import digits_only, fmt_phone, slugify_ru
from django.utils.crypto import get_random_string

PAGE_SIZE = 9

SORTS = {
    'rating': ('По рейтингу', ['-rating', '-reviews_count']),
    'reviews': ('По отзывам', ['-reviews_count', '-rating']),
    'price_asc': ('Сначала дешевле', ['price_from']),
    'price_desc': ('Сначала дороже', ['-price_from']),
    'exp': ('По опыту', ['-experience', '-rating']),
}


def index(request):
    categories = Category.objects.annotate(n=Count('masters'))
    top = (
        Master.objects.filter(reviews_count__gt=0)
        .select_related('category')
        .prefetch_related('districts')[:6]
    )
    agg = Master.objects.aggregate(avg=Avg('rating'), reviews=Count('reviews_count'))
    context = {
        'categories': categories,
        'top_masters': top,
        'masters_total': Master.objects.count(),
        'reviews_total': Master.objects.aggregate(s=Count('reviews_count'))['s'] or 0,
        'avg_rating': round(agg['avg'] or 0, 1),
    }
    return render(request, 'index.html', context)


def catalog(request):
    params = request.GET
    masters = Master.objects.select_related('category').prefetch_related('districts', 'services')

    filters = {
        'q': (params.get('q') or '').strip(),
        'cat': params.get('cat') or '',
        'district': params.get('district') or '',
        'min': params.get('min') or '',
        'max': params.get('max') or '',
        'rating': params.get('rating') or '',
        'verified': params.get('verified') == '1',
        'online': params.get('online') == '1',
        'sort': params.get('sort') if params.get('sort') in SORTS else 'rating',
    }

    if filters['q']:
        q = filters['q']
        masters = masters.filter(
            Q(name__icontains=q)
            | Q(title__icontains=q)
            | Q(about__icontains=q)
            | Q(category__name__icontains=q)
            | Q(services__name__icontains=q)
        ).distinct()
    if filters['cat']:
        masters = masters.filter(category__slug=filters['cat'])
    if filters['district']:
        masters = masters.filter(districts__pk=filters['district'])
    if filters['min']:
        masters = masters.filter(price_from__gte=filters['min'])
    if filters['max']:
        masters = masters.filter(price_from__lte=filters['max'])
    if filters['rating']:
        masters = masters.filter(rating__gte=filters['rating'])
    if filters['verified']:
        masters = masters.filter(verified=True)
    if filters['online']:
        masters = masters.filter(online=True)

    masters = masters.order_by(*SORTS[filters['sort']][1]).distinct()

    paginator = Paginator(masters, PAGE_SIZE)
    page_obj = paginator.get_page(params.get('page'))

    query = request.GET.copy()
    query.pop('page', None)
    context = {
        'page_obj': page_obj,
        'total': paginator.count,
        'categories': Category.objects.all(),
        'districts': District.objects.all(),
        'filters': filters,
        'sorts': SORTS,
        'qs': query.urlencode(),
        'active_category': Category.objects.filter(slug=filters['cat']).first(),
    }
    return render(request, 'catalog.html', context)


def master_detail(request, slug):
    master = get_object_or_404(
        Master.objects.select_related('category').prefetch_related('districts', 'services'),
        slug=slug,
    )
    reviews = master.reviews.all()

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.master = master
            if request.user.is_authenticated and not review.author.strip():
                review.author = request.user.first_name or 'Пользователь'
            if not review.author.strip():
                review.author = 'Гость'
            review.save()
            total = master.reviews_count
            master.rating = round((master.rating * total + review.rating) / (total + 1), 2)
            master.reviews_count += 1
            master.save(update_fields=['rating', 'reviews_count'])
            messages.success(request, 'Спасибо! Ваш отзыв опубликован.')
            return redirect(reverse('core:master', args=[master.slug]) + '#reviews')
        messages.error(request, 'Проверьте заполнение полей отзыва.')
    else:
        initial = {}
        if request.user.is_authenticated:
            initial['author'] = request.user.first_name
        form = ReviewForm(initial=initial)

    similar = (
        Master.objects.filter(category=master.category)
        .exclude(pk=master.pk)
        .select_related('category')
        .prefetch_related('districts')[:3]
    )
    return render(request, 'master.html', {
        'master': master,
        'reviews': reviews,
        'form': form,
        'similar': similar,
    })


def request_create(request, master_slug=None):
    master = None
    if master_slug:
        master = get_object_or_404(Master, slug=master_slug)

    initial = {}
    if master:
        initial.update({'category': master.category_id, 'service': master.title})
    if request.user.is_authenticated:
        initial.setdefault('name', request.user.first_name)
        initial.setdefault('phone', fmt_phone(request.user.username))

    created = None
    if request.method == 'POST':
        form = RequestForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.master = master
            if request.user.is_authenticated:
                obj.user = request.user
            obj.save()
            created = obj
            form = None
    else:
        form = RequestForm(initial=initial)

    return render(request, 'request.html', {
        'form': form,
        'master': master,
        'created': created,
    })


@login_required
def become_master(request):
    profile = request.user.master_profile.first()
    if profile:
        messages.info(request, 'Вы уже зарегистрированы как мастер.')
        return redirect('core:master', slug=profile.slug)

    form = MasterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        master = form.save(commit=False)
        master.slug = slugify_ru(master.name) + '-' + get_random_string(4, 'abcdefgh23456789')
        master.online = True
        master.user = request.user
        master.save()
        form.save_m2m()
        added = 0
        for i in (1, 2, 3):
            sname = (request.POST.get('service_name_{}'.format(i)) or '').strip()
            if not sname:
                continue
            try:
                sprice = int(request.POST.get('service_price_{}'.format(i)) or 0)
            except ValueError:
                sprice = 0
            Service.objects.create(master=master, name=sname, price=max(0, sprice), sort_order=i)
            added += 1
        if not added:
            Service.objects.create(
                master=master, name='Услуга по договорённости', price=master.price_from, sort_order=1
            )
        messages.success(request, 'Профиль мастера создан и уже виден в каталоге!')
        return redirect('core:master', slug=master.slug)

    return render(request, 'become_master.html', {'form': form, 'districts': District.objects.all()})


@login_required
def account(request):
    tab = request.GET.get('tab', 'requests')
    if tab not in ('requests', 'responses', 'profile'):
        tab = 'requests'

    my_requests = ServiceRequest.objects.filter(
        Q(user=request.user) | Q(phone=request.user.username)
    ).distinct().select_related('category', 'master', 'district')

    blocks = []
    for req in my_requests:
        if req.status in (ServiceRequest.STATUS_DONE, ServiceRequest.STATUS_CANCELLED):
            blocks.append({'request': req, 'responses': []})
            continue
        candidates = Master.objects.select_related('category').prefetch_related('districts')
        if req.category:
            candidates = candidates.filter(category=req.category)
        candidates = candidates.order_by('-rating', '-reviews_count')[:3]
        responses = []
        for m in candidates:
            templates = [
                'Свободен уже сегодня, могу подъехать после 15:00.',
                'Готов взяться, цена ориентировочная, приеду в удобное время.',
                'Сделаю качественно и с гарантией, есть отзывы по похожим заказам.',
            ]
            responses.append({
                'master': m,
                'message': templates[m.pk % len(templates)],
                'price': m.price_from,
            })
        blocks.append({'request': req, 'responses': responses})

    return render(request, 'account.html', {
        'tab': tab,
        'blocks': blocks,
        'my_requests': my_requests,
        'profile': request.user.master_profile.first(),
    })


@login_required
@require_POST
def cancel_request(request, pk):
    req = get_object_or_404(ServiceRequest, pk=pk)
    if req.user_id == request.user.id or req.phone == request.user.username:
        if req.status not in (ServiceRequest.STATUS_DONE, ServiceRequest.STATUS_CANCELLED):
            req.status = ServiceRequest.STATUS_CANCELLED
            req.save(update_fields=['status'])
            messages.info(request, 'Заявка {} отменена.'.format(req.number))
    return redirect('core:account')


def sign_up(request):
    if request.user.is_authenticated:
        return redirect('core:account')
    form = SignUpForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        phone = form.cleaned_data['phone']
        if User.objects.filter(username=phone).exists():
            form.add_error('phone', 'Этот телефон уже зарегистрирован. Войдите в кабинет.')
        else:
            user = User.objects.create_user(
                username=phone,
                password=form.cleaned_data['password1'],
                first_name=form.cleaned_data['name'],
            )
            auth_login(request, user)
            messages.success(request, 'Добро пожаловать! Аккаунт создан.')
            return redirect('core:account')
    return render(request, 'auth_register.html', {'form': form})


def sign_in(request):
    if request.user.is_authenticated:
        return redirect('core:account')
    form = SignInForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data['phone'],
            password=form.cleaned_data['password'],
        )
        if user:
            auth_login(request, user)
            messages.success(request, 'Вы вошли в личный кабинет.')
            return redirect(request.GET.get('next') or 'core:account')
        form.add_error(None, 'Неверный телефон или пароль.')
    return render(request, 'auth_login.html', {'form': form})


@require_POST
def sign_out(request):
    auth_logout(request)
    return redirect('core:index')


def suggest(request):
    q = (request.GET.get('q') or '').strip().lower()
    if len(q) < 2:
        return JsonResponse({'results': []})

    results = []

    for cat in Category.objects.filter(Q(name__icontains=q) | Q(short__icontains=q))[:3]:
        results.append({
            'type': 'Категория',
            'label': cat.name,
            'sub': cat.description,
            'url': reverse('core:catalog') + '?cat=' + cat.slug,
        })

    seen = set()
    services = (
        Service.objects.filter(name__icontains=q)
        .select_related('master')
        .order_by('name')
    )
    for s in services:
        if s.name.lower() in seen:
            continue
        seen.add(s.name.lower())
        results.append({
            'type': 'Услуга',
            'label': s.name,
            'sub': s.master.title,
            'url': reverse('core:catalog') + '?q=' + s.name,
        })
        if len(results) >= 8:
            break

    for m in Master.objects.filter(Q(name__icontains=q) | Q(title__icontains=q)).select_related('category')[:4]:
        results.append({
            'type': 'Мастер',
            'label': '{} — {}'.format(m.name, m.title),
            'sub': m.category.name,
            'url': reverse('core:master', args=[m.slug]),
        })
        if len(results) >= 8:
            break

    return JsonResponse({'results': results})

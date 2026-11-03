import re

TRANSLIT = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'h', 'ц': 'c', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
    'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
}


def digits_only(value):
    return re.sub(r'\D', '', value or '')


def fmt_phone(value):
    digits = digits_only(value)
    if len(digits) == 11 and digits[0] in '78':
        d = '7' + digits[1:]
        return '+7 ({}) {}-{}-{}'.format(d[1:4], d[4:7], d[7:9], d[9:11])
    return value or ''


def slugify_ru(value):
    value = (value or '').strip().lower()
    result = []
    for ch in value:
        if ch in TRANSLIT:
            result.append(TRANSLIT[ch])
        elif ch.isascii() and (ch.isalnum() or ch in '-_'):
            result.append(ch)
        else:
            result.append('-')
    slug = re.sub(r'-{2,}', '-', ''.join(result)).strip('-')
    return slug or 'master'

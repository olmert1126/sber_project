# site_blocker.py
import os
import socket
from pathlib import Path

HOSTS_FILE = Path(os.environ['SystemRoot']) / 'System32' / 'drivers' / 'etc' / 'hosts'
BACKUP_SUFFIX = '.backup_appblocker'
BLOCK_IP = '0.0.0.0'  # Перенаправляем на "никуда"

# Маркеры для безопасного редактирования
MARKER_START = '# >>> APP_BLOCKER_START <<<\n'
MARKER_END = '# >>> APP_BLOCKER_END <<<\n'


def is_valid_domain(domain: str) -> bool:
    """Проверка корректности домена"""
    if not domain or len(domain) > 253:
        return False
    domain = domain.lower().strip()
    if domain.startswith(('http://', 'https://', 'www.')):
        domain = domain.replace('http://', '').replace('https://', '').replace('www.', '', 1)
    domain = domain.split('/')[0].split('?')[0].split('#')[0]
    try:
        socket.inet_aton(domain)
        return False  # Это IP, а не домен
    except socket.error:
        pass
    allowed = set('abcdefghijklmnopqrstuvwxyz0123456789-.')
    return all(c in allowed for c in domain) and domain.count('.') >= 1


def normalize_domain(domain: str) -> str:
    """Приводим домен к единому формату"""
    domain = domain.lower().strip()
    for prefix in ('http://', 'https://'):
        domain = domain.replace(prefix, '')
    domain = domain.replace('www.', '', 1) if domain.startswith('www.') else domain
    domain = domain.split('/')[0].split('?')[0].split('#')[0]
    return domain


def get_blocked_domains() -> set:
    """Читаем заблокированные домены из hosts"""
    blocked = set()
    if not HOSTS_FILE.exists():
        return blocked
    try:
        with open(HOSTS_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        if MARKER_START in content and MARKER_END in content:
            section = content.split(MARKER_START)[1].split(MARKER_END)[0]
            for line in section.strip().split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = line.split()
                    if len(parts) >= 2 and parts[0] == BLOCK_IP:
                        domain = parts[1]
                        if not domain.startswith('localhost'):
                            blocked.add(domain)
    except Exception:
        pass
    return blocked


def update_hosts_file(domains: set):
    """Записывает список доменов в hosts с маркерами"""
    original_content = ""
    if HOSTS_FILE.exists():
        with open(HOSTS_FILE, 'r', encoding='utf-8') as f:
            original_content = f.read()

    # Создаём бэкап при первом запуске
    if not HOSTS_FILE.with_suffix(HOSTS_FILE.suffix + BACKUP_SUFFIX).exists():
        try:
            with open(HOSTS_FILE, 'rb') as src, open(HOSTS_FILE.with_suffix(HOSTS_FILE.suffix + BACKUP_SUFFIX),
                                                     'wb') as dst:
                dst.write(src.read())
        except:
            pass  # Не критично

    # Удаляем старый блок приложения
    if MARKER_START in original_content and MARKER_END in original_content:
        new_content = original_content.split(MARKER_START)[0] + original_content.split(MARKER_END)[1]
    else:
        new_content = original_content.rstrip('\n') + '\n'

    # Добавляем новый блок
    if domains:
        block = MARKER_START
        for d in sorted(domains):
            block += f"{BLOCK_IP} {d}\n"
            block += f"{BLOCK_IP} www.{d}\n"  # Блокируем и с www
        block += MARKER_END
        new_content += block

    with open(HOSTS_FILE, 'w', encoding='utf-8') as f:
        f.write(new_content.rstrip() + '\n')

    # Очистка DNS-кэша
    try:
        os.system('ipconfig /flushdns >nul 2>&1')
    except:
        pass
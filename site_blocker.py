# site_blocker.py (ОБНОВЛЁННАЯ ВЕРСИЯ)
import os
import socket
from pathlib import Path

HOSTS_FILE = Path(os.environ['SystemRoot']) / 'System32' / 'drivers' / 'etc' / 'hosts'
BACKUP_SUFFIX = '.backup_appblocker'
BLOCK_IP = '0.0.0.0'

MARKER_START = '# >>> APP_BLOCKER_START <<<\n'
MARKER_END = '# >>> APP_BLOCKER_END <<<\n'

# Дополнительные домены для популярных сайтов (включая зеркала)
SITE_MIRRORS = {
    'vk.com': ['vk.com', 'www.vk.com', 'm.vk.com', 'api.vk.com'],
    'youtube.com': ['youtube.com', 'www.youtube.com', 'm.youtube.com', 'youtu.be'],
    'ok.ru': ['ok.ru', 'www.ok.ru', 'm.ok.ru'],
    'facebook.com': ['facebook.com', 'www.facebook.com', 'm.facebook.com', 'fb.com'],
    'instagram.com': ['instagram.com', 'www.instagram.com', 'm.instagram.com'],
    'twitter.com': ['twitter.com', 'www.twitter.com', 'mobile.twitter.com'],
    'tiktok.com': ['tiktok.com', 'www.tiktok.com', 'm.tiktok.com'],
}


def is_valid_domain(domain: str) -> bool:
    if not domain or len(domain) > 253:
        return False
    domain = domain.lower().strip()
    for prefix in ('http://', 'https://'):
        domain = domain.replace(prefix, '')
    domain = domain.replace('www.', '', 1) if domain.startswith('www.') else domain
    domain = domain.split('/')[0].split('?')[0].split('#')[0]
    try:
        socket.inet_aton(domain)
        return False
    except socket.error:
        pass
    allowed = set('abcdefghijklmnopqrstuvwxyz0123456789-.')
    return all(c in allowed for c in domain) and domain.count('.') >= 1


def normalize_domain(domain: str) -> str:
    domain = domain.lower().strip()
    for prefix in ('http://', 'https://'):
        domain = domain.replace(prefix, '')
    domain = domain.replace('www.', '', 1) if domain.startswith('www.') else domain
    domain = domain.split('/')[0].split('?')[0].split('#')[0]
    return domain


def get_all_domains_to_block(domain: str) -> set:
    """Возвращает все варианты домена для блокировки"""
    domains = set()
    domain = normalize_domain(domain)

    # Если есть в словаре зеркал
    if domain in SITE_MIRRORS:
        domains.update(SITE_MIRRORS[domain])
    else:
        # Стандартная блокировка
        domains.add(domain)
        if not domain.startswith('www.'):
            domains.add(f'www.{domain}')
        if not domain.startswith('m.'):
            domains.add(f'm.{domain}')

    return domains


def get_blocked_domains() -> set:
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
                        d = parts[1]
                        if not d.startswith('localhost'):
                            blocked.add(d)
    except Exception:
        pass
    return blocked


def update_hosts_file(domains: set):
    original_content = ""
    if HOSTS_FILE.exists():
        with open(HOSTS_FILE, 'r', encoding='utf-8') as f:
            original_content = f.read()

    # Бэкап
    if not HOSTS_FILE.with_suffix(HOSTS_FILE.suffix + BACKUP_SUFFIX).exists():
        try:
            with open(HOSTS_FILE, 'rb') as src, open(HOSTS_FILE.with_suffix(HOSTS_FILE.suffix + BACKUP_SUFFIX),
                                                     'wb') as dst:
                dst.write(src.read())
        except:
            pass

    # Удаляем старый блок
    if MARKER_START in original_content and MARKER_END in original_content:
        new_content = original_content.split(MARKER_START)[0] + original_content.split(MARKER_END)[1]
    else:
        new_content = original_content.rstrip('\n') + '\n'

    # Добавляем новый блок
    if domains:
        block = MARKER_START
        for d in sorted(domains):
            block += f"{BLOCK_IP} {d}\n"
        block += MARKER_END
        new_content += block

    with open(HOSTS_FILE, 'w', encoding='utf-8') as f:
        f.write(new_content.rstrip() + '\n')

    # Очистка DNS
    try:
        os.system('ipconfig /flushdns >nul 2>&1')
        os.system('netsh winsock reset >nul 2>&1')
    except:
        pass
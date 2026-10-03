# Предпубликационная версия сайта Владимира Эглитиса

Статический HTML/CSS/JS, без CMS и платёжного backend. В `articles/` только две утверждённые статьи. Сайт закрыт от индексации через `robots.txt` и meta robots. WhatsApp и email подтверждены как рабочие CTA; MAX и Telegram взяты из предыдущей v0.7. Публично не размещать до остальных предпубликационных решений.

Локальный запуск из корня проекта:

```powershell
python -m http.server 8080 --directory site
```

Откройте `http://127.0.0.1:8080/`. Автопроверки при работающем сервере:

```powershell
python check_staging.py
python scripts/verify_site.py
python scripts/capture.py final
```

Скриншоты сохраняются локально в `output/playwright/`, исходное состояние зафиксировано первым коммитом Git. Полный аудит — `AUDIT_2026-10-03.md`, предстоящий серверный план — `deploy/RUNBOOK.md`.

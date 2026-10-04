# Источники значков мессенджеров

- `site/assets/icon-telegram.svg`: знак самолётика извлечён из [официального архива логотипов Telegram](https://telegram.org/tour/screenshots), без градиентного круга.
- `site/assets/icon-max.svg`: белая версия знака из [официального брендбука MAX](https://go.max.ru/brandbook).
- `site/assets/icon-whatsapp.svg`: контурный знак из [Simple Icons v15](https://github.com/simple-icons/simple-icons), с учётом [рекомендации WhatsApp о белом варианте](https://faq.whatsapp.com/5913398998672934).

На сайте знаки отображаются одним цветом через CSS mask, не меняя их форму. Их названия остаются текстом рядом со значками. Исходные URL и точная процедура получения зафиксированы в `scripts/fetch_messenger_icons.py`.

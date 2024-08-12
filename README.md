## Thoth: Bitrix24 Integration Hub 

### Описание

Одна инсталляция Thoth позволяет создавать и обслуживать неограниченное количество локальных приложений Битрикс24 с OAuth 2.0 авторизацией.

## Видеоинструкции на Youtube

https://www.youtube.com/playlist?list=PLeniNJl73vVmmsG1XzTlimbZJf969LIpS


## Установка 

Для тестового запуска использовался python 12

```
cd /opt
git clone https://github.com/vaestvita/thoth
cd thoth

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp docs/example/env_example .env 
nano .env
заменить HOME_URL, ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS на свои значения
HOME_URL - домен по которму будет доступен thoth (example.com)

python manage.py migrate
python manage.py collectstatic
python manage.py createsuperuser


python manage.py runserver 0.0.0.0:8000

```

После запуска сервера в файле .env будет создан ADMIN_URL, который необходимо исопльзовать для входа в админку

## Прокси сервер 
+ Процесс настройки Nginx и Gunicorn можно посмотреть [здесь](https://www.digitalocean.com/community/tutorials/how-to-set-up-django-with-postgres-nginx-and-gunicorn-on-ubuntu)
+ Примеры файлов конфигураций есть в [документации](docs/example)

## Логирование 
При необходимости можно включить подробные логи в консоль. Для этого в файле .env укажите уровень логиования LOG_LEVEL=DEBUG, перезапустите thoth и введите команду 

```
journalctl -u thoth -f
```

## Подключение 

+ [Битрикс](docs/bitrix.md)
+ [(WhatsApp) WABA](docs/waba.md)
+ [OLX](docs/olx.md)

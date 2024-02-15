# Changelog

## [1.0.1] - 2024-02-15

+ Added - Обработка ONIMCONNECTORLINEDELETE. При удалении открытой линии, удаляется коннектор.
+ Added - Загрузка полученных файлов в хранилище приложения с последующей отправкой в чат открытой линии
+ Added - Обработка входящих сообщений WhatsApp типов contacts, audio, image, document
+ Added - В скрипт [add_connector](tools/add_connector.py) добавлен функционал получения Id хранилища локльного приложения
+ Added - В скрипт [add_connector](tools/add_connector.py) добавлена подписка на события OnImConnectorLineDelete и OnImConnectorStatusDelete
+ Fixed - Удалены двойные слешы в [add_connector](tools/add_connector.py) в запросах, приводящие к ошибке в коробке 
```
{'error': 'NO_AUTH_FOUND', 'error_description': 'Wrong authorization data'} 
```

## [1.0.0] - 2024-02-11

+ Added [crest.py](crest.py) и базовый функционал для решистрации и подключения коннектора Битрикс24

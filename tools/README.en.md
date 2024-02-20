# Script Descriptions

[Русский](README.md)

Scripts for performing some routine operations

+ [add_config](add_config.py): Designed for the initial generation of a configuration file. After launching and entering the parameters requested by the script, a file with a unique name is created in the configs folder, which will subsequently store all the necessary credentials for the operation of one local Bitrix24 application, including both Bitrix24 itself and connected systems.
+ [add_connector](add_connector.py): Designed for the registration of a contact center connector [imconnector.register](https://training.bitrix24.com/rest_help/imconnector/methods/imconnector_register.php) and subscription to the events OnImConnectorMessageAdd, OnImConnectorLineDelete, OnImConnectorStatusDelete.
+ [add_whatsapp](add_whatsapp.py): Designed for entering WhatsApp Business API credentials into the configuration file.
+ [event_bind](event_bind.py): Designed for subscribing to arbitrary events at the handler address specified in the selected configuration file.
+ [event_unbind](event_unbind.py): Designed for unsubscribing from events of the selected local application (configuration file).

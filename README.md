## Bitrix24 Integration Hub - Thoth 

[Russian](README.ru.md)

### Description

Thoth enables the creation of local Bitrix24 applications with OAuth 2.0 authorization.

A single installation of the application allows integrating an unlimited number of external systems with Bitrix24 via API.

The Bitrix24 OAuth 2.0 authorization token is automatically refreshed.

## YouTube Video Tutorials

https://www.youtube.com/playlist?list=PLeniNJl73vVmmsG1XzTlimbZJf969LIpS

## ToDo
+ [x] WhatsApp API [Business](https://developers.facebook.com/docs/whatsapp/) /by 20.02.2024
+ [ ] Detailed logging /by 28.02.2024
+ [ ] [Asterisk](https://docs.asterisk.org/) /by 20.03.2024
+ [ ] Telegram - ... 
+ [ ] Instagram - ...
+ [ ] SMS (goip) - ...
+ more ...

## Installation 
+ For the correct operation of the Thoth platform, a domain secured with a valid SSL certificate is required.
+ Example of setting up [Flask with Gunicorn and Nginx on an Ubuntu server](https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-gunicorn-and-nginx-on-ubuntu-20-04)
+ All subsequent actions must be carried out with the application running and functioning correctly.

## Generating a Configuration File and Connecting a Connector 
+ Run the [add_config](tools/add_config.py) file
~~~
python tools/add_config.py
~~~
+ The script will request data necessary for generating the configuration
~~~
Enter configuration name (my_project): test
Enter portal address (domain.bitrix24.ru): domain.bitrix24.ru
Enter the server domain where the script will be located (domain.ru): app.thoth.kz
~~~
+ As a result, a configuration file will be created in the configs folder, and data necessary for connecting to Bitrix24 will be displayed in the console.
Save the received response for convenience 
~~~
Basic configuration saved. Data for app registration:
1. Bitrix24. Your handler path: https://app.thoth.kz/bitrix?config=qJA0VBVH7tjxfGEfVE5U
2. Bitrix24. Path for initial installation: https://app.thoth.kz/install?config=qJA0VBVH7tjxfGEfVE5U
~~~
+ In Bitrix24, create a server-side local application without a Bitrix24 interface and fill in the corresponding fields (Your handler path and Path for initial installation)
+ Required permissions (Setting permissions): crm, imopenlines, contact_center, user, im, imconnector, disk
+ Click "Save"
+ The configuration file will automatically be filled with data from the Bitrix24 server
+ Copy the values of the Application Code (client_id) and Application Key (client_secret) into the corresponding fields of the configuration file

#### Creating a Connector
+ Run the [add_connector.py](tools/add_connector.py) file, select a configuration for setup
+ Enter the connector name and the path to the SVG file or URL of the image

#### Connecting the Bitrix24 Connector to the Open Line
+ Go to the Integrations > Contact Center section and select the created connector
+ Click "Connect"
+ Thoth, like Bitrix24, supports "many-to-many" connections

#### Connecting a Messenger (Using WhatsApp as an Example) to Bitrix24

+ VERY IMPORTANT! For one pair of connector+line on the Thoth application side, only one channel should be connected! Otherwise, functionality is not guaranteed at all. You can view an example configuration [here](example/I29bPabawXtNqRtz4Q76.json)
+ It is recommended to obtain a [Permanent Token](https://developers.facebook.com/docs/whatsapp/business-management-api/get-started), otherwise, you will need to reissue the token every day
+ Create an application on the [developers' portal](https://developers.facebook.com/apps/)
+ In the panel, connect the Webhooks, WhatsApp products
+ Save the phone number ID (test or connected)
+ Run the [add_whatsapp](tools/add_whatsapp.py) script
+ On the portal - Quick Start > Configuration > Callback URL
+ Enter the address and Confirmation Token given by the [add_whatsapp](tools/add_whatsapp.py) script
+ Click "Verify and Save"
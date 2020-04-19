# Simple file uploader to AWS
Синхронный загрузчик файлов на хранилища AWS. 

#### Сценарий использования 
Загрузка одиночного дампа на AWS через внешний скрипт запускаемый через cron.

#### Поддерживаемые типы хранилищ
**S3**, **Glacier**

#### Пример запуска
`python3 uploader.py --help`

#### Конфигурируемые параметры
    access_key: AWS account access key ID
    secret_key: AWS account secret key
    vault_name: AWS account vault name (Glacier)
    bucket_name: AWS account bucket name (S3)
    history_file: uploaded files history (Glacier)
    backup_dir: directory where backups are
    backup_exp: backups extension
    mode: uploader mode (AWS Glacier or AWS S3)

#### Пример bash-скрипта для загрузки дампов PostgreSQL

```
#!/bin/bash
now=$(date +"%Y_%m_%d_%HH")'.back.7z'
cd /data/backup
sudo -u postgres pg_dumpall > $now

if [ $? -eq 0 ]
then
    echo "Dump created successfully. Running uploader"
    /usr/bin/env python3 uploader.py
    if [ $? -eq 0 ]
    then
        echo "Dump uploaded successfully. Everithing is ok"
    else
        echo "Can't upload dump to AWS" >&2
    fi
else
    echo "Could not create dump" >&2
fi
```
    

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Simple uploader to aws. 2019"""

__author__ = 'Aleksey Devyatkin <devyatkin.av@ya.ru>'

import logging
import os
import sys
import json
import argparse
import boto3
from botocore.exceptions import ClientError


logging.basicConfig(level=logging.DEBUG,
                    format='%(levelname).1s[%(asctime)s]: %(message)s',
                    datefmt='%H:%M:%S')


def save_history(history_file_name, data):
    """Add dict data to history"""
    archive_id = data.get('archiveId')
    with open(history_file_name, 'a') as hist_file:
        json.dump(archive_id, hist_file)


def find_backup(backup_dir: str, backup_ext: str):
    """Find all backup files by mask"""
    backups = set()
    for file in os.listdir(backup_dir):
        if not backup_ext or file.endswith(backup_ext):
            backup_file_name = os.path.join(backup_dir, file)
            backups.add(backup_file_name)
            logging.debug(f'Backup file {backup_file_name} added.')
    return backups


def remove_backup(file_name):
    """Remove backup file after successful uploading to AWS"""
    logging.debug(f'Trying to remove file {file_name}')
    if os.path.isfile(file_name):
        os.remove(file_name)
        logging.debug(f'File {file_name} removed')
    else:
        logging.error(f'File {file_name} not found')


def read_object_data(src_data):
    if isinstance(src_data, bytes):
        return src_data

    if isinstance(src_data, str):
        try:
            object_data = open(src_data, 'rb')
        except FileNotFoundError:
            logging.error('Can\'t open src_data')
            object_data = None
        return object_data

    logging.error(f'{type(src_data)} is not supported.')


def upload_to_glacier(access: str, secret: str, vault_name: str, src_data: bytes):
    """Add an archive to an Amazon S3 Glacier vault.

    The upload occurs synchronously.
    :param access: string
    :param secret: string
    :param vault_name: string
    :param src_data: bytes of data or string reference to file spec
    :return: If src_data was added to vault, return dict of archive
    information, otherwise None
    """

    object_data = read_object_data(src_data)
    if not object_data:
        return

    try:
        glacier = boto3.client('glacier',
                               aws_access_key_id=access,
                               aws_secret_access_key=secret)
        archive = glacier.upload_archive(vaultName=vault_name,
                                         archiveDescription=src_data,
                                         body=object_data)
    except ClientError as err:
        logging.debug(err)
        logging.error(f'{src_data} was not uploaded to {vault_name}')

    if isinstance(src_data, str):
        object_data.close()
    return archive


def upload_to_s3(access: str, secret: str, bucket: str, file_name: str):
    """Upload a file to an S3 bucket

    :param access: AWS account ACCESS KEY ID
    :param secret: AWS account SECRET KEY
    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :return: True if file was uploaded, else False
    """

    # If S3 object_name was not specified, use file_name
    object_name = os.path.basename(file_name)

    try:
        # Establish connection
        s3_client = boto3.client('s3',
                                 aws_access_key_id=access,
                                 aws_secret_access_key=secret)
        # Upload the file
        s3_client.upload_file(file_name, bucket, object_name)
    except ClientError as err:
        logging.debug(err)
        logging.error(f'{object_name} was not uploaded to {bucket}')


def upload_list_to_glacier(vault_name: str, access: str, secret: str, file_set: set, history_file: str):
    """Upload several files to Glacier"""
    for backup_file in file_set:
        archive = upload_to_glacier(vault_name=vault_name, src_data=backup_file, access=access, secret=secret)
        if archive:
            save_history(history_file, archive)
            logging.info(f'File {backup_file} added to {vault_name}')
            remove_backup(backup_file)


def upload_list_to_s3(bucket_name: str, access: str, secret: str, file_set: set):
    """Upload file_list to S3"""
    for backup_file in file_set:
        upload_to_s3(access, secret, bucket_name, backup_file)
        logging.info(f'File {backup_file} added to {bucket_name}')
        remove_backup(backup_file)


def parse_args():
    """Module arguments parser.

    access_key: AWS account access key ID
    secret_key: AWS account secret key
    vault_name: AWS account vault name (Glacier)
    bucket_name: AWS account bucket name (S3)
    history_file: uploaded files history (Glacier)
    backup_dir: directory where backups are
    backup_exp: backups extension
    mode: uploader mode (AWS Glacier or AWS S3)

    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--access_key', default='Z123456', type=str,
                        help='AWS account access key ID')
    parser.add_argument('-s', '--secret_key', default='A123456', type=str,
                        help='AWS account secret key')
    parser.add_argument('-v', '--vault_name', default='some Glacier vault', type=str,
                        help='AWS account vault name')
    parser.add_argument('-b', '--bucket_name', default='some S3 bucket', type=str,
                        help='AWS account bucket name')
    parser.add_argument('-d', '--backup_dir', default='/data/backup', type=str,
                        help='directory where backups are')
    parser.add_argument('-l', '--history_file', default='history.json', type=str,
                        help='uploaded files history (Glacier)')
    parser.add_argument('-e', '--backup_ext', default='.back.7z', type=str,
                        help='backups extension')
    parser.add_argument('-m', '--mode', default='s3', type=str, choices=['glacier', 's3'],
                        help='use AWS Glacier uploader instead of AWS S3')
    return parser.parse_args()


def shutdown(lvl: int = 0):
    logging.info('Stop')
    sys.exit(lvl)


def main():
    logging.info('Start')
    args = parse_args()

    # Assign these values before running the program
    backups_set = find_backup(args.backup_dir, args.backup_ext)
    if not backups_set:
        logging.warning(f'No backups in {args.backup_dir} found. Exit.')
        shutdown(1)

    if args.mode == 'glacier':
        upload_list_to_glacier(file_set=backups_set,
                               history_file=args.history_file,
                               access=args.access_key,
                               secret=args.secret_key,
                               vault_name=args.vault_name)
    else:
        upload_list_to_s3(file_set=backups_set,
                          access=args.access_key,
                          secret=args.secret_key,
                          bucket_name=args.bucket_name)
    shutdown(0)


if __name__ == '__main__':
    main()

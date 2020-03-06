#!/usr/bin/env python
import subprocess

from fabric.api import env, run, get
from fabric.context_managers import cd
from fabric.operations import local

output = subprocess.check_output('git branch', shell=True, universal_newlines=True)
env.hosts = [
    'centos@119.23.52.188:39989',
]


def utf8(path):
    import os
    from os.path import join, splitext
    import logging
    logging.getLogger().setLevel(logging.INFO)

    def convert(file):
        try:
            with open(file, 'r', encoding='GBK') as reader:
                content = reader.read()
                with open(file, 'w', encoding='UTF-8') as writer:
                    writer.write(content)
                    logging.info('文件[%s]已转换为UTF-8编码', file)
        except UnicodeDecodeError:
            logging.error('文件[%s]不是GBK编码', file)

    for root, dirs, files in os.walk(path):
        for f in files:
            _, ext = splitext(f)
            if ext not in ('.java', ):
                continue
            convert(join(root, f))


def email():
    import smtplib

    server = 'smtp.exmail.qq.com'
    port = 465
    username = 'vipfitness@vipfitness.cn'
    sender = 'vipfitness@vipfitness.cn'
    password = 'QS9e3zebLMEezeeP'

    smtp_obj = smtplib.SMTP_SSL(server, port)
    smtp_obj.login(username, password)
    smtp_obj.sendmail(sender, ('gaoyanchao@vipfitness.cn',), 'test')


def download():
    get('/var/log/myapp.log', 'myapp-0301.log')


def deploy():
    local('git push')
    with cd('/home/centos/doudizhu'):
        run('git pull')
        # run('docker-compose restart')
        run('docker-compose up -d --build')

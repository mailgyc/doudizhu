FROM python:3.7-alpine

ENV PYTHONUNBUFFERED 1
ENV TORNADO_SETTINGS_MODULE settings.production

COPY requirements.txt requirements.txt
COPY doudizhu/ /app

RUN echo "https://mirror.tuna.tsinghua.edu.cn/alpine/v3.9/main/" > /etc/apk/repositories
RUN apk add --no-cache --virtual .build-deps gcc musl-dev openssl-dev libffi-dev
RUN pip install -U setuptools pip && pip install -r requirements.txt -i https://pypi.douban.com/simple

WORKDIR /app
EXPOSE 8080
CMD ["python3", "app.py"]

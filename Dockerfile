FROM python:alpine3.10

ENV PYTHONUNBUFFERED 1

COPY requirements.txt requirements.txt
COPY doudizhu/ /app

RUN echo "https://mirror.tuna.tsinghua.edu.cn/alpine/v3.10/main/" > /etc/apk/repositories
RUN set -e; apk add --no-cache --virtual .build-deps gcc musl-dev openssl-dev libffi-dev
RUN pip install -U pip && pip install -r requirements.txt -i https://pypi.douban.com/simple

WORKDIR /app
EXPOSE 8080
CMD ["python3", "app.py"]

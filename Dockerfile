FROM python:alpine3.12

ENV PYTHONUNBUFFERED 1

COPY requirements.txt requirements.txt
COPY doudizhu/ /app

RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.ustc.edu.cn/g' /etc/apk/repositories
RUN set -e; apk add --no-cache --virtual .build-deps gcc musl-dev openssl-dev libffi-dev
RUN pip install -U pip && pip install -r requirements.txt -i https://pypi.douban.com/simple

WORKDIR /app
EXPOSE 8080
CMD ["python3", "app.py"]

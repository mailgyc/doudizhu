FROM python:3.7.2-alpine

ENV PYTHONUNBUFFERED 1

COPY ../.../requirements.txt requirements.txt
COPY ../../doudizhu /app

RUN apk add --no-cache --update gcc musl-dev openssl-dev libffi-dev libjpeg-turbo-dev
RUN pip install -r requirements.txt -i https://pypi.douban.com/simple

ENTRYPOINT ["entrypoint.sh"]

WORKDIR /app
EXPOSE 8080
CMD ["python3", "app.py"]

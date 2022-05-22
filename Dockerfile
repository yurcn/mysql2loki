FROM python:3.9-alpine

ENV PATH /usr/local/bin:$PATH
ENV LANG C.UTF-8

RUN for pkg in PyYAML PyMysql python-logging-loki ; do pip install $pkg ; done

RUN mkdir /app
RUN touch /app/mysql2loki-config.yml
COPY ./mysql2loki.py /app/

WORKDIR /app

CMD ["python", "mysql2loki.py"]
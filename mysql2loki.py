#!/usr/bin/env python

import yaml
import pymysql
import logging
import logging_loki
import re
from time import sleep
from multiprocessing import Queue

with open("mysql2loki-config.yml", "r") as ymlconfig:
    cnf = yaml.safe_load(ymlconfig)

handler = logging_loki.LokiQueueHandler(
    Queue(-1),
    url= cnf['loki']['url'],
    tags={"instance": cnf['name'],},
    version="1",
)

try:
    period = cnf['period']
except KeyError:
    period = 150

try:
    logger_name = cnf['logger'] 
except KeyError:
    logger_name = 'SlowQueriesSnap'

try:
    port = cnf['mysql']['port']
except KeyError:
    port = 3306

try:
    log_key = cnf['mysql']['log_column']
except KeyError:
    log_key = 'info'

extra_tags = {"severity": "info",}

while True:
    connection = pymysql.connect( host=cnf['mysql']['host'], user=cnf['mysql']['user'], password=cnf['mysql']['pass'],database=None, port=port, cursorclass=pymysql.cursors.DictCursor)
    try:
        with connection.cursor() as cur:
            cur.execute(cnf['mysql']['query'])
            numrows = cur.rowcount
            for i in range(0,numrows):
                row = cur.fetchone()
                if row is None or log_key not in row:
                    continue
                if len(row[log_key]) > 0:
                    if logger_name == 'SlowQueries':
                        stmt = re.sub(r'IN\s+\([\(\),0123456789]{20,}$', r'IN (-- long line trimmed', str(row[log_key]))
                        stmt = re.sub(r'VALUES\s*\([\(\),0123456789]{20,}$', r'VALUES(-- long line trimmed', stmt)
                        if int(row['time']) > 30:
                            timetag = '30_'
                        elif 20 < int(row['time']) <= 30:
                            timetag = '20_30'
                        elif 10 < int(row['time']) <= 20:
                            timetag = '10_20'
                        elif 5 < int(row['time']) <= 10:
                            timetag = '5_10'                    
                        elif 3 < int(row['time']) <= 5:
                            timetag = '3_5'
                        else:
                            timetag = '1_3'
                        stmt = str(format(row['time'],'02d')) + 's ' + stmt 
                        extra_tags['timetag'] = timetag
                        extra_tags['host'] = str(row['host']).split(":")[0]
                    if 'extra_tags' in cnf['mysql']:
                        for tag in cnf['mysql']['extra_tags']:
                            if tag in row:
                                extra_tags[tag] = str(row[tag])
                    logger = logging.getLogger(logger_name)
                    logger.addHandler(handler)
                    logger.error(stmt,
                        extra={"tags": extra_tags },)                   
    finally:
        connection.close()

    sleep(period)

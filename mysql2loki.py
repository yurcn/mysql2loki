#!/usr/bin/env python

import yaml
import pymysql
import logging
import logging_loki
import re
from time import sleep
from multiprocessing import Queue

def time2tag(time):
    if int(time) < 3:
        return '1_3'
    elif 3 < int(time) <= 5:
        return '3_5'
    elif 5 < int(time) <= 10:
        return'5_10'
    elif 10 < int(time) <= 20:
        return '10_20'
    elif 20 < int(time) <= 30:
        return '20_30'
    else:
        return '30_'        

def process_replacements(stmt, replacements):
    if len(replacements) > 0:
        trimmed = len(stmt)
        for pattern in replacements:
            for q in replacements[pattern]:
                stmt = re.sub(q['search'], q['replace'], stmt)
    if len(stmt) > 1000:
        last_closing_par = stmt.rfind(')')
        last_opening_par = stmt.rfind('(')
        if last_opening_par > last_closing_par:
            stmt = stmt[:980] + '-- long line trimmed'
        elif last_closing_par > 700:
            stmt = stmt[:680] + '/* long line trimmed */' + stmt[last_closing_par-1:]
    trimmed -= len(stmt)
    if trimmed > 0 and 'long line trimmed' in stmt:
        stmt = re.sub(r'long line trimmed', str(trimmed) + ' chars trimmed', stmt)
    return stmt

def read_config(config_file):
    with open(config_file, "r") as ymlconfig:
        cnf = yaml.safe_load(ymlconfig)
    handler = logging_loki.LokiQueueHandler(
        Queue(-1),
        url= cnf['loki']['url'],
        tags={"instance": cnf['name'],},
        version="1",
    )
    period = cnf.get('period', 150)
    logger_name = cnf.get('logger', 'SlowQueriesSnap')
    port = cnf['mysql'].get('port', 3306)
    log_key = cnf['mysql'].get('log_column', 'info')
    replacements = cnf.get('replacements', {})
    extra_tags = {"severity": "info",}
    return handler, cnf, period, logger_name, port, log_key, replacements, extra_tags

handler, cnf, period, logger_name, port, log_key, replacements, extra_tags = read_config("mysql2loki-config.yml")

while True:
    try:
        connection = pymysql.connect(host=cnf['mysql']['host'], user=cnf['mysql']['user'], password=cnf['mysql']['pass'], database=None, port=port, cursorclass=pymysql.cursors.DictCursor)
        with connection.cursor() as cur:
            cur.execute(cnf['mysql']['query'])
            numrows = cur.rowcount
            for i in range(0,numrows):
                row = cur.fetchone()
                if row is None or log_key not in row:
                    continue
                stmt = str(row[log_key])
                if len(stmt) > 0:
                    if len(replacements) > 0:
                        stmt = process_replacements(stmt,replacements)
                    if 'time' in row:
                        timetag = time2tag(row['time'])
                        stmt = str(format(row['time'], '02d')) + 's ' + stmt
                        extra_tags['timetag'] = timetag
                    if 'host' in row:
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

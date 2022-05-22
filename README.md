# mysql2loki
Log snapshots of MySQL queries straight to Loki to look back into your database state over time.

As a sample use case, log snapshots of running tasks from ``information_schema`` to check what was running when spikes logged on your panels in Grafana.

Usage
------
#
Edit configuration in [mysql2loki-config.yml](mysql2loki-config.yml) setting your database credentials, Loki URL and SQL query to save in logs. 
```yaml
name: instance
period: 30 # in seconds
logger: SlowQueriesSnap # goes to logger tag
mysql:
  host: localhost
  port: 3306
  user: logger
  pass: password
  query: "SELECT id, user, host, db, command, time, state, info from information_schema.processlist WHERE state NOT IN ('', 'Waiting for an event from Coordinator')	AND command NOT IN ('Daemon', 'connect', 'Binlog Dump') AND time > 1 ORDER BY time DESC LIMIT 200"
  log_column: info # column to go into main log content
  extra_tags: # columns to go into tags
    - user 
    - command
    - state
     
loki:
  url: http://127.0.0.1:3100/loki/api/v1/push
```

Logged content is controlled by ``log_column`` and ``extra_tags`` option. ``log_column`` goes into log with all tags set by ``extra_tags`:
![Tags selection in Grafana](assets/tags-selection.png?raw=true "Tags selection in Grafana")

Installation
------
The script is based on beautiful [logging_loki handler](https://github.com/GreyZmeem/python-logging-loki) and makes use of [PyMySQL](https://github.com/PyMySQL/PyMySQL) and [PyYaml](https://github.com/yaml/pyyaml) libraries, so these should be installed:
```shell
pip install python-logging-loki
pip install PyYAML
pip install PyMysql
```

Docker 
------
You can build docker image with supplied [Dockerfile](Dockerfile) or run it from ghcr.io. Point your configuration file to ``/app/mysql2loki-config.yml`` inside container:
```shell
$ docker run -d --restart=unless-stopped -v ./mysql2loki-config.yml:/app/mysql2loki-config.yml ghcr.io/yurcn/mysql2loki
```


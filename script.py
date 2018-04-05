#!/usr/bin/env python3

import MySQLdb as mysql

from config import db_credentials
from metrics import get_risk_level


""" IMPORT ENVIRONMENT-SPECIFIC CONFIGS """
ENV = "dev"
db_creds = db_credentials[ENV]

""" GLOBAL VARIABLES """
db = None
cursor = None


def main():
    get_risk_level('ias', 0)


try:
    db = mysql.connect(**db_creds)
    cursor = db.cursor(mysql.cursors.DictCursor)

    main()
except mysql.Error as e:
    print('MySQL Error [%d]: %s', e.args[0], e.args[1])
    print('Last Executed Query: %s', cursor._last_executed)
finally:
    if cursor is not None:
        cursor.close()
    if db is not None:
        db.close()

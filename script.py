#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import MySQLdb as mysql

from config import db_credentials as db_creds

'''GLOBAL VARIABLES'''
db = None
cursor = None

PENALTY_PER_DEDUCTION = 4


fetch_metric_data_sql = """\
    SELECT
        flight_id, approach_id, turn_risk_level, landing_type, unstable,
        heading_risk_level, crosstrack_risk_level, ias_risk_level, 
        vsi_risk_level
    FROM approaches
    WHERE flight_id IN (%s);
"""
update_score_sql = """\
    UPDATE approaches
    SET score = %s
    WHERE flight_id = %s and approach_id = %s;
"""


def main():
    flight_ids = (
        381046, 381218, 381233, 381349, 381812, 382172, 382178, 382486, 382496,
        382538, 382741, 382928, 383219, 383403, 383544, 383556, 383749, 383781,
        383790, 384269, 384270, 384307, 384326, 384412, 384420, 384441, 384445,
        384460, 384476, 384647, 384674, 384965, 385012, 385331, 385645, 385690,
        385836, 386486, 386666, 386765, 386800, 387160, 387181, 387201, 387607,
        387627, 387765, 387949, 388186, 388192, 388354, 388498, 388638, 388639,
        389027, 389165, 389178, 389421, 389521, 389844, 389850, 390048, 390052,
        390082, 390131, 390247, 392334, 392504, 392538, 392706, 392824, 392836,
        392886, 392898, 392955, 393046, 393230, 393246, 393289, 393554, 393655,
        393769, 393837, 394127, 394355, 394362, 394365, 394475, 394645, 394766,
        394927, 394933, 394998, 395219, 395220, 395316, 395374, 395599, 397800,
        397803
    )

    cursor.execute(
        fetch_metric_data_sql % ', '.join(str(f) for f in flight_ids)
    )
    results = cursor.fetchall()

    for result in results:
        flight_id, approach_id = result['flight_id'], result['approach_id']
        print('For %d %d:' % (flight_id, approach_id))
        risk_level_keys = filter(
            lambda k: k.endswith('risk_level'), result.keys()
        )

        # Total up all deductions based on risk level
        deductions = sum(result[k] for k in risk_level_keys if result[k])

        if result['unstable'] and result['landing_type'] != 'go-around':
            print('\t', 'Unstable & DID NOT go-around')
            deductions += 1

        score = 100 - (PENALTY_PER_DEDUCTION * deductions)

        print('\t', 'Total Deductions: %3d' % deductions)
        print('\t', 'Score = %3d' % score)

        try:
            cursor.execute(update_score_sql, (score, flight_id, approach_id))
            db.commit()
        except mysql.Error as e:
            print('MySQL Error [%d]: %s', e.args[0], e.args[1])
            print('Last Executed Query: %s', cursor._last_executed)


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

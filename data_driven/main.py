#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Importing libraries
from data_driven.initial_preprocessing import initial_data_preprocessing

import logging
import argparse

logging.basicConfig(level=logging.INFO)


def data_driven_pipeline(args):
    '''
    Function to run the ML pipeline
    '''

    logger = logging.getLogger(' Data-driven modeling')

    logger.info(' Starting data-driven modeling')

    # Opening and preliminary data preprocessing
    df_ml = initial_data_preprocessing(args)
    

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--rdbms',
                        help='The Relational Database Management System (RDBMS) you would like to use',
                        choices=['MySQL', 'PostgreSQL'],
                        type=str,
                        default='mysql')
    parser.add_argument('--password',
                        help='The password for using the RDBMS',
                        type=str)
    parser.add_argument('--username',
                        help='The username for using the RDBMS',
                        type=str,
                        default='root')
    parser.add_argument('--host',
                        help='The computer hosting for the database',
                        type=str,
                        default='127.0.0.1')
    parser.add_argument('--port',
                        help='Port used by the database engine',
                        type=str,
                        default='3306')
    parser.add_argument('--db_name',
                        help='Database name',
                        type=str,
                        default='PRTR_transfers')
    parser.add_argument('--grouping_type',
                        help='How you want to calculate descriptors for the chemical groups',
                        choices=[1, 2, 3, 4, 5, 6, 7, 8],
                        type=int,
                        required=False,
                        default=1)
    parser.add_argument('--including_groups',
                        help='Would you like to include the chemical groups',
                        choices=['Yes', 'No'],
                        type=str,
                        default='Yes')

    args = parser.parse_args()

    data_driven_pipeline(args)
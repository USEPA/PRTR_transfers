#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Importing libraries
from data_engineering.transform.common import opening_files
from data_engineering.transform.common import config

import pandas as pd
pd.set_option('mode.chained_assignment', None)
import os
import re


dir_path = os.path.dirname(os.path.realpath(__file__)) # current directory path
ancillary_path = f'{dir_path}/../../ancillary' # ancillary folder path

def sections_to_potential_divisions(codes):
    '''
    Function for looking for the potential ISIC division
    '''

    codes = [str(code) for code in codes]
    divisions = [code[0:2] if len(code) == 4 else code[0] for code in codes]
    df_divisions = pd.DataFrame({'divisions': divisions})
    df_divisions = df_divisions.divisions.value_counts().rename_axis('divisions').reset_index(name='counts')
    df_divisions['divisions'] = df_divisions['divisions'].astype(int)
    df_divisions.sort_values(by='divisions', ascending=True, inplace=True)
    df_divisions.reset_index(drop=True, inplace=True)
    max_count = df_divisions['counts'].max()
    if df_divisions[df_divisions.counts != max_count].empty:
        result_code = df_divisions.divisions.iloc[0]
    else:
        result_code = df_divisions.loc[df_divisions.counts.idxmax(), 'divisions']

    return result_code


def normalizing_sectors():
    '''
    Function for standardizing the national industry classification systems
    based on ISIC divisions
    '''

    # Calling dictionary for cross-walking to ISIC
    sic = config(f'{ancillary_path}/Dictionary_to_crosswalk_to_isic.yaml')['system']

    # Searching for PRTR files
    df_sectors = opening_files(usecols=['national_sector_code'],
                                dtype={'national_sector_code': int},
                                systems_class=['USA_NAICS', 'ANZSIC', 'CAN_NAICS'],
                                column_name='industry_classification_system')

    # Calling files for cross-walking industry sectors
    df_converter = pd.DataFrame()
    for system, att in sic.items():

        file_name = att['file']
        file_path = f'{ancillary_path}/{file_name}.csv'
        df = pd.read_csv(file_path, usecols=att['cols'],
                        dtype={col: 'object' for col in att['cols']})

        national_code = att['cols'][0]
        national_name = att['cols'][1]
        df[national_code] = df[national_code].apply(lambda val: re.sub(r"[^0-9]+", "", val).lstrip('0'))
        df['ISIC'] = df['ISIC'].apply(lambda val: re.sub(r"[^0-9]+", "", val).lstrip('0'))
        df[national_code] = pd.to_numeric(df[national_code])
        df = df.loc[pd.notnull(df[national_code])]
        df[national_code] = df[national_code].astype('int')
        df['ISIC'] = df['ISIC'].astype('int')
        df[national_name] = df[national_name].str.strip().str.capitalize()
        df['ISIC TITLE'] = df['ISIC TITLE'].str.strip().str.capitalize()
        df.drop(['ISIC TITLE'], inplace=True, axis=1)
        df.sort_values(by=[national_code, 'ISIC'],
                       inplace=True)
        df['industry_classification_system'] = system
        df.rename(columns={'ISIC': 'isic_code',
                            national_code: 'national_sector_code',
                            national_name: 'national_sector_name'},
                  inplace=True)
        df_converter = pd.concat([df_converter, df],
                                 ignore_index=True,
                                 sort=False,
                                 axis=0)
    
        del df

    # Keeping only those national sectors reporting to the PRTR systems
    df_converter = pd.merge(df_converter, df_sectors,
                        on=['national_sector_code', 'industry_classification_system'], how='right')
    del df_sectors

    # Looking for ISIC divisions
    grouping = ['national_sector_code', 'national_sector_name', 'industry_classification_system']
    df_converter['generic_sector_code'] = df_converter.groupby(grouping, as_index=False)['isic_code']\
        .transform(lambda g: sections_to_potential_divisions(g))


    # National to generic industry codes
    df_national_to_generic = df_converter[['national_sector_code',
                                           'national_sector_name',
                                           'generic_sector_code',
                                           'industry_classification_system']]
    del df_converter
    df_national_to_generic.drop_duplicates(keep='first',
                                           inplace=True)

    # Calling ISIC division codes
    df_isic_divisions = pd.read_csv(f'{ancillary_path}/ISIC_4.csv',
                                    dtype = {'Code': int})
    df_isic_divisions.rename(columns={'Code': 'generic_sector_code',
                                      'Description': 'generic_sector_name'},
                                      inplace=True)
    df_national_to_generic = pd.merge(df_national_to_generic, df_isic_divisions,
                                  on='generic_sector_code', how='left')

    # Saving the information
    df_national_to_generic.to_csv(f'{dir_path}/output/national_to_generic_sector.csv',
                                  index=False, sep=',')


if __name__ == '__main__':

    normalizing_sectors()

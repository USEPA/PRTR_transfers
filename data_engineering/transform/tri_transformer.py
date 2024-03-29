#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Importing libraries
from data_engineering.transform.common import config, dq_score
from data_engineering.transform.naics_normalization import normalizing_naics
from data_engineering.extract.srs_scraper import get_cas_by_alternative_id

import os
import pandas as pd
import numpy as np
import re


dir_path = os.path.dirname(os.path.realpath(__file__))
conversion_factor = {'Pounds': 0.453592,
                     'Grams': 10**-3}


def weight_mean(v, w):
    '''
    Function for calculating weighted average and avoiding ZeroDivisionError, which ocurres
    "when all weights along axis are zero".
    '''
    
    try:
        return np.average(v, weights=w)
    except ZeroDivisionError:
        return v.mean()


def opening_file(key, year):
    '''
    Function to open the TRI files
    '''

    # Calling columns for using and their names
    columns_path = f'{dir_path}/../../ancillary/TRI_columns_for_using.yaml'
    columns_for_using = config(columns_path)


    # Calling TRI data file
    extracted_npi_path = f'{dir_path}/../extract/output/US_{key}_{year}.csv'
    df = pd.read_csv(extracted_npi_path, header=None,
                     skiprows=[0], engine='python',
                     error_bad_lines=False,
                     usecols=columns_for_using[key].keys(),
                     names=columns_for_using[key].values())
    
    # Dropping records for mixtures and trade secrets
    df = df[~(df.national_substance_id.isin(['TRD SECRT', 'MIXTURE']))]
    
    return df


def organizing_columns(df_raw, key, year):
    '''
    Function to transform the dataset structure
    '''

    non_off_columns = [col for col in df_raw.columns if 'Off-site' not in col]
    off_columns = [col for col in df_raw.columns if ('Off-site' in col) and ('basis of estimate' not in col)]

    if (key == '3c'):
        if (year >= 2018):
            off_columns = off_columns[1:]
        else:
            off_columns = [off_columns[0]]

    df_off = pd.DataFrame()
    for off in off_columns:
        df_raw[off] = pd.to_numeric(df_raw[off], errors='coerce', downcast='float')
        if (df_raw[off] == 0).all() or (pd.isnull(df_raw[off])).all():
            continue
        else:
            df_off_aux = df_raw[non_off_columns + [off, f'{off} - basis of estimate']].copy()
            df_off_aux.rename(columns={off: 'transfer_amount_kg',
                                    f'{off} - basis of estimate': 'reliability_score'},
                            inplace=True)
            if (key == '3c') and (year >= 2018):
                val_to_insert = 'Off-site - total POTW transfer'
            else:
                val_to_insert = off
            df_off_aux.insert(8, 'national_transfer_class_name',
                            [val_to_insert]*df_raw.shape[0], True)
            df_off = pd.concat([df_off, df_off_aux], ignore_index=True, axis=0)
            del df_off_aux
    
    return df_off


def organizing_landfill_surface_impoundment(group, df):
    '''
    Function to impute the transfers class for Off-site - landfills/disposal surface impoundment.
    Options:
    (1) Off-site - surface impoundment
    (2) Off-site - other landfills
    (3) Off-site - RCRA subtitle c landfills
    '''

    df.national_sector_code = df.national_sector_code.astype(str)

    substance_id = group['national_substance_id'].values[0]
    facility_id = group['national_facility_id'].values[0]
    sector = str(group['national_sector_code'].values[0])
    # Searching for the information using the NAICS hierarchy structure
    for i in range(7,-2,-1):
        if i == 7:
            df_f_chem = df[(df.national_substance_id == substance_id) &
                (df.national_facility_id == facility_id)]
        elif i == 1:
            df_f_chem = df[(df.national_substance_id == substance_id)]
        elif i == 0:
            df_f_chem = df[df.national_facility_id == facility_id]
        elif i == -1:
            df_f_chem = df.copy()
        else:
            df_f_chem = df[(df.national_substance_id == substance_id) &
                        (df.national_sector_code.str[0: i] == sector[0: i])]
        if df_f_chem.empty:
            continue
        else:
            break

    # Selecting the method
    df_f_chem = df_f_chem[['national_transfer_class_name', 'transfer_amount_kg', 'times']]
    df_f_chem = df_f_chem.groupby('national_transfer_class_name', as_index=False).sum()
    df_f_chem['probability'] = df_f_chem['times']*df_f_chem['transfer_amount_kg']
    df_f_chem.sort_values(by=['probability'], ascending=False, inplace=True)
    df_f_chem.reset_index(drop=True, inplace=True)
    group['national_transfer_class_name'] = df_f_chem['national_transfer_class_name'].iloc[0]

    group.to_csv(f'{dir_path}/output/tri.csv',
                index=False, sep=',',
                mode='a', header=False)


def transforming_tri():
    '''
    Function to transform TRI raw data into the structure for the
    generic database
    '''

    # Looking for TRI years extracted from internet
    regex = re.compile(r'US_3a_([0-9]{4}).csv')
    years = [int(re.search(regex, file).group(1)) for file in os.listdir(f'{dir_path}/../extract/output/') if file.startswith('US_3a')]
    years.sort()

    # Concatenating files
    df_cas_searched = pd.DataFrame(columns=['national_substance_id',
                                            'cas_number'])
    for year in years:
        df_tri = pd.DataFrame()
        for key in ['3a', '3b', '3c']:
            if (key == '3a') or ((key == '3b') and (int(year) <= 2010)) or ((key == '3c') and (int(year) >= 2011)):
                df = opening_file(key, year)
                df = organizing_columns(df, key, year)
                df_tri = pd.concat([df_tri, df], ignore_index=True, axis=0)

        # Dropping 0 for transfer_amount_kg
        def checking_basis_estimate(bs):
            try:
                if bs:
                    return bs.strip()
                else:
                    return bs
            except AttributeError:
                return None
        to_keep = ['O', 'C', 'E', 'E1', 'E2', 'M', 'M1', 'M2']
        df_tri['transfer_amount_kg'] = pd.to_numeric(df_tri['transfer_amount_kg'],
                                                    errors='coerce',
                                                    downcast='float')
        df_tri = df_tri.where(pd.notnull(df_tri), None)
        df_tri['reliability_score'] = df_tri['reliability_score'].apply(lambda x: checking_basis_estimate(x))
        df_tri = df_tri[(df_tri['transfer_amount_kg'] != 0) | (df_tri['reliability_score'].isin(to_keep))]
        df_tri = df_tri[pd.notnull(df_tri['transfer_amount_kg'])]

        # Converting to kg
        func = lambda quanity, units: quanity*conversion_factor[units.capitalize()]
        df_tri['transfer_amount_kg'] = df_tri.apply(lambda row: \
            func(row['transfer_amount_kg'],
                row['Units']), axis=1)
        df_tri.drop(columns=['Units'], inplace=True)
            
        # Calling values for reliability score
        dq_matrix = dq_score('TRI')

        # Giving the reliability scores for the off-site transfers reported by facilities
        df_tri['reliability_score'] = df_tri['reliability_score'].where(df_tri['reliability_score'].isin(dq_matrix.keys()), None)
        df_tri['reliability_score'] = df_tri['reliability_score'].apply(lambda s: dq_matrix[s] if s else 5)

        # Aggregation of flow and reliability
        wm = lambda x: weight_mean(x, df_tri.loc[x.index, 'transfer_amount_kg'])
        grouping_vars = ['national_substance_name', 'reporting_year',
                        'national_sector_code', 'national_transfer_class_name',
                        'national_substance_id', 'national_facility_id']
        df_tri = df_tri.groupby(grouping_vars).agg({'transfer_amount_kg':'sum',
                                                    'reliability_score': wm})
        df_tri = df_tri.reset_index()
        
        # Adding country column
        df_tri['country'] = 'USA'

        # Organizing list of CAS numbers to search for
        df_tri['national_substance_id'] = df_tri['national_substance_id'].str.lstrip('0')
        tri_ids = df_tri[['national_substance_id', 'national_substance_name']]\
            .drop_duplicates(subset=['national_substance_id'], keep='first')\
            .reset_index(drop=True)
        cas_list = df_cas_searched['national_substance_id'].tolist()
        tri_ids = tri_ids.loc[~tri_ids['national_substance_id'].isin(cas_list)]
        del cas_list
        if not tri_ids.empty:
            tri_ids['cas_number'] = tri_ids.apply(lambda x:
                                        get_cas_by_alternative_id(altId=x['national_substance_id'],
                                                                substanceName=x['national_substance_name']),
                                            axis=1)
            tri_ids.drop(columns=['national_substance_name'], inplace=True)
            df_cas_searched = df_cas_searched.set_index('national_substance_id')\
                    .combine_first(tri_ids.set_index('national_substance_id')).reset_index()

        # Adding CAS number column
        df_tri = pd.merge(df_tri, df_cas_searched, on='national_substance_id', how='left')

        # Crosswalking NAICS codes
        df_tri = normalizing_naics(df_tri)

        # Saving the transformed data
        decimals = pd.Series([2, 0], index=['transfer_amount_kg', 'reliability_score'])
        df_tri[['transfer_amount_kg', 'reliability_score']] =\
            df_tri[['transfer_amount_kg', 'reliability_score']].round(decimals)
        df_tri.to_csv(f'{dir_path}/output/tri_{year}.csv',
                    index=False, sep=',')

        del df_tri, tri_ids


    # Cross-year search for Off-site - landfills/disposal surface impoundment
    df_tri = pd.DataFrame()
    for year in years:
        df_year = pd.read_csv(f'{dir_path}/output/tri_{year}.csv')
        df_tri = pd.concat([df_tri, df_year],
                            ignore_index=True,
                            sort=False,
                            axis=0)
        del df_year
        os.remove(f'{dir_path}/output/tri_{year}.csv')
    
    decimals = pd.Series([2, 0], index=['transfer_amount_kg', 'reliability_score'])
    df_tri[['transfer_amount_kg', 'reliability_score']] =\
        df_tri[['transfer_amount_kg', 'reliability_score']].round(decimals)
    df_landfill_surface = df_tri[df_tri.national_transfer_class_name == 'Off-site - landfills/disposal surface impoundment']
    df_landfill_surface.reset_index(drop=True, inplace=True)
    df_tri = df_tri[df_tri.national_transfer_class_name != 'Off-site - landfills/disposal surface impoundment']

    # Saving the tri records
    df_tri.to_csv(f'{dir_path}/output/tri.csv',
                    index=False, sep=',')


    df_tri = df_tri[df_tri.national_transfer_class_name.isin(['Off-site - surface impoundment',
                                                            'Off-site - RCRA subtitle c surface impoundment',
                                                            'Off-site - other surface impoundment',
                                                            'Off-site - other landfills',
                                                            'Off-site - RCRA subtitle c landfills'
                                                            ])]
    method_to_method = {'Off-site - RCRA subtitle c surface impoundment': 'Off-site - surface impoundment',
                            'Off-site - other surface impoundment': 'Off-site - surface impoundment'}
    df_tri.national_transfer_class_name = df_tri.national_transfer_class_name.apply(lambda x: x if x in method_to_method.keys() else x)
    df_tri = df_tri[['national_transfer_class_name',
                    'transfer_amount_kg', 'national_substance_id',
                    'national_facility_id', 'national_sector_code',
                    'reporting_year']]
    grouping = ['national_transfer_class_name', 'national_facility_id',
                'national_sector_code', 'national_substance_id'] 
    df_tri = df_tri.loc[df_tri.groupby(grouping).reporting_year.idxmin()].reset_index(drop=True)
    df_tri['times'] = 1
    grouping.pop(0)
    df_landfill_surface\
        .groupby(grouping, as_index=False)\
            .apply(lambda g: organizing_landfill_surface_impoundment(g, df_tri.copy()))


if __name__ == '__main__':
    
    transforming_tri()
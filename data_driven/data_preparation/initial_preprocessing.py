# Importing libraries
from data_driven.data_preparation.rdkit_descriptors import information_for_set_of_chems
from data_engineering.extract.nlm_scraper import looking_for_structure_details as nlm
from data_engineering.extract.pubchem_scraper import looking_for_structure_details as pubchem
from data_driven.data_preparation.opening_dataset import opening_dataset

import random
from random import seed
import pandas as pd
import numpy as np
from scipy.stats import zscore, mode
import os

dir_path = os.path.dirname(os.path.realpath(__file__)) # current directory path
seed(1) # seed random number generator

def chemical_group_descriptors(group, generic_substance_id, grouping_type=1):
    '''
    Function to calculate the descriptors for chemical groups
    
    Options:

    (1) mean value without outliers (default)
    (2) mean value with outliers
    (3) median value
    (4) min value
    (5) max value
    (6) random value
    (7) random chemical
    (8) keep chemicals (keep all chemicals having non-null records (95%))
    '''

    if (grouping_type == 1) or (grouping_type == 2):
        if (group.shape[0] != 1) and (grouping_type == 1):
            # Removing outliers
            z_scores = zscore(group)
            abs_z_scores = z_scores.abs()
            # Filling NaN zscore values
            abs_z_scores.fillna(0, inplace=True)
            filtered_entries = (abs_z_scores < 3).all(axis=1)
            group = group[filtered_entries]
        group = group.mean(skipna=True)
    elif grouping_type == 3:
        group = group.median(skipna=True)
    elif grouping_type == 4:
        group = group.min(skipna=True)
    elif grouping_type == 5:
        group = group.max(skipna=True)
    elif grouping_type == 6:
        group.reset_index(drop=True, inplace=True)
        group = pd.Series(group.apply(lambda x: pd.Series(random.choice(x)), axis=0).to_dict('records')[0])
    elif grouping_type == 7:
        group = pd.Series(group.sample(1, random_state=0).to_dict('records')[0])
    elif grouping_type == 8:
        group = group[group.count(axis=1)/group.shape[1] >= 0.95]
        group['generic_substance_id'] = generic_substance_id

    return group



def looking_for_smiles(cas_number):
    '''
    Function to look for the SMILES using both the NLM and PubChem databases
    '''
    smiles = pubchem(cas_number)
    if not smiles:
        smiles = nlm(cas_number)

    return smiles


def initial_data_preprocessing(logger, args):
    '''
    Function for a preliminary preprocessing of the data
    '''

    db_name = args.db_name
    including_groups = args.including_groups
    grouping_type = args.grouping_type
    cas_dict = {'chemical': 'chemical_in_category_cas',
                'substance': 'cas_number'}
    datasets = ['chemical', 'substance', 'record']

    df_chem = pd.DataFrame()
    for dataset in datasets:

        # Opening and/or creating the dataset
        logger.info(f' Fetching the needed information for the {dataset} dataset from the {db_name} database')

        if os.path.isfile(f'{dir_path}/output/{dataset}.csv'):

            df = pd.read_csv(f'{dir_path}/output/{dataset}.csv',
                            dtype={'generic_substance_id': object})
        else:

            df = opening_dataset(args, dataset)

            if (dataset in cas_dict.keys()):
                
                # Looking for SMILES
                logger.info(f' Looking for SMILES for compounds belonging to the {dataset}s list')
                df['smiles'] = df[cas_dict[dataset]].apply(lambda cas: looking_for_smiles(cas))

                # Looking for chemical descriptors
                df = df[pd.notnull(df['smiles'])]
                logger.info(f' Looking for descriptors for compounds belonging to the {dataset}s list')
                df = information_for_set_of_chems(cas_dict[dataset], df)
                df.reset_index(drop=True, inplace=True)
                df.drop(columns=['smiles'], inplace=True)

            # Saving information for further use and speeding up ML pipeline
            df.to_csv(f'{dir_path}/output/{dataset}.csv', index=False, sep=',')

        # Organizing descriptors for chemicals belonging to the groups
        if (dataset == 'chemical') and (including_groups == 'Yes'):
            df.drop(columns=['chemical_in_category_cas'], inplace=True)
            descriptors = [col for col in df.columns if col != 'generic_substance_id']
            fcols = df[descriptors].select_dtypes('float').columns
            icols = df[descriptors].select_dtypes('integer').columns
            df = df.groupby(['generic_substance_id'], as_index=False)\
                            .apply(lambda group: chemical_group_descriptors(
                                    group[descriptors],
                                    group.generic_substance_id.unique()[0],
                                    grouping_type=grouping_type)
                                    )
            df_chem = pd.concat([df_chem, df], ignore_index=True, axis=0)
        elif (dataset == 'substance'):
            df.drop(columns=['cas_number'], inplace=True)
            df_chem = pd.concat([df_chem, df], ignore_index=True, axis=0)
            # Dropping columns with a lot missing values
            to_drop = df_chem.columns[pd.isnull(df_chem).sum(axis=0)/df_chem.shape[0] > 0.8].tolist()
            df_chem.drop(columns=to_drop, inplace=True)
            # Missing values imputation
            to_impute = df_chem.columns[pd.isnull(df_chem).any(axis=0)].tolist()
            fcols_i = [col for col in to_impute if col in fcols]
            icols_i = [col for col in to_impute if col in icols]
            df_chem[fcols_i] = df_chem[fcols_i].fillna({fcols_i[idx]: val for idx, val in enumerate(np.nanmedian(df_chem[fcols_i].values, axis=0))})
            df_chem[fcols] = df_chem[fcols].round(2)
            df_chem[icols_i] = df_chem[icols_i].fillna({icols_i[idx]: val for idx, val in enumerate(mode(df_chem[icols_i].values, nan_policy='omit')[0])})
            df_chem[fcols] = df_chem[fcols].apply(pd.to_numeric, downcast='float')
            df_chem[icols] = df_chem[icols].apply(pd.to_numeric, downcast='integer')
            del to_impute, fcols_i, icols_i, fcols, icols
        elif (dataset == 'record'):
            # Keeping the column selected by the user as the model output
            if args.output_column == 'generic':
                df.drop(columns=['transfer_class_wm_hierarchy_name'],
                        inplace=True)
            else:
                df.drop(columns=['generic_transfer_class_id'],
                        inplace=True)
            df_ml = pd.merge(df, df_chem, on='generic_substance_id', how='inner')
            del df_chem

        del df

    return df_ml
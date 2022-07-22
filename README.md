# PRTR transfers

<p align="center">
  <img src=https://github.com/jodhernandezbe/PRTR_transfers/blob/data-engineering/logo.svg width="50%">
</p>

<hr/>

## 1. Overview

### 1.1. Project tree

The following is the project tree considering only its most important files for a developer. Don't hesitate to fully check the folders, including the [ancillary](https://github.com/jodhernandezbe/PRTR_transfers/tree/master/ancillary) one that contains important information for the data processing.  

```bash

PRTR_transfers
├── ancillary
│    
└── data_engineering
    ├── __init__.py
    ├── main.py
    ├── extract
    |   ├── __init__.py
    │   ├── config.yaml
    │   ├── main.py
    |   ├── common.py
    │   ├── npi_scraper.py
    │   ├── npri_scraper.py
    │   ├── tri_scraper.py
    │   ├── srs_scraper.py
    │   ├── nlm_scraper.py
    │   ├── pubchem_scraper.py
    │   └── output
    │ 
    ├── transform
    |   ├── __init__.py
    │   ├── main.py
    │   ├── common.py
    │   ├── industry_sector_standardizing.py
    │   ├── chemical_standardizing.py
    │   ├── naics_normalization.py
    │   ├── npi_transformer.py
    │   ├── npri_transformer.py
    │   ├── tri_transformer.py
    │   ├── database_normalization.py
    │   └── output
    │ 
    └── load
        ├── __init__.py
        ├── main.py
        ├── industry_sector.py
        ├── facility.py
        ├── prtr_system.py
        ├── record.py
        ├── substance.py
        ├── transfer.py
        ├── chemical.py
        ├── base.py
        └── output

```

### 1.2. Enhanced entity-relationship diagram (EERD) for the PRTR_transfers database 

The EERD model in the following figure represents the PRTR_transfers database schema created after data engineering. The prtr_system table is shown without any explicit relationship between the other tables in the database. The reason is that the columns of the prtr_system table were not set as foreign key; however, its columns could be used to connect to other tables like the national_substance table to know the PRTR system the report comes from. 

<p align="center">
  <img src=https://github.com/jodhernandezbe/PRTR_transfers/blob/data-engineering/data_engineering/load/PRTR_transfers_EER_Diagram.svg width="100%">
</p>

<hr/>

## 2. Requirements

### 2.1. Developers

#### 2.1.1. Creating conda environment

A conda environment can be created by executing the following command:


```
conda env create -n PRTR -f environment.yml

```

The above command is written assuming that you are in the folder containing .yml file, i.e. the root folder PRTR_transfers. 

#### 2.1.2. Avoiding ModuleNotFoundError and ImportError<sup>[1](#myfootnote1)</sup>

If you are working as a Python developer, you should avoid both ```ModuleNotFoundError``` and ```ImportError``` (see the following [link](https://towardsdatascience.com/how-to-fix-modulenotfounderror-and-importerror-248ce5b69b1c)). Thus, follow the steps below to solve the above mentioned problems:

<ol>
  <li>
    Run the following command in order to obtain the PRTR_transfers project location and then saving its path into the variable PACKAGE
    
    PACKAGE=$(locate -br '^PRTR_transfers$')
  </li>
  <li>
    Check the PACKAGE value by running the following command
    
    echo $PACKAGE
   </li>
   <li>
    Run the following command to add the PRTR_transfers project to the system paths
     
    export PYTHONPATH="${PYTHONPATH}:$PACKAGE"
   </li>
</ol>

If you prefer to save the path to the PRTR_transfers project folder as a permanent environment variable, follow these steps:

<ol>
   <li>
    Open the .bashrc file with the text editor of your preference (e.g., Visual Studio Code)
        
    code ~/.bashrc
   </li>
   <li>
    Scroll to the bottom of the file and add the following lines
       
    export PACKAGE=$(locate -br '^PRTR_transfers$')
    export PYTHONPATH="${PYTHONPATH}:$PACKAGE"
   </li>
   <li>
    Save the file with the changes
   </li>
   <li>
    You can open another terminal to verify that the variable has been successfully saved by running the following command
    
    echo $PYTHONPATH
   </li>
</ol>

<hr/>

#### 2.1.3. Installation of Relational Database Management System (RDMS)

The Extract, Transform, Load (ETL) procedure uses an Object–Relational Mapping (ORT) for data persistence by an RDMS. PostgreSQL and MySQL are the RDMS currently supported by the ETL. Thus, you must have installed any of these RDMSs to run the data engineering pipeline or the data-driven modeling module.

## 3. How to use

### 3.1. Data engineering module

You can use each .py file in the data engineering module separately. However, the developed module enables to run the ETL pipeline using the main.py inside the [datan_engineering](https://github.com/jodhernandezbe/PRTR_transfers/tree/master/data_engineering) folder. Thus, follow the above steps:

<ol>
   <li>
    In your terminal or command line, navigate to the data_engineering folder
   </li>
   <li>
    Run the following command

    python main.py --help
   </li>
   <li>
    You will see the following help menu

    usage: main.py [-h] [--rdbms RDBMS] [--password PASSWORD] [--username USERNAME] [--host HOST] [--port PORT] [--db_name DB_NAME]
                   [--sql_file SQL_FILE]

    optional arguments:
          -h, --help           show this help message and exit
          --rdbms {mysql,postgresql}
                               The Relational Database Management System (RDBMS) you would like to use
          --password PASSWORD  The password for using the RDBMS
          --username USERNAME  The username for using the RDBMS
          --host HOST          The computer hosting for the database
          --port PORT          Port used by the database engine
          --db_name DB_NAME    Database name
          --sql_file {True,False}
                               Would you like to obtain .SQL file
   </li>
   <li>
    You must indicate the value for each parameter, e.g., if you would like to name your database as PRTR, you write <code>--dn_name PRTR</code>. Each argument       except <code>--password</code> has a default value (see the table below)
    
   |Argument|Default| Comment |
   |---|---|---|
   | rdbms | mysql | Only two options: MySQL and PostgreSQL |
   | username | root | root is the default username for MySQL. For PostgreSQL is postgres |
   | host | 127.0.0.1 | 127.0.0.1 (localhost) is the default host for MySQL. The same is for PostgreSQL |
   | port | 3306 | 3306 is the default port for MySQL. For PostgreSQL is 5432 |
   | db_name | PRTR_transfers | You are free to choose a name for the database |
   | sql_file | False | Only two options: True and False |
   </li>
</ol>

<hr/>

## 4. Notes

<a name="myfootnote1">1</a>: If you have troubles with this step, update ```updatedb```  by running ```sudo updatedb```.

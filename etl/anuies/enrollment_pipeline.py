def format_text(df, cols_names=None, stopwords=None):

    # format
    for ele in cols_names:
        df[ele] = df[ele].str.title().str.strip()
        for ene in stopwords:
            df[ele] = df[ele].str.replace(' ' + ene.title() + ' ', ' ' + ene + ' ')

    return df

import pandas as pd
from bamboo_lib.connectors.models import Connector
from bamboo_lib.models import EasyPipeline, PipelineStep, Parameter
from bamboo_lib.steps import LoadStep

class ReadStep(PipelineStep):
    def run_step(self, prev, params):
        # read data
        df = pd.read_excel(params.get('url'), header=1)
        df.columns = df.columns.str.lower().str.replace('suma de ', '')
        df.rename(columns={'entidad': 'ent_id', 'municipio': 'mun_id', 'cve campo unitario': 'career', 
                           'nivel': 'type', 'ciclo': 'period', 'clave centro de trabajo': 'institution', 
                           'nombre carrera sep': 'program'}, inplace=True)
        # careers ids
        url = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTzv8dN6-Cn7vR_v9UO5aPOBqumAy_dXlcnVOFBzxCm0C3EOO4ahT5FdIOyrtcC7p-akGWC_MELKTcM/pub?output=xlsx'
        ent = pd.read_excel(url, sheet_name='origin', dtypes='str')
        careers = pd.read_excel(url, sheet_name='careers')
        return df, ent, careers

class TransformStep(PipelineStep):
    def run_step(self, prev, params):
        df, ent, careers = prev[0], prev[1], prev[2]
        # type format
        for col in ['ent_id', 'mun_id', 'career', 'type', 'period', 'institution']:
            df[col] = df[col].ffill()
        df.ent_id = df.ent_id.str.title()

        # ids replace from external table
        df.ent_id.replace(dict(zip(ent.origin, ent.id)), inplace=True)

        # municipality level id
        df.loc[:, 'mun_id'] = df.loc[:, 'ent_id'].astype('str') + df.loc[:, 'mun_id'].astype('str')
        df.drop(columns=['ent_id'], inplace=True)
          
        # totals clean
        df.career = df.career.astype('str')
        for col in ['mun_id', 'career', 'type', 'period', 'institution', 'program']:
            df = df.loc[df[col].str.contains('Total') == False].copy()
            df[col] = df[col].str.strip().str.replace('  ', ' ').str.replace(':', '')
        df.career = df.career.str.replace('.', '').astype('int')

        # column names format
        df.columns = df.columns.str.replace('suma de ', '').str.replace('pni-', '')

        # melt step
        df = df[['mun_id', 'career', 'type', 'period', 'institution', 'program',
               'mat-h-22', 'mat-h-23', 'mat-h-24', 'mat-h-25', 'mat-h-26', 'mat-h-27',
               'mat-h-28', 'mat-h-29', 'mat-h-30', 'mat-h-31', 'mat-h-32', 'mat-m-22',
               'mat-m-23', 'mat-m-24', 'mat-m-25', 'mat-m-26', 'mat-m-27', 'mat-m-28',
               'mat-m-29', 'mat-m-30', 'mat-m-31', 'mat-m-32']].copy()
        
        df.columns = df.columns.str.replace('mat-', '')
        
        df = df.melt(id_vars=['mun_id', 'career', 'type', 'period', 'institution', 'program'], var_name='sex', value_name='value')
        df = df.loc[df.value != 0]
        
        split = df['sex'].str.split('-', n=1, expand=True) 
        df['sex'] = split[0]
        df['age'] = split[1]
        
        sex = {
            'h': 1,
            'm': 2,
        }

        df.sex.replace(sex, inplace=True)
        
        types = {
            'TS': 1,
            'LEN': 2,
            'LUT': 3,
            'MAESTRÍA': 4,
            'ESPECIALIDAD': 5,
            'DOCTORADO': 6
        }
        df.type.replace(types, inplace=True)

        # careers ids
        stopwords_es = ['a', 'e', 'en', 'ante', 'con', 'contra', 'de', 'del', 'desde', 'la', 'lo', 'las', 'los', 'y']
        df = format_text(df, ['program'], stopwords=stopwords_es)
        df.program.replace(dict(zip(careers.name_es, careers.code)), inplace=True)
        
        for col in ['mun_id', 'career', 'program', 'type', 'sex', 'value', 'age']:
            df[col] = df[col].astype('float')

        df.drop(columns=['career'], inplace=True)
        
        return df

class EnrollmentPipeline(EasyPipeline):
    @staticmethod
    def parameter_list():
        return [
            Parameter(name='url', dtype=str)
        ]

    @staticmethod
    def steps(params):
        
        db_connector = Connector.fetch('clickhouse-database', open('../conns.yaml'))
        
        dtype = {
            'mun_id':      'UInt16',
            'type':        'UInt8',
            'period':      'String',
            'institution': 'String',
            'program':     'UInt64',
            'sex':         'UInt8',
            'value':       'UInt32',
            'age':         'UInt8'
        }
        
        read_step = ReadStep()
        transform_step = TransformStep()
        load_step = LoadStep('anuies_enrollment', db_connector, if_exists='append', pk=['mun_id', 'institution', 'program'], dtype=dtype)

        return [read_step, transform_step, load_step]
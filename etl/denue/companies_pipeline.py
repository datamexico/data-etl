
import numpy as np
import pandas as pd
from bamboo_lib.connectors.models import Connector
from bamboo_lib.models import EasyPipeline, PipelineStep, Parameter
from bamboo_lib.steps import DownloadStep, LoadStep

class ReadStep(PipelineStep):
    def run_step(self, prev, params):
        # read data
        try:
            df = pd.read_csv(prev, encoding='utf-8', dtype='str', usecols=[0, 3, 5, 25, 26, 28, 30, 32, 33, 37, 38, 39, 40])
            df.columns = ['id', 'codigo_act', 'per_ocu', 'cod_postal', 'cve_ent', 'cve_mun', 'cve_loc', 'ageb', 'manzana', 
                    'tipounieco', 'latitud', 'longitud', 'fecha_alta']
        except:
            df = pd.read_csv(prev, encoding='latin-1', dtype='str', usecols=[0, 3, 5, 25, 26, 28, 30, 32, 33, 37, 38, 39, 40])
            df.columns = ['id', 'codigo_act', 'per_ocu', 'cod_postal', 'cve_ent', 'cve_mun', 'cve_loc', 'ageb', 'manzana', 
                    'tipounieco', 'latitud', 'longitud', 'fecha_alta']
        return df

class TransformStep(PipelineStep):
    def run_step(self, prev, params):
        df = prev

        # format
        df.cve_mun = df.cve_mun.str.zfill(3)
        df.cve_loc = df.cve_loc.str.zfill(4)
        
        # create columns
        df.cve_mun = df.cve_ent + df.cve_mun
        df['cve_mun'] = df['cve_mun'].astype('int')

        df.drop(columns=['ageb', 'manzana', 'cve_ent'], inplace=True)

        df.per_ocu = df.per_ocu.str.replace('personas', '').str.strip()
        df.per_ocu = df.per_ocu.str.replace(' a ', ' - ')
        df.per_ocu = df.per_ocu.str.replace(' y más', ' +')
        df.per_ocu = df.per_ocu.str.replace(' y m�s', ' +')
        df.fecha_alta = df.fecha_alta.str.replace('-', '')

        # date processing
        df.fecha_alta = df.fecha_alta.str.upper()
        months = {'ENERO': '01',
                'FEBRERO': '02',
                'MARZO': '03',
                'ABRIL': '04',
                'MAYO': '05',
                'JUNIO': '06',
                'JULIO': '07',
                'AGOSTO': '08',
                'SEPTIEMBRE': '09',
                'OCTUBRE': '10',
                'NOVIEMBRE': '11',
                'DICIEMBRE': '12'}

        for key, val in months.items():
            for date in df.fecha_alta.unique().tolist():
                try:
                    if key in date:
                        temp = date.replace(key, val).split()[1] + date.replace(key, val).split()[0]
                        df.fecha_alta = df.fecha_alta.str.replace(date, temp)
                except:
                    continue

        #range creation
        df['lower'] = np.nan
        df['upper'] = np.nan
        df['middle'] = np.nan

        for ele in df.per_ocu.unique():
            try:
                if '-' in ele:
                    df.loc[df.per_ocu == ele, 'lower'] = int(ele.split(' - ')[0])
                    df.loc[df.per_ocu == ele, 'upper'] = int(ele.split(' - ')[1])
                    df.loc[df.per_ocu == ele, 'middle'] = (float(ele.split(' - ')[1]) + float(ele.split(' - ')[0]))/2.0
                else:
                    df.loc[df.per_ocu == ele, 'lower'] = int(ele.split(' +')[0])
                    df.loc[df.per_ocu == ele, 'upper'] = int(ele.split(' +')[0])
                    df.loc[df.per_ocu == ele, 'middle'] = int(ele.split(' +')[0])
            except:
                continue
        
        # replace values
        workers = {
            '0 - 5': 1,
            '6 - 10': 2,
            '11 - 30': 3,
            '31 - 50': 4,
            '51 - 100': 5,
            '101 - 250': 6,
            '251 +': 7
        }
        df.per_ocu.replace(workers, inplace=True)

        place = {
            'Fijo': 1,
            'Semifijo': 2,
            'Actividad en vivienda': 3
        }
        df.tipounieco.replace(place, inplace=True)

        # rename column names
        column_names = {
            'codigo_act': 'national_industry_id',
            'per_ocu': 'n_workers',
            'cod_postal': 'postal_code',
            'tipounieco': 'establishment',
            'fecha_alta': 'directory_added_date',
            'cve_mun': 'mun_id',
            'latitud': 'latitude',
            'longitud': 'longitude'
        }
        df.rename(columns=column_names, inplace=True)
        df.postal_code = df.postal_code.str.replace('O', '0')
        for code in df.postal_code.unique():
            try:
                float(code)
            except:
                df.postal_code.replace(code, np.nan, inplace=True)
        
        # data types conversion
        dtypes = {
            'id':                   'int',
            'national_industry_id': 'str',
            'directory_added_date': 'int',
            'n_workers':            'int',
            'postal_code':          'str',
            'mun_id':               'int',
            'establishment':        'int',
            'latitude':             'float',
            'longitude':            'float',
            'lower':                'int',
            'middle':               'float',
            'upper':                'int'
        }
        df['directory_added_date'] = df['directory_added_date'].astype(str).str.replace(' ', '')
        
        for key, val in dtypes.items():
            try:
                # string column check
                if (df.loc[:, key].isnull().sum() > 0) & (key == 'str'):
                    df.loc[:, key] = df.loc[:, key].astype('object')
                else:
                    df.loc[:, key] = df.loc[:, key].astype(val)
            except Exception as e:
                if val == 'int':
                    df.loc[:, key] = df.loc[:, key].astype('float')
                else:
                    print(e)
        
        df['publication_date'] = int(params['date'])

        return df

class DENUEPipeline(EasyPipeline):
    @staticmethod
    def parameter_list():
        return [
            Parameter(label="Date", name="date", dtype=str),
            Parameter(label="URL", name="url", dtype=str)
        ]

    @staticmethod
    def steps(params):
        
        db_connector = Connector.fetch('clickhouse-database', open('../conns.yaml'))
        
        dtypes = {
            'id':                   'UInt32',
            'national_industry_id': 'String',
            'n_workers':            'UInt8',
            'postal_code':          'String',
            'establishment':        'UInt8',
            'mun_id':               'UInt16',
            'latitude':             'Float32',
            'longitude':            'Float32',
            'lower':                'UInt8',
            'middle':               'Float32',
            'upper':                'UInt8',
            'publication_date':     'UInt32',
            'directory_added_date': 'UInt32'
        }

        download_step = DownloadStep(
            connector='data',
            connector_path="conns.yaml"
        )

        read_step = ReadStep()
        transform_step = TransformStep()
        load_step = LoadStep('inegi_denue', connector=db_connector, if_exists='append', pk=['id', 'mun_id', 'national_industry_id'], dtype=dtypes, 
                                nullable_list=['n_workers', 'postal_code', 'establishment', 'latitude', 'longitude', 'directory_added_date',
                                'lower', 'middle', 'upper'])
        return [download_step, read_step, transform_step, load_step]
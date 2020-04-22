
import os
import glob
import numpy as np
import pandas as pd
from bamboo_lib.helpers import grab_parent_dir
from bamboo_lib.connectors.models import Connector
from bamboo_lib.models import EasyPipeline, PipelineStep, Parameter
from bamboo_lib.steps import DownloadStep, LoadStep, UnzipToFolderStep
from shared import rename_columns, rename_countries


class TransformStep(PipelineStep):
    def run_step(self, prev, params):

        data = glob.glob('*.csv')

        df = pd.read_csv(data[0])

        df.columns = [x.strip().lower().replace(' ', '_') for x in df.columns]

        df['entidad_res'] = df['entidad_res'].astype(str).str.zfill(2)
        df['municipio_res'] = df['municipio_res'].astype(str).str.zfill(3)
        df['patient_residence_mun_id'] = df['entidad_res'] + df['municipio_res']
        df['patient_residence_mun_id'] = df['patient_residence_mun_id'].astype(int)
        df.drop(columns=['entidad_res', 'municipio_res', 'id_registro'], inplace=True)

        for col in ['fecha_actualizacion', 'fecha_ingreso', 'fecha_sintomas', 'fecha_def']:
            df[col] = df[col].str.replace('-', '').astype(int)

        df.rename(columns=rename_columns, inplace=True)
        df['death_date'].replace(99999999, np.nan, inplace=True)
        df['country_nationality'].replace(rename_countries, inplace=True)
        df['country_origin'].replace(rename_countries, inplace=True)

        df['death_date'] = df['death_date'].astype(float)

        for col in [x for x in df.columns if x not in ['country_nationality', 'country_origin', 'death_date']]:
            df[col] = df[col].astype(int)

        return df

class CovidPipeline(EasyPipeline):
    @staticmethod
    def parameter_list():
        return [
            Parameter(label='folder_path', name='year', dtype=str)
        ]

    @staticmethod
    def steps(params):
        db_connector = Connector.fetch('clickhouse-database', open('../conns.yaml'))

        dtypes = {
            'updated_date':                     'UInt32',
            'origin':                           'UInt8',
            'type_health_institution_attended': 'UInt8',
            'health_institution_attended_ent':  'UInt8',
            'sex':                              'UInt8',
            'patient_origin_ent_id':            'UInt8',
            'patient_type':                     'UInt8',
            'ingress_date':                     'UInt32',
            'symptoms_date':                    'UInt32',
            'death_date':                       'UInt32',
            'intubated':                        'UInt8',
            'pneumonia_diagnose':               'UInt8',
            'age':                              'UInt8',
            'nationality':                      'UInt8',
            'pregnancy':                        'UInt8',
            'speaks_indigenous_language':       'UInt8',
            'diabetes_diagnose':                'UInt8',
            'COPD_diagnose':                    'UInt8',
            'asthma_diagnose':                  'UInt8',
            'inmunosupresion_diagnose':         'UInt8',
            'hypertension_diagnose':            'UInt8',
            'diagnosis_another_disease':        'UInt8',
            'cardiovascular_diagnose':          'UInt8',
            'obesity_diagnose':                 'UInt8',
            'chronic_kidney_failure_diagnose':  'UInt8',
            'smoking_diagnose':                 'UInt8',
            'contact_another_covid_case':       'UInt8',
            'covid_positive':                   'UInt8',
            'migrant':                          'UInt8',
            'country_nationality':              'String',
            'country_origin':                   'String',
            'required_ICU':                     'UInt8',
            'patient_residence_mun_id':         'UInt16'
        }

        download_step = DownloadStep(
            connector='covid-data-mx',
            connector_path='conns.yaml'
        )

        path = grab_parent_dir('.') + '/covid/'
        unzip_step = UnzipToFolderStep(compression='zip', target_folder_path=path)
        xform_step = TransformStep()
        load_step = LoadStep(
            'gobmx_covid', db_connector, if_exists='drop', pk=['updated_date', 'symptoms_date', 'ingress_date', 
                            'patient_residence_mun_id', 'patient_origin_ent_id', 
                            'country_nationality', 'country_origin'], nullable_list=['death_date'], dtype=dtypes
        )

        return [download_step, unzip_step, xform_step, load_step]
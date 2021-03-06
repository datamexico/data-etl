
import numpy as np
import pandas as pd
from bamboo_lib.connectors.models import Connector
from bamboo_lib.models import EasyPipeline, PipelineStep, Parameter
from bamboo_lib.steps import DownloadStep, LoadStep

class TransformStep(PipelineStep):
    def run_step(self, prev, params):

        df = pd.read_csv(prev)

        df.replace(' ', np.nan, inplace=True)

        # filter
        df = df.loc[~df['Edad'].isna()].copy()
        df = df.loc[~df['clave_actividad_economica'].isna()].copy()
        df = df.loc[df['clave_municipio'].isna()].copy()
        df = df.loc[df['clave_actividad_economica'].astype(str).str.len() == 6].copy()

        df.drop(columns=['entidad_federativa', 'clave_municipio', 'municipio', 'actividad_economica', 'Edad'], inplace=True)

        df.rename(columns={'clave_actividad_economica': 'national_industry_id',
                           'clave_entidad': 'ent_id'}, inplace=True)

        df['year'] = 2014

        df.columns = df.columns.str.lower()

        return df

class EconomicCensusPipeline(EasyPipeline):
    @staticmethod
    def parameter_list():
        return [
            Parameter(name='state', dtype=str)
        ]

    @staticmethod
    def steps(params, **kwargs):
        db_connector = Connector.fetch('clickhouse-database', open('../conns.yaml'))

        dtypes = {
            'ent_id':                  'UInt8',
            'national_industry_id':    'String',
            'year':                    'UInt16'
        }

        download_step = DownloadStep(
            connector='economic-census-data',
            connector_path='conns.yaml'
        )

        transform_step = TransformStep()

        load_step = LoadStep(
            'inegi_economic_census_ent', db_connector, dtype=dtypes, if_exists='append', 
            pk=['national_industry_id', 'ent_id', 'year']
        )

        return [download_step, transform_step, load_step]

if __name__ == '__main__':
    pp = EconomicCensusPipeline()
    for state in range(1, 32 + 1):
        pp.run({
            'state': str(state).zfill(2)
        })

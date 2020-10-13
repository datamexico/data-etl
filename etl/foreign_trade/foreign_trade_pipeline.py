import re
import pandas as pd
from bamboo_lib.connectors.models import Connector
from bamboo_lib.models import EasyPipeline, PipelineStep, Parameter
from bamboo_lib.steps import LoadStep, DownloadStep
from util import hs6_converter, get_time, get_number, get_params

class ReadStep(PipelineStep):
    def run_step(self, prev, params):
        # params
        df = pd.read_csv(prev)
        df.columns = [row.strip().lower() for row in df.columns]
        return df

class TransformStep(PipelineStep):
    def run_step(self, prev, params):
        df = prev

        params, url = get_params(params.get('url')), params.get('url')

        names = {
            'municipality_code': 'mun_id',
            'state_code': 'ent_id',
            'foreign_destination_origin': 'partner_country',
            'trade_flow': 'flow_id',
            'product_2d': 'hs2_id',
            'product_4d': 'hs4_id',
            'product': 'hs6_id'
        }
        df.rename(columns=names, inplace=True)

        # negative values
        df.value.replace('C', pd.np.nan, inplace=True)
        df.value = df.value.astype('float')
        df = df.loc[df.value > 0].copy()

        # iso3 names
        df['partner_country'] = df['partner_country'].str.lower()

        # fill columns
        level = ['hs6_id', 'hs4_id', 'hs2_id']
        for i in level:
            if i != params['depth']:
                df[i] = 0

        # drop date, create time dimension
        for k, v in params['datetime'].items():
            df[k] = v
        df.drop(columns='date', inplace=True)

        # hs codes
        df[params['depth']] = df[params['depth']].astype('str').str.zfill(get_number(params['depth']))
        for row in df[params['depth']].unique():
            df[params['depth']].replace(row, hs6_converter(row), inplace=True)

        for col in df.columns[df.columns != 'partner_country']:
            df[col] = df[col].astype('float').round(0).astype('int')

        # drop null trade values
        df.dropna(subset=['value'], inplace=True)

        # national ent id
        if 'National' in url:
            df['ent_id'] = 0

        # explicit level name
        df['level'] = int(params['level'][2])
        df['product_level'] = int(re.findall(r"(\d){1}", params['depth'])[0])

        return df

class ForeignTradePipeline(EasyPipeline):
    @staticmethod
    def parameter_list():
        return [
            Parameter('url', dtype=str),
            Parameter('type', dtype=str),
            Parameter('name', dtype=str),
        ]

    @staticmethod
    def steps(params):
        db_connector = Connector.fetch('clickhouse-database', open('../conns.yaml'))
        
        dtype = {
            'level':                         'UInt8',
            'product_level':                 'UInt8',
            params.get('name')+'_id': params.get('type'),
            'hs2_id':                        'UInt16',
            'hs4_id':                        'UInt32',
            'hs6_id':                        'UInt32',
            'flow_id':                       'UInt8',
            'partner_country':               'String',   
            'firms':                         'UInt16',
            'value':                         'UInt64',
            'month_id':                      'UInt32',
            'year':                          'UInt16'
        }
        
        read_step = ReadStep()

        download_step = DownloadStep(
            connector='foreign-trade',
            connector_path='conns.yaml'
        )

        transform_step = TransformStep()
        load_step = LoadStep('economy_foreign_trade_' + params.get('name'), db_connector, if_exists='append', 
                            pk=[params.get('name')+'_id', 'partner_country', 'month_id', 'year', 
                                'hs2_id', 'hs4_id', 'hs6_id', 'level', 'product_level'], 
                             dtype=dtype)

        return [download_step, read_step, transform_step, load_step]

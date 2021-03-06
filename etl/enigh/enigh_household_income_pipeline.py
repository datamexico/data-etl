
import pandas as pd
from bamboo_lib.connectors.models import Connector
from bamboo_lib.models import Parameter, EasyPipeline, PipelineStep
from bamboo_lib.steps import DownloadStep, LoadStep

def fix_geo_level(df, target, lenght):
    max_ = df[target].max()
    len_ = len(str(max_))
    df[target] = df[target].astype('str').str.zfill(len_)
    df[target] = df[target].str[:lenght].astype('int')
    return df

class TransformStep(PipelineStep):
    def run_step(self, prev, params):

        # read file
        household_cols = ['folioviv', 'ubica_geo', 'factor', 'tot_integ', 'trabajo']
        df = pd.read_csv(prev[0], index_col=None, header=0, encoding='latin-1', usecols = household_cols)

        # Turning Factor to int value
        df['factor'] = df['factor'].astype(int)

        # set year
        df['year'] = params.get('year')

        # to monthly
        df['trabajo_viv_mes'] = (df['trabajo']/3).astype('int')
        df.drop(columns=['trabajo', 'folioviv'], inplace=True)

        # municipality id
        df = fix_geo_level(df, 'ubica_geo', 5)

        # rename columns
        df.columns = ['mun_id', 'households', 'n_people_home', 'year', 'monthly_wage']

        # income interval v2
        def to_interval(df, target, intervals):
            for k, v in intervals.items():
                # asuming 'v' is an array
                df.loc[(df[target] >= v['interval_lower']) & (df[target] < v['interval_upper']), target] = k
            return df

        # income values format
        income = pd.read_excel(prev[1], encoding='latin-1')
        income = income.set_index('id')[['interval_lower', 'interval_upper']].to_dict('index')

        df = to_interval(df, 'monthly_wage', income)

        for col in df.columns:
            df[col] = df[col].astype('float')

        return df

class EnighIncomeHousePipeline(EasyPipeline):
    @staticmethod
    def parameter_list():
        return [
            Parameter(label='Year', name='year', dtype=str)
        ]

    @staticmethod
    def steps(params):
        db_connector = Connector.fetch('clickhouse-database', open('../conns.yaml'))

        dtype = {
            'mun_id':                   'UInt16',
            'households':               'UInt16',
            'n_people_home':            'UInt8',
            'monthly_wage':             'UInt8',
            'year':                     'UInt16'
        }

        download_step = DownloadStep(
            connector=['enigh-household', 'income-dim'],
            connector_path='conns.yaml'
        )
        transform_step = TransformStep()
        load_step = LoadStep(
            'inegi_enigh_household_income', db_connector, if_exists='append', pk=['mun_id'], dtype=dtype
        )

        return [download_step, transform_step, load_step]
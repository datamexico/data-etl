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
from sklearn.feature_extraction import stop_words

class TransformStep(PipelineStep):
    def run_step(self, prev, params):
        # read data
        df = pd.read_csv('https://docs.google.com/spreadsheets/d/e/2PACX-1vT0959aScOQnJcoxJTgvPqwma0jxsdyGZGswl4z8yl9KqiPeZleckFHoFyA2KHCMP3HrE8n7EwLyQAR/pub?output=csv')
        df.drop(columns=['hs4_id', 'hs4_es', 'hs4_en', 'hs6_id', 'hs6_es', 'hs6_en'], inplace=True)

        cols_es = ['chapter_es', 'hs2_es']
        cols_en = ['chapter_en', 'hs2_en']

        # codes ids
        stopwords_es = ['a', 'e', 'en', 'ante', 'con', 'contra', 'de', 'del', 'desde', 'la', 'lo', 'las', 'los', 'y']
        df = format_text(df, cols_es, stopwords=stopwords_es)
        df = format_text(df, cols_en, stopwords=stop_words.ENGLISH_STOP_WORDS)

        for col in ['hs2_id', 'chapter']:
            df[col] = df[col].astype('int')

        df = df.groupby(['chapter', 'chapter_es', 'chapter_en', 'hs2_id', 'hs2_es', 
            'hs2_en']).sum().reset_index(col_fill='ffill')

        return df

class DimCountriesPipeline(EasyPipeline):
    @staticmethod
    def steps(params):
        
        db_connector = Connector.fetch('clickhouse-database', open('../conns.yaml'))

        dtype = {
            'chapter':    'UInt8',
            'chapter_es': 'String',
            'chapter_en': 'String',
            'hs2_id':     'UInt16',
            'hs2_es':     'String',
            'hs2_en':     'String',
        }
        
        transform_step = TransformStep()
        load_step = LoadStep('dim_shared_hs12_2digit', db_connector, if_exists='drop', pk=[ 'hs2_id', 'chapter'], dtype=dtype)

        return [transform_step, load_step]
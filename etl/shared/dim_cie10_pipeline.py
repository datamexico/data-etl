import pandas as pd
import nltk
from bamboo_lib.models import PipelineStep
from bamboo_lib.models import EasyPipeline
from bamboo_lib.connectors.models import Connector
from bamboo_lib.steps import LoadStep, DownloadStep
# English stopwords
from sklearn.feature_extraction import stop_words

class ReadStep(PipelineStep):
    def run_step(self, prev, params):
        df = pd.read_csv(prev, dtype='str')
        return df

class CleanStep(PipelineStep):
    def run_step(self, prev, params):
        df = prev
								
        # Setting column names to set in format
        cols_es = ['category_es', 'cie10_3digit_es', 'cie10_4digit_es']
        cols_en = ['category_en', 'cie10_3digit_en', 'cie10_4digit_en']

        # stopwords es
        nltk.download('stopwords')

        # Step for spanish words
        for ele in cols_es:
            df[ele] = df[ele].str.title()
            for ene in nltk.corpus.stopwords.words('spanish'):
                df[ele] = df[ele].str.replace(' ' + ene.title() + ' ', ' ' + ene + ' ')

        # Step for english words
        for ele in cols_en:
            df[ele] = df[ele].str.title()
            for ene in list(stop_words.ENGLISH_STOP_WORDS):
                df[ele] = df[ele].str.replace(' ' + ene.title() + ' ', ' ' + ene + ' ')

        return df

class CIE10Pipeline(EasyPipeline):
    @staticmethod
    def website():
        return 'http://datawheel.us'

    @staticmethod
    def steps(params, **kwargs):
        # Use of connectors specified in the conns.yaml file
        db_connector = Connector.fetch('clickhouse-database', open('../conns.yaml'))
        dtype = {
            'chapter_id':               'String',
            'category_es':              'String',
            'category_en':              'String',
            'cie10_3digit':             'String',
            'cie10_3digit_es':          'String',
            'cie10_3digit_en':          'String',
            'cie10_4digit':             'String',
            'cie10_4digit_es':          'String',
            'cie10_4digit_en':          'String'
        }

        # Definition of each step
        download_step = DownloadStep(
            connector="cie10",
            connector_path="conns.yaml"
        )
        read_step = ReadStep()
        clean_step = CleanStep()
        load_step = LoadStep(
            'dim_shared_cie10', db_connector, if_exists='drop', pk=['chapter_id', 'cie10_3digit', 'cie10_4digit'], dtype=dtype
        )
        
        return [download_step, read_step, clean_step, load_step]
import nltk
import pandas as pd
from bamboo_lib.models import PipelineStep
from bamboo_lib.models import EasyPipeline
from bamboo_lib.connectors.models import Connector
from bamboo_lib.steps import LoadStep, DownloadStep
# English stopwords
from sklearn.feature_extraction import stop_words

class ReadStep(PipelineStep):
    def run_step(self, prev, params):
        df = pd.read_excel(prev, sheet_name="crime_modality", dtype="str")
        return df

class CleanStep(PipelineStep):
    def run_step(self, prev, params):
        df = prev
        # stopwords es
        nltk.download('stopwords')

        # Step for spanish words
        df["crime_modality_es"] = df["crime_modality_es"].str.title()
        for ene in nltk.corpus.stopwords.words('spanish'):
            df["crime_modality_es"] = df["crime_modality_es"].str.replace(" " + ene.title() + " ", " " + ene + " ")

        # Step for english words
        df["crime_modality_en"] = df["crime_modality_en"].str.title()
        for ene in list(stop_words.ENGLISH_STOP_WORDS):
            df["crime_modality_en"] = df["crime_modality_en"].str.replace(" " + ene.title() + " ", " " + ene + " ")

        # Groupby step
        grouped = ["crime_modality_id", "crime_modality_es", "crime_modality_en"]
        df = df.groupby(grouped).sum().reset_index(col_fill="ffill")

        df["crime_modality_id"] = df["crime_modality_id"].astype(int)

        return df

class CrimesModalityPipeline(EasyPipeline):
    @staticmethod
    def description():
        return "Processes crimes modality codification to Mexico Crimes Data"

    @staticmethod
    def website():
        return "http://datawheel.us"

    @staticmethod
    def steps(params, **kwargs):
        # Use of connectors specified in the conns.yaml file
        db_connector = Connector.fetch("clickhouse-database", open("../conns.yaml"))
        dtype = {
            "crime_modality_id":              "UInt8",
            "crime_modality_es":              "String",
            "crime_modality_en":              "String",
        }

        # Definition of each step
        download_step = DownloadStep(
            connector="dim-crime",
            connector_path="conns.yaml"
        )
        read_step = ReadStep()
        clean_step = CleanStep()
        load_step = LoadStep("dim_shared_crimes_modality", db_connector, if_exists="drop", pk=["crime_modality_id"], dtype=dtype)

        return [download_step, read_step, clean_step, load_step]
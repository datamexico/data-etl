import pandas as pd
from bamboo_lib.connectors.models import Connector
from bamboo_lib.models import EasyPipeline
from bamboo_lib.models import Parameter
from bamboo_lib.models import PipelineStep
from bamboo_lib.steps import DownloadStep
from bamboo_lib.steps import LoadStep


class TransformStep(PipelineStep):
    def run_step(self, prev, params):

        df = pd.read_csv(prev, header=0)

        # Replacing "no available" values with 0's
        df.replace({"n.a." : 0}, inplace=True)

        df = df[['mun', 'mun_id', 'zona_metropolitana', 'zona_metropolitana_id']].copy()

        # Transforming str columns into int values
        df["zona_metropolitana_id"] = df["zona_metropolitana_id"].astype(int)
        df["mun_id"] = df["mun_id"].astype(int)

        df.rename(columns={
            'zona_metropolitana':    'zm_name',
            'zona_metropolitana_id': 'zm_id'
        }, inplace=True)

        return df

class MetroAreaPopulationPipeline(EasyPipeline):
    @staticmethod
    def steps(params):
        db_connector = Connector.fetch("clickhouse-database", open("../conns.yaml"))

        dtype = {
            "zm_id":   "UInt32",
            "mun_id":  "UInt16",
        }

        download_step = DownloadStep(
            connector="population-data",
            connector_path="conns.yaml"
        )

        transform_step = TransformStep()

        load_step = LoadStep(
            "dim_conapo_metro_area_population", db_connector, if_exists="append", pk=["zm_id", "mun_id"], dtype=dtype, 
        )

        return [download_step, transform_step, load_step]

if __name__ == "__main__":
    pp = MetroAreaPopulationPipeline()
    pp.run({})
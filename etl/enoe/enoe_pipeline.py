import pandas as pd
from bamboo_lib.connectors.models import Connector
from bamboo_lib.models import EasyPipeline
from bamboo_lib.models import Parameter
from bamboo_lib.models import PipelineStep
from bamboo_lib.steps import DownloadStep
from bamboo_lib.steps import LoadStep


class TransformStep(PipelineStep):
    def run_step(self, prev, params):

        # Loading labels from spredsheet
        excel_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSg-NM8Jt_vHnuIcJ3fjHMxcae_IkK7sresHvhUs_G7NSM5CN5NGYiCf-BP_GMPw3jwmm791CXPLpqJ/pub?output=xlsx"
        df_labels = pd.ExcelFile(excel_url)

        print(params)

        # Loading 2 ENOE files, in order to create 1 quarter per year data
        dt_1 = pd.read_csv(prev[0], index_col=None, header=0, encoding="latin-1")
        dt_2 = pd.read_csv(prev[1], index_col=None, header=0, encoding="latin-1")

        # Standarizing headers, some files are capitalized
        dt_1.columns = df.columns.str.lower()
        dt_2.columns = df.columns.str.lower()

        # Setting the list of the respective columns for each part of the survey
        half1 = ["r_def", "cd_a", "ent", "n_pro_viv", "n_ren", "eda", "p1b", "p2_1", "p2_2", "p2_3", "p2_4", "p2_9",
                  "p2a_anio", "p2b", "p2c", "p2d1", "p2d2", "p2d3", "p2d4", "p2d5", "p2d6", "p2d7", "p2d8", "p2d9",
                  "p2d10", "p2d11", "p2d99", "p2e", "p2f", "p2g1", "p2g2", "p3", "p3i", "p3j1", "p3j2", "p3k1", "p3k2",
                  "p3k3", "p3k4", "p3k5", "p3k9", "p4a", "p4b", "p5b_thrs", "p5d_thrs", "p5b_tdia", "p5d_tdia", "fac"]
        half2 = ["p6_1", "p6_2", "p6_3", "p6_4", "p6_5", "p6_6", "p6_7", "p6_8", "p6_9", "p6_10", "p6_99",
                  "p6b1", "p6b2", "p6c", "p6d", "p7", "p7a", "p7c", "p8_2", "p8_3", "p8_4", "p8_9", "p8a"]

        # Creating df
        df = dt_1[half1]
        df[half2] = dt_2[half2]

        # Getting values of year and respective quarter for the survey
        df["year"] = "20" + prev[0][slice(-6,-4)]
        df["quarter"] = prev[0][slice(-7,-6)]
        df["year"] = df["year"].astype(int)
        df["quarter"] = df["quarter"].astype(int)

        # Dictionaries for renaming the columns
        part1 = pd.read_excel(df_labels, "part1")
        part2 = pd.read_excel(df_labels, "part2")

        # Renaming of the columns for a explanatory ones
        df.rename(columns = dict(zip(part1.column, part1.new_column)), inplace=True)
        df.rename(columns = dict(zip(part2.column, part2.new_column)), inplace=True)

        # Replacing NaN an empty values in order to change content of the columns with IDs
        df.replace(" ", 99999, inplace = True)
        df.fillna(99999, inplace = True)

        # Final columns [24 columns]
        batch = ["ent_id", "age", "has_job_or_business", "search_job_overseas", "search_job_mexico",
                "search_start_business", "search_no_search", "search_no_knowledge", "search_job_year",
                "time_looking_job", "actual_job_position", "actual_job_industry_group_id", 
                "actual_job_hrs_worked_lastweek", "actual_job_days_worked_lastweek", "population", 
                "actual_frecuency_payments", "actual_amount_pesos", "actual_minimal_wages_proportion", 
                "actual_healthcare_attention", "second_activity", "second_activity_task", "second_activity_group_id"
                "year", "quarter"]

        df = df[batch]

        # Changing columns with IDs trought cycle
        filling = ["has_job_or_business", "search_job_overseas", "search_job_mexico",
                    "search_start_business", "search_no_search", "search_no_knowledge",
                    "actual_frecuency_payments", "actual_minimal_wages_proportion", 
                    "actual_healthcare_attention", "second_activity"]

        # For cycle in order to change the content of a column from previous id, into the new ones (working for translate too)
        for sheet in filling:
            df_l = pd.read_excel(df_labels, sheet)
            df[sheet] = df[sheet].astype(int)
            df[sheet] = df[sheet].replace(dict(zip(df_l.prev_id, df_l.id)))

        # Turning back NaN values in the respective columns
        df.replace(99999, pd.np.nan, inplace=True)

        # Transforming certains columns to objects
        for col in (batch):
            df[col] = df[col].astype("object")

        return df

class PopulationPipeline(EasyPipeline):
    @staticmethod
    def parameter_list():
        return [
            Parameter(label="Year", name="year", dtype=str),
            Parameter(label="Quarter", name="quarter", dtype=str)
        ]

    @staticmethod
    def steps(params):
        db_connector = Connector.fetch("clickhouse-database", open("../conns.yaml"))

        dtype = {

        }

        download_step = DownloadStep(
            connector=["enoe-1-data", "enoe-2-data"],
            connector_path="conns.yaml"
        )
        transform_step = TransformStep()
        load_step = LoadStep(
            "inegi_enoe_simple", db_connector, if_exists="append", pk=["ent_id", "actual_job_position", "actual_job_industry_group_id", "year" ], dtype=dtype, 
            nullable_list=[]
        )

        return [download_step, transform_step, load_step]
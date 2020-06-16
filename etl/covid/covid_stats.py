
import glob
import numpy as np
import os
import pandas as pd
import requests

from bamboo_lib.helpers import grab_parent_dir
from bamboo_lib.connectors.models import Connector
from bamboo_lib.models import EasyPipeline, PipelineStep, Parameter
from bamboo_lib.steps import DownloadStep, LoadStep, UnzipToFolderStep
from shared import rename_columns, rename_countries
from helpers import norm


class TransformStep(PipelineStep):
    def run_step(self, prev, params):

        data = sorted(glob.glob("*.csv"))

        df = pd.read_csv(data[-1], encoding="latin-1")
        
        r = requests.get("https://api.datamexico.org/tesseract/data?Year=2015&cube=inegi_population&drilldowns=State&measures=Population")
        data_json = r.json()
        states_data = pd.DataFrame(data_json["data"])
        dicto_states_population = dict(zip(states_data["State ID"], states_data["Population"]))

        df.columns = [x.strip().lower().replace(" ", "_") for x in df.columns]

        df1 = df[["entidad_res", "fecha_ingreso", "resultado"]]
        df1 = df1[df1["resultado"] == 1]
        df1 = df1.rename(columns={"entidad_res": "ent_id", 
                                  "fecha_ingreso": "date_id", 
                                  "resultado": "daily_cases"})

        df1 = df1.groupby(["ent_id", "date_id"]).sum().reset_index()
        df1["date_id"] = pd.to_datetime(df1["date_id"])

        ##Add missing dates daily cases
        df1_ = []
        last_day = df1["date_id"].max()
        for a, df_a in df1.groupby("ent_id"):
            
            first_day = df_a["date_id"].min()
            idx = pd.date_range(first_day, last_day)
            df_b = df_a.reindex(idx)
            df_b = pd.DataFrame(df_b.index)
            df_b = df_b.rename(columns={0: "date_id"})
            
            result = pd.merge(df_b, df_a, how="outer", on="date_id")
            
            df1_.append(result)
        df1_ = pd.concat(df1_, sort=False)

        df1_["ent_id"] = df1_["ent_id"].fillna(method="ffill")

        #Deaths
        df2 = df[["entidad_res", "fecha_ingreso", "fecha_def", "resultado"]]

        df2 = df2.rename(columns={"entidad_res": "ent_id", 
                                  "fecha_ingreso": "ingress_date", 
                                  "fecha_def": "death_date", 
                                  "resultado": "daily_deaths"})

        df2 = df2[df2["daily_deaths"] == 1]
        df2 = df2[df2["death_date"]!= "9999-99-99"]

        for i in ["ingress_date", "death_date"]:
            df2[i] = pd.to_datetime(df2[i])
            
        df2["days_between_ingress_and_death"] = df2["death_date"] - df2["ingress_date"]
        df2["days_between_ingress_and_death"] = df2["days_between_ingress_and_death"].dt.days

        df2 = df2.drop(columns="ingress_date")
        df2 = df2.rename(columns={"death_date":"date_id"})

        df2 = df2.groupby(["ent_id", "date_id"]).agg({"daily_deaths": "sum", "days_between_ingress_and_death": "mean"}).reset_index()

        ##Add missing dates deaths 
        df2_ = []
        last_day = df2["date_id"].max()
        for a, df_a in df2.groupby("ent_id"):
            
            first_day = df_a["date_id"].min()
            idx = pd.date_range(first_day, last_day)
            df_b = df_a.reindex(idx)
            df_b = pd.DataFrame(df_b.index)
            df_b = df_b.rename(columns={0:"date_id"})
            
            result = pd.merge(df_b, df_a, how="outer", on="date_id")
            
            df2_.append(result)
        df2_ = pd.concat(df2_, sort=False)

        df2_["ent_id"] = df2_["ent_id"].fillna(method="ffill")

        #Merge daily cases and deaths
        data = pd.merge(df1_, df2, how="outer", on=["date_id", "ent_id"])

        data = data.sort_values(by=["ent_id", "date_id"])

        for col in ["ent_id", "daily_cases", "daily_deaths"]:
            data[col] = data[col].fillna(0).astype(int)

        #Add column of accumulated cases
        df_final = []
        for a, df_a in data.groupby("ent_id"):
            # create temporal df to silence "SettingWithCopyWarning"
            _df = df_a.copy()
            _df["accum_cases"] = _df["daily_cases"].cumsum()
            _df["accum_deaths"] = _df["daily_deaths"].cumsum()

            for i in ["daily_cases", "accum_cases", "daily_deaths", "accum_deaths"]:
                measure = "avg_7_days_{}".format(i)
                _df[measure] = _df[i].rolling(7).mean()
                
            for j in ["daily_cases", "daily_deaths"]:
                measure = "total_last_7_days_{}".format(j)
                _df[measure] = _df[j].rolling(7).sum()

            df_final.append(_df)
        df_final = pd.concat(df_final, sort=False)

        df_final = df_final.rename(columns={"total_last_7_days_daily_cases":"cases_last_7_days", "total_last_7_days_daily_deaths":"deaths_last_7_days"})
        for i in ["cases_last_7_days", "deaths_last_7_days"]:
            df_final[i] = df_final[i].fillna(0).astype(int)

        #Rate per 100.000 inhabitans
        df_final["population"] = df_final["ent_id"].replace(dicto_states_population)

        df_final["rate_daily_cases"] = (df_final["daily_cases"] / df_final["population"]) * 100000
        df_final["rate_accum_cases"] = (df_final["accum_cases"] / df_final["population"]) * 100000

        df_final["rate_daily_deaths"] = (df_final["daily_deaths"] / df_final["population"]) * 100000
        df_final["rate_accum_deaths"] = (df_final["accum_deaths"] / df_final["population"]) * 100000

        df_final = df_final.drop(columns="population")
            
        #Add column with day from first case and death
        for col in ["accum_cases", "accum_deaths"]:
            measure = "{}_day".format(col)
            day = []
            for a, df_a in df_final.groupby("ent_id"):
                default = 0
                for row in df_a.iterrows():
                    if row[1][col] != 0:
                        default = default + 1

                    day.append(default)
            df_final[measure] = day 
            
        df_final = df_final.rename(columns={"accum_cases_day": "cases_day", "accum_deaths_day": "deaths_day"})

        df_final["date_id"] = df_final["date_id"].astype(str).str.replace("-", "").astype(int)

        #Add a column with days, being day one when at least 50 cases accumulate
        day = []
        for a, df_a in df_final.groupby("ent_id"):
            default = 0
            for row in df_a.iterrows():
                if row[1]["accum_cases"] >= 50:
                    default = default + 1

                day.append(default)
        df_final["day_from_50_cases"] = day

        #Add a column with days, being day one when at least 10 deaths accumulate
        day = []
        for a, df_a in df_final.groupby("ent_id"):
            default = 0
            for row in df_a.iterrows():
                if row[1]["accum_deaths"] >= 10:
                    default = default + 1

                day.append(default)
        df_final["day_from_10_deaths"] = day
    
        return df_final


class CovidStatsPipeline(EasyPipeline):
    @staticmethod
    def steps(params):
        db_connector = Connector.fetch("clickhouse-database", open("../conns.yaml"))

        dtypes = {
            "date_id":                          "UInt32",
            "ent_id":                           "UInt8",
            "daily_cases":                      "UInt32",
            "daily_deaths":                     "UInt32",
            "days_between_ingress_and_death":   "Float32",
            "accum_cases":                      "UInt32",
            "accum_deaths":                     "UInt32",
            "rate_daily_cases":                 "Float32",
            "rate_accum_cases":                 "Float32",
            "rate_daily_deaths":                "Float32",
            "rate_accum_deaths":                "Float32",
            "avg_7_days_daily_cases":           "Float32",
            "avg_7_days_accum_cases":           "Float32",
            "avg_7_days_daily_deaths":          "Float32",
            "avg_7_days_accum_deaths":          "Float32",
            "cases_day":                        "UInt16",
            "deaths_day":                       "UInt16",
            "day_from_50_cases":                "UInt16",
            "day_from_10_deaths":               "UInt16",
            "cases_last_7_days":                "UInt16",
            "deaths_last_7_days":               "UInt16",
        }

        download_step = DownloadStep(
            connector="covid-data-mx",
            connector_path="conns.yaml",
            force=True
        )

        path = grab_parent_dir(".") + "/covid/"
        unzip_step = UnzipToFolderStep(compression="zip", target_folder_path=path)
        xform_step = TransformStep()
        load_step = LoadStep(
            "gobmx_covid_stats", db_connector, if_exists="drop", 
            pk=["date_id", "ent_id"], 
            nullable_list=["days_between_ingress_and_death", "avg_7_days_daily_cases", "avg_7_days_accum_cases", 
                           "avg_7_days_daily_deaths", "avg_7_days_accum_deaths"], 
            dtype=dtypes
        )

        return [download_step, unzip_step, xform_step, load_step]

if __name__ == "__main__":
    pp = CovidStatsPipeline()
    pp.run({})
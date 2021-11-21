from typing import Any
import pandas as pd
import numpy as np
import sqlite3
import os
import dataframe_image

from pandas.core.frame import DataFrame
from enum import Enum

class Algorithms(Enum):
    FULL_STATE = 0
    TIMESTAMP = 1
    TOKEN = 2

    def capitalized_name(self):
        ret = []
        for word in self._name_.split("_"):
            ret.append(word.capitalize())
        return " ".join(ret)

def fetch_table(db_name, table_name) -> DataFrame:
    db_conn = sqlite3.connect(db_name)
    df = pd.read_sql_query(f"SELECT * FROM {table_name}", db_conn)
    db_conn.commit()
    db_conn.close()
    return df

control_prefix = "control_"
infrastructure_prefix = "infrastructure_"
statistics_suffix = "_statistics"

class SimulationData:

    db_name: str
    db_full_name: str
    algorithm: Algorithms
    number_of_variables_per_node_table: DataFrame
    simulation_table: DataFrame
    control_table: DataFrame
    infrastructure_table: DataFrame

    def __init__(self, db_name: str, algorithm: Algorithms):
        self.db_name = db_name.replace(".db", "")
        if not os.path.exists(f"figures/{self.db_name}"):
            os.mkdir(f"figures/{self.db_name}")
        self.db_full_name = os.path.abspath(f"simulations/{db_name}")
        self.algorithm = algorithm
        self.number_of_variables_per_node_table = fetch_table(self.db_full_name, "number_of_variables_per_node")
        self.simulation_table = fetch_table(self.db_full_name, "simulation")
        self.control_table = fetch_table(self.db_full_name, control_prefix + algorithm.name.lower() + statistics_suffix)
        self.infrastructure_table = fetch_table(self.db_full_name, infrastructure_prefix + algorithm.name.lower() + statistics_suffix)

    def _build_number_statistics_tables(self, table, varname, param_name, values):
        data_control = []
        data_infrastructure = []

        for value in sorted(values):
            simulation_ids = table.index[table[param_name] == value]
            table_control = self.control_table[self.control_table["simulation_id"].isin(simulation_ids)]
            data_control.append({param_name: value, "min": table_control[varname].min(), 
                    "max": table_control[varname].max(), "avg": table_control[varname].mean()})
            table_infrastructure = self.infrastructure_table[self.infrastructure_table["simulation_id"].isin(simulation_ids)]
            data_infrastructure.append({param_name: value, "min": table_infrastructure[varname].min(), 
                    "max": table_infrastructure[varname].max(), "avg": table_infrastructure[varname].mean()})

        table_control = pd.DataFrame(data_control)
        table_infrastructure = pd.DataFrame(data_infrastructure)

        return {"control":table_control, "infrastructure":table_infrastructure}

    def _generate_number_statistics_graphics(self, fname, tables, param_name):
        if not os.path.exists(f"figures/{self.db_name}/{fname}"):
            os.mkdir(f"figures/{self.db_name}/{fname}")
        for table_key in tables.keys():
            table_name = table_key.capitalize()
            base_folder_name = f"figures/{self.db_name}/{fname}/{table_name}"
            folder_name = base_folder_name + "/" + param_name
            if not os.path.exists(base_folder_name):
                os.mkdir(base_folder_name)
            if not os.path.exists(folder_name):
                os.mkdir(folder_name)
            file_name = folder_name + "/" + self.algorithm.capitalized_name() + f" {fname} {table_name} {param_name}.png"
            styled_table = tables[table_key].style.format("{:.0f}").hide_index().set_properties(**{'text-align': 'center'})
            styled_table.set_table_styles([dict(selector='th', props=[('text-align', 'center')])])
            dataframe_image.export(styled_table, file_name)

    def _generate_number_statistics_tables(self, varname, fname): # varname should be band_width_used or memory_used
        # Tables for number_of_nodes
        number_of_nodes_values = self.simulation_table["number_of_nodes"].unique()
        temp_table = self.simulation_table.set_index("id")
        tables = self._build_number_statistics_tables(self.simulation_table, varname, "number_of_nodes", number_of_nodes_values)
        self._generate_number_statistics_graphics(fname, tables, "Nodes")        

        # Tables for number_of_variables
        temp_table = self.number_of_variables_per_node_table.groupby(["simulation_id"]).agg({"value":"sum"})
        number_of_variables_values = temp_table["value"].unique()
        temp_table.rename(columns={"value":"number_of_variables"}, inplace=True)
        tables = self._build_number_statistics_tables(temp_table, varname, "number_of_variables", number_of_variables_values)
        self._generate_number_statistics_graphics(fname, tables, "Variables")

    def generate_bandwidth_statistics_tables(self):
        self._generate_number_statistics_tables("band_width_used", "Bandwidth")

    def generate_memory_statistics_tables(self):
        self._generate_number_statistics_tables("memory_used", "Memory")

    def _generate_rate_graphics(self, table, rate_name):
        folder_name = f"figures/{self.db_name}/{rate_name}"
        if not os.path.exists(folder_name):
            os.mkdir(folder_name)
        file_name = folder_name + "/" + self.algorithm.capitalized_name() + f" {rate_name}.png"
        styled_table = table.style.format("{:.2f}%").hide_index().set_properties(**{'text-align': 'center'})
        styled_table.set_table_styles([dict(selector='th', props=[('text-align', 'center')])])
        dataframe_image.export(styled_table, file_name)

    def generate_false_negative_rates_tables(self): # TODO: maybe add time component and merge with false positive maybe?
        good_simulation_ids = self.simulation_table["id"][self.simulation_table["category"] == "GOOD"]
        bad_simulation_ids = self.simulation_table["id"][self.simulation_table["category"] == "BAD"]

        table = self.control_table.groupby(["simulation_id"]).agg({"error_detected":"sum"})
        table_good = table.loc[good_simulation_ids]
        table_bad = table.loc[bad_simulation_ids]

        false_negative_rates = dict()
        false_negative_rates["all"] = (len(table[(table["error_detected"] == 0)]) / len(table)) * 100
        false_negative_rates["good"] = (len(table_good[(table_good["error_detected"] == 0)]) / len(table_good)) * 100
        false_negative_rates["bad"] = (len(table_bad[(table_bad["error_detected"] == 0)]) / len(table_bad)) * 100

        table = pd.DataFrame([false_negative_rates])
        self._generate_rate_graphics(table, "False Negative Rates")

        return table

    def generate_false_positive_rates_tables(self):
        good_simulation_ids = self.simulation_table["id"][self.simulation_table["category"] == "GOOD"]
        bad_simulation_ids = self.simulation_table["id"][self.simulation_table["category"] == "BAD"]

        table = self.infrastructure_table.groupby(["simulation_id"]).agg({"error_detected":"sum"})
        table_good = table.loc[good_simulation_ids]
        table_bad = table.loc[bad_simulation_ids]

        false_positive_rates = dict()
        false_positive_rates["all"] = (len(table[(table["error_detected"] > 0)]) / len(table)) * 100
        false_positive_rates["good"] = (len(table_good[(table_good["error_detected"] > 0)]) / len(table_good)) * 100
        false_positive_rates["bad"] = (len(table_bad[(table_bad["error_detected"] > 0)]) / len(table_bad)) * 100

        table = pd.DataFrame([false_positive_rates])
        self._generate_rate_graphics(table, "False Positive Rates")

        return table

    def generate_error_curves(self):
        if not os.path.exists(f"figures/{self.db_name}/Error Curves"):
            os.mkdir(f"figures/{self.db_name}/Error Curves")

        table = self.control_table.groupby(["time"]).agg({"error_detected":"sum"}).cumsum()
        title = self.algorithm.capitalized_name() + " Control Error Curve"
        plot = table.plot(title=title, xlabel="Time", ylabel="Errors (cumulative)")
        fig = plot.get_figure()
        if not os.path.exists(f"figures/{self.db_name}/Error Curves/Control"):
            os.mkdir(f"figures/{self.db_name}/Error Curves/Control")
        fig.savefig(f"figures/{self.db_name}/Error Curves/Control/{title}.png")

        table = self.infrastructure_table.groupby(["time"]).agg({"error_detected":"sum"}).cumsum()
        title = self.algorithm.capitalized_name() + " Infrastructure Error Curve"
        plot = table.plot(title=title, xlabel="Time", ylabel="Errors (cumulative)")
        fig = plot.get_figure()
        if not os.path.exists(f"figures/{self.db_name}/Error Curves/Infrastructure"):
            os.mkdir(f"figures/{self.db_name}/Error Curves/Infrastructure")
        fig.savefig(f"figures/{self.db_name}/Error Curves/Infrastructure/{title}.png")

def detection_delay_statistics(statistics: DataFrame):
    """
    Returns the Statistics for the Detection Delay
    """
    # TODO

def evaluate_statistics(db_name):
    for algorithm in Algorithms:
        simulation_data = SimulationData(db_name, algorithm)
        simulation_data.generate_false_negative_rates_tables()
        simulation_data.generate_false_positive_rates_tables()
        simulation_data.generate_bandwidth_statistics_tables()
        simulation_data.generate_memory_statistics_tables()
        simulation_data.generate_error_curves()


if not os.path.exists("figures"):
    os.mkdir("figures")

for db in os.listdir("simulations"):
    evaluate_statistics(db)
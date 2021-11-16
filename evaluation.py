import pandas as pd
import numpy as np
import sqlite3

from pandas.core.frame import DataFrame

def fetch_table(db_name, table_name) -> DataFrame:
    db_conn = sqlite3.connect(db_name)
    df = pd.read_sql_query(f"SELECT * FROM {table_name}", db_conn)
    db_conn.commit()
    db_conn.close()
    return df

def aggregate_statistics(statistics: DataFrame):
    statistics = statistics.drop(labels=["id"], axis=1)
    statistics = statistics.groupby(by=["simulation_id"]).agg({"time":"max", "error_detected":"sum", "band_width_used":"sum"})
    return statistics

def false_negative_rate(statistics: DataFrame):
    """
    Returns the rate of false negatives
    """
    aggregated_statistics = aggregate_statistics(statistics)
    return len(aggregated_statistics[(aggregated_statistics["error_detected"] == 0)]) / len(aggregated_statistics)

def false_positive_rate(statistics: DataFrame):
    """
    Returns the rate of false positives
    """
    aggregated_statistics = aggregate_statistics(statistics)
    return len(aggregated_statistics[(aggregated_statistics["error_detected"] > 0)]) / len(aggregated_statistics)

def evaluate_statistics(db_name):
    control_full_state_statistics = fetch_table(db_name, "control_full_state_statistics")
    infrastructure_full_state_statistics = fetch_table(db_name, "infrastructure_full_state_statistics")
    control_timestamp_statistics = fetch_table(db_name, "control_timestamp_statistics")
    infrastructure_timestamp_statistics = fetch_table(db_name, "infrastructure_timestamp_statistics")
    control_token_statistics = fetch_table(db_name, "control_token_statistics")
    infrastructure_token_statistics = fetch_table(db_name, "infrastructure_token_statistics")

    print(false_negative_rate(control_full_state_statistics))
    print(false_positive_rate(infrastructure_full_state_statistics))
    print(false_negative_rate(control_timestamp_statistics))
    print(false_positive_rate(infrastructure_timestamp_statistics))
    print(false_negative_rate(control_token_statistics))
    print(false_positive_rate(infrastructure_token_statistics))

evaluate_statistics("simulation20211117002528.db")
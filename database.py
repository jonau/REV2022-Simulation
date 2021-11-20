from simulation_objects import RuleFunction, RuleFunctionElement, State
from base_model import ParameterCategories, SimulationParameters
from error_model import Statistics
from datetime import datetime
from delay_functions import DelayTypes

import typing
import sqlite3
import sys

def create_table(table_name: str, cls=None, type=None, reference=None,):
    fields = []

    fields.append(('id', 'INTEGER PRIMARY KEY'))
    if reference:
        fields.append((reference+'_id', 'INTEGER'))

    def add_field(field_name, type, sub_table_name):
        if type == int:
            fields.append((field_name, 'INTEGER'))
        elif type == float:
            fields.append((field_name, 'REAL'))
        elif type == str:
            fields.append((field_name, 'TEXT'))
        elif type == bool:
            fields.append((field_name, 'INTEGER'))
        elif type == State:
            fields.append((field_name, 'INTEGER'))
        elif type == DelayTypes:
            fields.append((field_name, 'TEXT'))
        elif type == ParameterCategories:
            fields.append((field_name, 'TEXT'))
        elif type == RuleFunction:
            create_table(sub_table_name+'_elements', type=int, reference=table_name)
        elif hasattr(type, '_name') and type._name == 'List' or hasattr(type, "_gorg") and type._gorg == typing.List:
            create_table(sub_table_name, type=type.__args__[0], reference=table_name)
        else:
            raise ValueError(f'Unknown type {type}')
    if cls:
        for field, type in cls.__annotations__.items():
            add_field(field, type, field)
    elif type:
        add_field('value', type, table_name)

    print(f"CREATE TABLE IF NOT EXISTS {table_name} ({','.join([f[0]+' '+f[1] for f in fields])})")
    con.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({','.join([f[0]+' '+f[1] for f in fields])})")

def insert_table(table_name: str, cls=None, value=None, reference=None, reference_value=None):
    fields = []

    if reference:
        fields.append((reference+'_id', reference_value))

    reference_id=None

    def add_field(field_name, value, sub_table_name):
        if value.__class__ == int:
            fields.append((field_name, value))
        elif value.__class__ == float:
            fields.append((field_name, value))
        elif value.__class__ == str:
            fields.append((field_name, value))
        elif value.__class__ == bool:
            fields.append((field_name, value))
        elif value.__class__ == State:
            fields.append((field_name, value.int_representation))
        elif value.__class__ == DelayTypes:
            fields.append((field_name, value.name))
        elif value.__class__ == ParameterCategories:
            fields.append((field_name, value.name))
        elif value.__class__ == RuleFunctionElement:
            fields.append((field_name, value.int_representation))
        elif value.__class__ == RuleFunction:
            if reference_id:
                for v in value.elements:
                    insert_table(sub_table_name+'_elements', value=v, reference=table_name,reference_value=reference_id)
        elif isinstance(value, list):
            if reference_id:
                for v in value:
                    insert_table(sub_table_name, value=v, reference=table_name, reference_value=reference_id)
        else:
            raise ValueError(f'Unknown type {value.__class__}')
    if cls:
        for field, value in cls.__class__.__annotations__.items():
            add_field(field, getattr(cls, field), field)
    elif value:
        add_field('value', value, table_name)

    reference_id=con.execute(f"INSERT INTO {table_name}({','.join([f[0] for f in fields])}) VALUES ({','.join(['?' for f in fields])})",[f[1] for f in fields]).lastrowid

    if cls:
        for field, value in cls.__class__.__annotations__.items():
            add_field(field, getattr(cls, field), field)
    elif value:
        add_field('value', value, table_name)

    return reference_id

def write_statistics(prefix, env, simulation_reference):
    for statistic in env.token_statistics:
        insert_table(prefix+'token_statistics', cls=statistic, reference='simulation', reference_value=simulation_reference)
    for statistic in env.timestamp_statistics:
        insert_table(prefix+'timestamp_statistics', cls=statistic, reference='simulation', reference_value=simulation_reference)
    for statistic in env.full_state_statistics:
        insert_table(prefix+'full_state_statistics', cls=statistic, reference='simulation', reference_value=simulation_reference)

def commit():
    con.commit()

database_name='simulation'+datetime.now().strftime("%Y%m%d%H%M")+'.db'
if len(sys.argv)>=2:
    database_name=sys.argv[1]
con = sqlite3.connect(database_name)

create_table('simulation', cls=SimulationParameters)
create_table('control_full_state_statistics', cls=Statistics, reference='simulation')
create_table('control_timestamp_statistics', cls=Statistics, reference='simulation')
create_table('control_token_statistics', cls=Statistics, reference='simulation')
create_table('infrastructure_full_state_statistics', cls=Statistics, reference='simulation')
create_table('infrastructure_timestamp_statistics', cls=Statistics, reference='simulation')
create_table('infrastructure_token_statistics', cls=Statistics, reference='simulation')

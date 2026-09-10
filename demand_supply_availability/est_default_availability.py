# import necessary libraries
import pandas as pd
import numpy as np
import os
from django.conf import settings
import argparse
import json
import math

# define list of construction materials and years for which availability will be estimated
MATERIALS = [
    "Cement",
    "Aggregate",
    "Fly ash (conventional)",
    "Fly ash (alternative)",
    "Blast furnace slag",
]
YEARS = list(range(2025, 2051))

# construct path to availability by material, state, and year
base_path = os.path.join(
    settings.BASE_DIR, "demand_supply_availability/static/raw_data/availability_data.xlsx"
)

def est_default_availability(material, year):
    """
    Estimates default availability for a given material and year.

    Args:
        material (list): construction material (options include "Cement", "Aggregate", "Fly ash (conventional)", "Fly ash (alternative)", "Blast furnace slag", and "Steel")
        year (into): year of desired material availability (options include 2025-2050)

    """
    # identify sheet name based on material type
    if material == "Cement":
        demand_sheet_name = "1. Cement demand"
        supply_sheet_name = "S8" 
    elif material == "Aggregate":
        demand_sheet_name = "3. Aggregate demand"
        supply_sheet_name = "S10" 
    elif material == "Fly ash (conventional)":
        demand_sheet_name = "4. Fly ash demand"    
        supply_sheet_name = "7a. Fly ash supply" #use lower bound, per Josefine's recommendation
    elif material == "Fly ash (alternative)":
        demand_sheet_name = "4. Fly ash demand"
        supply_sheet_name = "9c. Recovered FA supply" #use lower bound, per Josefine's recommendation 
    elif material == "Blast furnace slag":
        demand_sheet_name = "5. Slag demand"
        supply_sheet_name = "8a. Slag supply" #use lower bound, per Josefine's recommendation
    elif material == "Steel":
        demand_sheet_name = "" #note, steel data forthcoming
        supply_sheet_name = "" #note, steel data forthcoming
    else:
        return "Not a valid material. Please select from the following options: Cement, Aggregate, Fly ash (conventional), Fly ash (alternative), Blast furnace slag, or Steel."    

    # read in supply and demand data for the specified material
    if material == "Cement":
        demand_df = pd.read_excel(base_path, sheet_name=demand_sheet_name, header=2)
        demand_df.rename(columns = {'Unnamed: 0':'State'}, inplace = True)
        demand_df = demand_df.loc[demand_df['State'] != 'USA']
        
        # note, we only have cement plant capacity for the state of California in 2025
        ca_supply = pd.read_excel(base_path, sheet_name=supply_sheet_name, header=1)
        ca_supply = ca_supply.loc[ca_supply['Plants'] == 'CA capacity', 'Cement capacity (MMT)'].values[0] * 10**6 #MT

        # reformat supply data to match demand data format
        years = list(range(2025, 2051))
        supply_df = pd.DataFrame({year: np.nan for year in years}, index=[0])
        supply_df['State'] = pd.Series(dtype='object')
        supply_df.loc[0, 'State'] = 'California'
        supply_df.loc[0, supply_df.columns[:-1]] = ca_supply

    elif material == "Aggregate":
        # note, this sheet contains demand for disaggregated by type of aggregate
        demand_df = pd.read_excel(base_path, sheet_name=demand_sheet_name, header=2)

        # seperate into dataframes for natural and crushed, fine and coarse demand dataframes
        natural_fine_demand = demand_df.iloc[0:51]
        crushed_fine_demand = demand_df.iloc[53:104]
        natural_coarse_demand = demand_df.iloc[106:157]
        crushed_coarse_demand = demand_df.iloc[159:210]
        
        # sum demand for all types of aggregate by state and year
        combined = pd.concat([natural_fine_demand, crushed_fine_demand, natural_coarse_demand, crushed_coarse_demand], ignore_index=True)
        demand_df = combined.groupby('Natural fine aggs', as_index=False).sum()
        demand_df.rename(columns = {'Natural fine aggs':'State'}, inplace = True)
        demand_df = demand_df.loc[demand_df['State'] != 'USA']
        demand_df[list(range(2025, 2051))] = demand_df[list(range(2025, 2051))] * 1000

        # note, this sheet contains supply for disaggregated by type of aggregate
        supply_temp = pd.read_excel(base_path, sheet_name=supply_sheet_name, header=1, usecols=['Total CA', 'Reserves (MMT)']).iloc[:6] * 10**6 #MT

        #reformat supply data to match demand data format
        row = {'State': 'California'}
        for year in range(2025, 2056):
            if year <= 2035:
                row[year] = supply_temp.loc[supply_temp['Total CA'].str.contains('10 or Fewer Years'), 'Reserves (MMT)'].values[0]
            elif year <= 2045:
                row[year] = supply_temp.loc[supply_temp['Total CA'].str.contains('11 to 20 Years'), 'Reserves (MMT)'].values[0]
            else:
                row[year] = supply_temp.loc[supply_temp['Total CA'].str.contains('21 to 30 Years'), 'Reserves (MMT)'].values[0]
            supply_df = pd.DataFrame([row])
    else:
        demand_df = pd.read_excel(base_path, sheet_name=demand_sheet_name, header=2)
        demand_df.rename(columns = {'Unnamed: 0':'State'}, inplace = True)
        demand_df = demand_df.loc[demand_df['State'] != 'USA'].iloc[0:50]
        demand_df[list(range(2025, 2051))] = demand_df[list(range(2025, 2051))] * 1000 #MT
        supply_df = pd.read_excel(base_path, sheet_name=supply_sheet_name, header=2)
        supply_df.rename(columns = {'Unnamed: 0':'State'}, inplace = True)
        supply_df = supply_df.loc[supply_df['State'] != 'USA'].iloc[0:50]
        supply_df[list(range(2025, 2051))] = supply_df[list(range(2025, 2051))] * 1000 #MT

    # filter to 2025-2050 data for both demand and supply dataframes
    cols = ['State'] + list(range(2025, 2051))
    supply_df = supply_df[cols] 
    demand_df = demand_df[cols]

    # fill NaN values with zeroes
    supply_df.fillna(0, inplace=True)
    demand_df.fillna(0, inplace=True)

    # create dataframe for statewide material availability by subtracting demand from supply
    if material == "Cement":
        # note, because we only have cement plant capacity for the state of California in 2025, we will only calculate availability for California in 2025
        year_cols = list(range(2025, 2051))
        availability_df = (supply_df.set_index('State')[year_cols].sub(demand_df.loc[demand_df['State'] == 'California'].set_index('State')[year_cols],fill_value=0).reset_index())
        
        # add unknown columns for other states
        availability_df = pd.concat([availability_df, pd.DataFrame({'State': ['Alabama', 'Alaska', 'Arizona', 'Arkansas', 'Colorado', 'Connecticut', 'Delaware', 'Florida', 'Georgia', 'Hawaii', 'Idaho', 'Illinois', 'Indiana', 'Iowa', 'Kansas', 'Kentucky', 'Louisiana', 'Maine', 'Maryland', 'Massachusetts', 'Michigan', 'Minnesota', 'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada', 'New Hampshire', 'New Jersey', 'New Mexico', 'New York', 'North Carolina', 'North Dakota', 'Ohio', 'Oklahoma', 'Oregon', 'Pennsylvania', 'Rhode Island', 'South Carolina', 'South Dakota', 'Tennessee', 'Texas', 'Utah', 'Vermont', 'Virginia', 'Washington', 'West Virginia','Wisconsin','Wyoming'], 2025: [np.nan]*49})], ignore_index=True)
    elif material == "Aggregate":
        # note, because we only have permitted aggregate for the state of California (2025-2050), we will only calculate availability for California
        year_cols = list(range(2025, 2051))
        availability_df = (supply_df.set_index('State')[year_cols].sub(demand_df.loc[demand_df['State'] == 'California'].set_index('State')[year_cols],fill_value=0).reset_index())
        
        # add unknown columns for other states
        availability_df = pd.concat([availability_df, pd.DataFrame({'State': ['Alabama', 'Alaska', 'Arizona', 'Arkansas', 'Colorado', 'Connecticut', 'Delaware', 'Florida', 'Georgia', 'Hawaii', 'Idaho', 'Illinois', 'Indiana', 'Iowa', 'Kansas', 'Kentucky', 'Louisiana', 'Maine', 'Maryland', 'Massachusetts', 'Michigan', 'Minnesota', 'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada', 'New Hampshire', 'New Jersey', 'New Mexico', 'New York', 'North Carolina', 'North Dakota', 'Ohio', 'Oklahoma', 'Oregon', 'Pennsylvania', 'Rhode Island', 'South Carolina', 'South Dakota', 'Tennessee', 'Texas', 'Utah', 'Vermont', 'Virginia', 'Washington', 'West Virginia','Wisconsin','Wyoming'], 2025: [np.nan]*49})], ignore_index=True)
    else:
        year_cols = list(range(2025, 2051))
        availability_df = (supply_df.set_index('State')[year_cols].sub(demand_df.set_index('State')[year_cols], fill_value=0).reset_index())

    # set path for processed_data 
    processed_data_path = os.path.join(settings.BASE_DIR, "demand_supply_availability/static/processed_data")
    os.makedirs(processed_data_path, exist_ok=True)

    # export supply, demand, and availability to JSON format for visualization in webtool
    supply_df.to_json(os.path.join(processed_data_path, f"supply_{material.lower()}.json"), orient="records")
    print(f"supply_{material.lower()}.json updated.")
    demand_df.to_json(os.path.join(processed_data_path, f"demand_{material.lower()}.json"), orient="records")
    print(f"demand_{material.lower()}.json updated.")
    availability_df.to_json(os.path.join(processed_data_path, f"availability_{material.lower()}.json"), orient="records")
    print(f"availability_{material.lower()}.json updated.")

    return supply_df, demand_df, availability_df

def _frame_to_state_year(df):
    """Convert a State + year-columns dataframe into {state: {year: value|None}}."""
    out = {}
    for _, row in df.iterrows():
        vals = {}
        for y in YEARS:
            v = row.get(y)
            if v is None or (isinstance(v, float) and math.isnan(v)):
                vals[str(y)] = None
            else:
                vals[str(y)] = float(v)
        out[row["State"]] = vals
    return out


def build_map_data(materials=None, output_path=None, log=print):
    """Build a single JSON payload of supply/demand/availability for the map.

    Returns the path the file was written to.
    """
    materials = materials or MATERIALS

    payload = {
        "years": YEARS,
        "units": "metric tonnes",
        "data": {"supply": {}, "demand": {}, "availability": {}},
    }

    for material in materials:
        log(f"  {material}...")
        supply_df, demand_df, availability_df = est_default_availability(material, YEARS[0])
        payload["data"]["supply"][material] = _frame_to_state_year(supply_df)
        payload["data"]["demand"][material] = _frame_to_state_year(demand_df)
        payload["data"]["availability"][material] = _frame_to_state_year(availability_df)

    if output_path is None:
        processed = os.path.join(
            settings.BASE_DIR, "demand_supply_availability/static/processed_data"
        )
        os.makedirs(processed, exist_ok=True)
        output_path = os.path.join(processed, "map_data.json")

    with open(output_path, "w") as f:
        json.dump(payload, f)

    return output_path




    
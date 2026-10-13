# import necessary libraries
import pandas as pd
import numpy as np
import os
from django.conf import settings
import json
import math

# define list of construction materials, scenarios, and years for which availability will be estimated
MATERIALS = [
    "Cement",
    "Aggregate",
    "Fly ash (conventional)",
    "Fly ash (alternative)",
    "Blast furnace slag",
    "Pozzolan"
]
years = list(range(2025, 2051))
SCENARIOS = [
    "Increased/continued use of coal for electricity generation",
    "Reduced use of coal for electricity generation",
    "Increased/continued operation of blast furnaces for domestic steel production",
    "Retirement of blast furnaces for domestic steel production",
    "No increase in domestic cement production capacity",
    "Fast track to utilization of natural pozzolans",
    "Fast track to harvesting and processing recovered fly ash for use as SCMs",
    "Cement/steel plant shutdown (temporary or long term)", #NTS, needs to be modified once steel data is available
    None
    # "Increased production of blended cements (blended cement = clinker + gypsum + SCMs)",
    # "Import disruptions"
]

# construct path to availability by material, state, and year
base_path = os.path.join(
    settings.BASE_DIR, "demand_supply_availability/static/raw_data/availability_data.xlsx"
)

def est_availability(material, scenario=None):
    """
    Estimates default availability for a given material.
    """
    if material == "Cement":
        demand_sheet_name = "1. Cement demand"
        supply_sheet_name = "S8"
        if scenario == "No increase in domestic cement production capacity":
            supply_sheet_name = 'S8' #same as default scenario
        elif scenario == 'Cement/steel plant shutdown (temporary or long term)':
            supply_sheet_name = 'S8'
    elif material == "Aggregate":
        demand_sheet_name = "3. Aggregate demand"
        supply_sheet_name = "S10" 
    elif material == "Fly ash (conventional)":
        demand_sheet_name = "4. Fly ash demand"    
        supply_sheet_name = "7a. Fly ash supply"
        if scenario == "Increased/continued use of coal for electricity generation":
            supply_sheet_name = '7b. Fly ash supply'
        elif scenario == "Reduced use of coal for electricity generation": 
            supply_sheet_name = '7a. Fly ash supply'
    elif material == "Fly ash (alternative)":
        demand_sheet_name = "4. Fly ash demand"
        supply_sheet_name = "9c. Recovered FA supply" 
        if scenario == "Fast track to harvesting and processing recovered fly ash for use as SCMs":
            supply_sheet_name = '9a. Recovered FA supply'
    elif material == "Blast furnace slag":
        demand_sheet_name = "5. Slag demand"
        supply_sheet_name = "8a. Slag supply"
        if scenario == "Increased/continued operation of blast furnaces for domestic steel production":
            supply_sheet_name = '8b. Slag supply'
        elif scenario == "Retirement of blast furnaces for domestic steel production":    
            supply_sheet_name = '8a. Slag supply'
    elif material == "Pozzolan":
        supply_sheet_name = "10. Natural pozz. supply"
        if scenario == "Fast track to utilization of natural pozzolans":
            pozzolon_flag = 'S1: Fast'
        else:
            pozzolon_flag = 'S2: Medium'    
    elif material == "Steel":
        demand_sheet_name = ""
        supply_sheet_name = ""
    else:
        return "Not a valid material."    
                        
    if material == "Cement":
        demand_df = pd.read_excel(base_path, sheet_name=demand_sheet_name, header=2)
        demand_df.rename(columns = {'Unnamed: 0':'State'}, inplace = True)
        demand_df = demand_df.loc[demand_df['State'] != 'USA']
        demand_df[years] = demand_df[years] * 1000 / 10**6 * 1.10231

        ca_supply = pd.read_excel(base_path, sheet_name=supply_sheet_name, header=1)
        ca_supply = ca_supply.loc[ca_supply['Plants'] == 'CA capacity', 'Cement capacity (MMT)'].values[0] * 1.10231

        supply_df = pd.DataFrame({year: np.nan for year in years}, index=[0])
        supply_df['State'] = pd.Series(dtype='object')
        supply_df.loc[0, 'State'] = 'California'
        supply_df.loc[0, supply_df.columns[:-1]] = ca_supply

        #account for scenarios that affect supply
        if scenario == None:
            supply_df.loc[0, supply_df.columns[1:-1]] = None
        elif scenario == 'Cement/steel plant shutdown (temporary or long term)':
            supply_df.loc[0, supply_df.columns[:-1]] = 0    

    elif material == "Aggregate":
        demand_df = pd.read_excel(base_path, sheet_name=demand_sheet_name, header=2)
        natural_fine_demand = demand_df.iloc[0:51]
        crushed_fine_demand = demand_df.iloc[53:104]
        natural_coarse_demand = demand_df.iloc[106:157]
        crushed_coarse_demand = demand_df.iloc[159:210]
        combined = pd.concat([natural_fine_demand, crushed_fine_demand, natural_coarse_demand, crushed_coarse_demand], ignore_index=True)
        demand_df = combined.groupby('Natural fine aggs', as_index=False).sum()
        demand_df.rename(columns = {'Natural fine aggs':'State'}, inplace = True)
        demand_df = demand_df.loc[demand_df['State'] != 'USA']
        demand_df[years] = demand_df[years] * 1000 / 10**6 * 1.10231

        supply_temp = pd.read_excel(base_path, sheet_name=supply_sheet_name, header=1, usecols=['Total CA', 'Reserves (MMT)']).iloc[:6]
        row = {'State': 'California'}
        for year in range(2025, 2056):
            if year <= 2035:
                row[year] = supply_temp.loc[supply_temp['Total CA'].str.contains('10 or Fewer Years'), 'Reserves (MMT)'].values[0]
            elif year <= 2045:
                row[year] = supply_temp.loc[supply_temp['Total CA'].str.contains('11 to 20 Years'), 'Reserves (MMT)'].values[0]
            else:
                row[year] = supply_temp.loc[supply_temp['Total CA'].str.contains('21 to 30 Years'), 'Reserves (MMT)'].values[0]
        supply_df = pd.DataFrame([row])
        supply_df[years] = supply_df[years]  * 1.10231
    elif material == "Pozzolan":
        ca_supply = pd.read_excel(base_path, sheet_name=supply_sheet_name, header=2)
        supply_df = ca_supply.loc[ca_supply['California'] == pozzolon_flag]
        supply_df.rename(columns = {'California':'State'}, inplace = True)
        supply_df.loc[supply_df['State'] == pozzolon_flag, 'State'] = 'California'
        supply_df[years] = supply_df[years] * 1.10231
    else:
        demand_df = pd.read_excel(base_path, sheet_name=demand_sheet_name, header=2)
        demand_df.rename(columns = {'Unnamed: 0':'State'}, inplace = True)
        demand_df = demand_df.loc[demand_df['State'] != 'USA'].iloc[0:50]
        demand_df[years] = demand_df[years] * 1000 / 10**6 * 1.10231
        supply_df = pd.read_excel(base_path, sheet_name=supply_sheet_name, header=2)
        supply_df.rename(columns = {'Unnamed: 0':'State'}, inplace = True)
        supply_df = supply_df.loc[supply_df['State'] != 'USA'].iloc[0:50]
        supply_df[years] = supply_df[years] * 1000 / 10**6 * 1.10231
    
    supply_df = supply_df[['State'] + years] 
    if material != "Cement":
        supply_df.fillna(0, inplace=True)

    if material != "Pozzolan":
        demand_df = demand_df[['State'] + years]
        demand_df.fillna(0, inplace=True)

    if material == "Cement":
        if scenario == None:
            availability_df = (supply_df.set_index('State')[years].sub(demand_df.loc[demand_df['State'] == 'California'].set_index('State')[years]).reset_index())
            availability_df = pd.concat([availability_df, pd.DataFrame({'State': ['Alabama', 'Alaska', 'Arizona', 'Arkansas', 'Colorado', 'Connecticut', 'Delaware', 'Florida', 'Georgia', 'Hawaii', 'Idaho', 'Illinois', 'Indiana', 'Iowa', 'Kansas', 'Kentucky', 'Louisiana', 'Maine', 'Maryland', 'Massachusetts', 'Michigan', 'Minnesota', 'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada', 'New Hampshire', 'New Jersey', 'New Mexico', 'New York', 'North Carolina', 'North Dakota', 'Ohio', 'Oklahoma', 'Oregon', 'Pennsylvania', 'Rhode Island', 'South Carolina', 'South Dakota', 'Tennessee', 'Texas', 'Utah', 'Vermont', 'Virginia', 'Washington', 'West Virginia','Wisconsin','Wyoming'], 2025: [np.nan]*49})], ignore_index=True)
        else:    
            availability_df = (supply_df.set_index('State')[years].sub(demand_df.loc[demand_df['State'] == 'California'].set_index('State')[years],fill_value=0).reset_index())
            availability_df = pd.concat([availability_df, pd.DataFrame({'State': ['Alabama', 'Alaska', 'Arizona', 'Arkansas', 'Colorado', 'Connecticut', 'Delaware', 'Florida', 'Georgia', 'Hawaii', 'Idaho', 'Illinois', 'Indiana', 'Iowa', 'Kansas', 'Kentucky', 'Louisiana', 'Maine', 'Maryland', 'Massachusetts', 'Michigan', 'Minnesota', 'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada', 'New Hampshire', 'New Jersey', 'New Mexico', 'New York', 'North Carolina', 'North Dakota', 'Ohio', 'Oklahoma', 'Oregon', 'Pennsylvania', 'Rhode Island', 'South Carolina', 'South Dakota', 'Tennessee', 'Texas', 'Utah', 'Vermont', 'Virginia', 'Washington', 'West Virginia','Wisconsin','Wyoming'], 2025: [np.nan]*49})], ignore_index=True)
    elif material == "Aggregate":
        availability_df = (supply_df.set_index('State')[years].sub(demand_df.loc[demand_df['State'] == 'California'].set_index('State')[years],fill_value=0).reset_index())
        availability_df = pd.concat([availability_df, pd.DataFrame({'State': ['Alabama', 'Alaska', 'Arizona', 'Arkansas', 'Colorado', 'Connecticut', 'Delaware', 'Florida', 'Georgia', 'Hawaii', 'Idaho', 'Illinois', 'Indiana', 'Iowa', 'Kansas', 'Kentucky', 'Louisiana', 'Maine', 'Maryland', 'Massachusetts', 'Michigan', 'Minnesota', 'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada', 'New Hampshire', 'New Jersey', 'New Mexico', 'New York', 'North Carolina', 'North Dakota', 'Ohio', 'Oklahoma', 'Oregon', 'Pennsylvania', 'Rhode Island', 'South Carolina', 'South Dakota', 'Tennessee', 'Texas', 'Utah', 'Vermont', 'Virginia', 'Washington', 'West Virginia','Wisconsin','Wyoming'], 2025: [np.nan]*49})], ignore_index=True)
    elif material == "Pozzolan":
        availability_df = None
    else:
        availability_df = (supply_df.set_index('State')[years].sub(demand_df.set_index('State')[years], fill_value=0).reset_index())

    processed_data_path = os.path.join(settings.BASE_DIR, "demand_supply_availability/static/processed_data")
    os.makedirs(processed_data_path, exist_ok=True)

    if material == "Pozzolan":
        supply_df.to_json(os.path.join(processed_data_path, f"supply_{material.lower()}.json"), orient="records")
        return supply_df
    else:    
        supply_df.to_json(os.path.join(processed_data_path, f"supply_{material.lower()}.json"), orient="records")
        demand_df.to_json(os.path.join(processed_data_path, f"demand_{material.lower()}.json"), orient="records")
        availability_df.to_json(os.path.join(processed_data_path, f"availability_{material.lower()}.json"), orient="records")
        return supply_df, demand_df, availability_df

def _frame_to_state_year(df):
    out = {}
    for _, row in df.iterrows():
        vals = {}
        for y in years:
            v = row.get(y)
            if v is None or (isinstance(v, float) and math.isnan(v)):
                vals[str(y)] = None
            else:
                vals[str(y)] = float(v)
        out[row["State"]] = vals
    return out

def build_map_data(materials=None, scenarios=None, output_path=None, log=print):
    """Build separate JSON payloads for each scenario."""
    materials = materials or MATERIALS
    
    # Normalize scenarios to a list
    if scenarios is None:
        scenarios_to_process = [None] 
    elif isinstance(scenarios, str):
        scenarios_to_process = [scenarios]
    else:
        scenarios_to_process = scenarios

    written_files = []

    for current_scenario in scenarios_to_process:
        log(f"Processing Scenario: {current_scenario if current_scenario else 'Baseline'}...")
        
        payload = {
            "years": years,
            "units": "million U.S. tons",
            "data": {"supply": {}, "demand": {}, "availability": {}},
        }

        for material in materials:
            if material == "Pozzolan":
                supply_df = est_availability(material, current_scenario)
                payload["data"]["supply"][material] = _frame_to_state_year(supply_df)
            else:
                supply_df, demand_df, availability_df = est_availability(material, current_scenario)
                payload["data"]["supply"][material] = _frame_to_state_year(supply_df)
                payload["data"]["demand"][material] = _frame_to_state_year(demand_df)
                payload["data"]["availability"][material] = _frame_to_state_year(availability_df)

        # File Path Logic
        processed_dir = os.path.join(settings.BASE_DIR, "demand_supply_availability/static/processed_data")
        os.makedirs(processed_dir, exist_ok=True)

        if current_scenario is None:
            current_output_path = os.path.join(processed_dir, "map_data.json")
        else:
            slug = current_scenario.lower().replace(" ", "_").replace("/", "_")
            current_output_path = os.path.join(processed_dir, f"map_data_{slug}.json")

        # If a specific path was passed via --output, we use that instead
        if output_path:
            current_output_path = output_path

        with open(current_output_path, "w") as f:
            json.dump(payload, f)
        
        written_files.append(current_output_path)
        log(f"  Wrote {os.path.basename(current_output_path)}")

    return written_files
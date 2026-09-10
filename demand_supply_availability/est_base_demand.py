# import necessary libraries
import pandas as pd
import os
from django.conf import settings
import argparse

# construct path to material demand by building archetype, as compiled by Isabella Cicco at University of Pittsburgh
base_mat_demand_path = os.path.join(
    settings.BASE_DIR, "demand_supply_availability/static/raw_data/Archetypes MIC detailed.xlsx"
)

# read in material demand and reformat
base_mat_demand = pd.read_excel(base_mat_demand_path, header=1)
base_mat_demand.rename(columns={"Unnamed: 0": "Building Archetype"}, inplace=True)
base_mat_demand["Building Archetype"] = [
    atype.split(",")[0] for atype in base_mat_demand["Building Archetype"]
]
base_mat_demand.replace("-", 0, inplace=True)

def est_base_demand(
    new_building_types,
    new_building_sizes,
    state,
    reused_materials,
    old_building_types=None,
    old_building_sizes=None,
):
    """
    Estimates material demand for buildings, with the option of using materials sourced from demolished buildings, and exports to a .JSON file for front-end visualization

    Args:
        new_building_types (list): archetype(s) of new building(s)
        new_building_sizes (list): size(s) of new building(s) (GSF)
        state (str): state (e.g., California); used to determine regional concrete mixture design
        reused_materials (bool): whether reused materials should be included
        old_building_types (list, optional): archetype(s) of demolished building(s)
        old_building_sizes (list, optional): size(s) of demolished building(s) (GSF)

    """
    # identify material demand for selected building archetype
    type_demand = base_mat_demand[
        base_mat_demand["Building Archetype"].isin(new_building_types)
    ]

    # add size column for new buildings
    i = 0
    for new_building in new_building_types:
        type_demand.loc[
            type_demand["Building Archetype"] == new_building, "Size"
        ] = new_building_sizes[i]
        i += 1

    # multiply material intensity by building size and drop size column
    for col in type_demand.columns.difference(["Building Archetype", "Size"]):
        type_demand[col] = type_demand[col] * type_demand["Size"]
    type_demand.drop(columns=["Size"], inplace=True)

    # sum material demand across building types and drop materials not relevant for selected building(s)
    new_bldg_demand = (
        type_demand.loc[:, type_demand.columns != "Building Archetype"]
        .sum(axis=0)
        .loc[lambda x: x != 0]
    )

    # if reusing materials, identify whether demolished buildings contain reusable materials
    if reused_materials:
        # identify materials that can be reused within demolished buildings
        reused_available = base_mat_demand[
            base_mat_demand["Building Archetype"].isin(old_building_types)
        ]

        # filter to materials elligible for reuse
        reused_available = reused_available[
            [
                "Building Archetype",
                "Carbon steel (rebar)",
                "Cold-formed, galvanized steel",
                "Hot-rolled, structural steel",
                "Cold-formed, structural steel",
                "Solid modular brick",
            ]
        ]

        # rename reused materials columns
        reused_available = reused_available.rename(
            columns=lambda c: c if c == "Building Archetype" else f"{c}_reused"
        )

        # add size column for demolished buildings
        i = 0
        for old_building in old_building_types:
            reused_available.loc[
                reused_available["Building Archetype"] == old_building, "Size"
            ] = old_building_sizes[i]
            i += 1

        # multiply material intensity by building size and drop size column
        for col in reused_available.columns.difference(["Building Archetype", "Size"]):
            reused_available[col] = reused_available[col] * reused_available["Size"]
        reused_available.drop(columns=["Size"], inplace=True)

        # sum material availability from demolished buildings
        old_bldg_supply = (
            reused_available.loc[:, reused_available.columns != "Building Archetype"]
            .sum(axis=0)
            .loc[lambda x: x != 0]
        )

        # add relevant reused materials into main dataframe
        new_bldg_demand = pd.concat([new_bldg_demand, old_bldg_supply])

        for col in [
            "Carbon steel (rebar)",
            "Cold-formed, galvanized steel",
            "Hot-rolled, structural steel",
            "Cold-formed, structural steel",
            "Solid modular brick",
        ]:
            # remove reused materials that are not needed for new building construction
            if col + "_reused" in new_bldg_demand.index:
                if col not in new_bldg_demand.index:
                    new_bldg_demand.drop(col + "_reused", inplace=True)
                # if reused material is needed for new building construction, correct amount of material used for new construction
                else:
                    if new_bldg_demand[col + "_reused"] > new_bldg_demand[col]:
                        new_bldg_demand[col + "_reused"] = new_bldg_demand[col]

    # construct path to cement mixture data, from "A Cradle-to-Gate Life Cycle Assessment of Ready-Mixed Concrete Manufactured by NRMCA Members – Version 3 "
    cement_mix_path = os.path.join(
        settings.BASE_DIR, "demand_supply_availability/static/raw_data/US concrete mixture data.xlsx"
    )
    
    # read cement mixture data
    cement_mix = pd.read_excel(
        cement_mix_path,
        sheet_name="Regional mixture designs",
        header=1,
    )
    cement_mix = cement_mix.iloc[0:7]

    # identify concrete mixture based on region; note, AK and HI not included
    if state in [
        "Connecticut",
        "Delaware",
        "Maine",
        "Maryland",
        "Massachusetts",
        "New Hampshire",
        "New Jersey",
        "New York",
        "Pennsylvania",
        "Rhode Island",
        "Vermont",
        "Virginia",
        "West Virginia",
    ]:
        region = "Eastern"
    elif state in ["Illinois", "Indiana", "Michigan", "Ohio", "Wisconsin"]:
        region = "Great Lakes Midwest"
    elif state in ["Iowa", "Minnesota", "Nebraska", "North Dakota", "South Dakota"]:
        region = "North Central"
    elif state in ["Idaho", "Montana", "Oregon", "Washington"]:
        region = "Pacific Northwest"
    elif state in ["Arizona", "California", "Nevada"]:
        region = "Pacific Southwest"
    elif state in ["Colorado", "New Mexico", "Utah", "Wyoming"]:
        region = "Rocky Mountains"
    elif state in [
        "Alabama",
        "Florida",
        "Georgia",
        "Kentucky",
        "Mississippi",
        "North Carolina",
        "South Carolina",
        "Tennessee",
    ]:
        region = "South Eastern"
    elif state in [
        "Arkansas",
        "Kansas",
        "Louisiana",
        "Missouri",
        "Oklahoma",
        "Texas",
    ]:
        region = "South Central"
    else:
        raise ValueError(
            f"State {state} not recognized. Please enter a valid US state."
        )

    # create seperate dataframe for demand of concrete components based on region
    concrete_demand = cement_mix[["Constituents per kg PC", region]]

    # convert from kg cement constituent per kg cement to lb per lb
    concrete_demand[region] = concrete_demand[region] * 2.20462

    # multiply by total concrete demand to obtain total amount of raw materials needed for new construction
    concrete_demand[region] = (
        concrete_demand[region] * new_bldg_demand["Cast-in-place concrete"]
    )

    # rename columns to match formatting of new_bldg_demand
    concrete_demand.rename(
        columns={
            "Constituents per kg PC": "Material",
            region: "Baseline Demand (lbs)",
        },
        inplace=True,
    )

    # reformat new_bldg_demand as a dataframe for ease of plotting
    new_bldg_demand = pd.DataFrame(new_bldg_demand)
    new_bldg_demand["Material"] = new_bldg_demand.index.values
    new_bldg_demand.reset_index(drop=True, inplace=True)
    new_bldg_demand.rename(columns={0: "Baseline Demand (lbs)"}, inplace=True)

    # add column for structural versus non-structural material classification
    classification_map = {
        m: "Structural"
        for m in [
            "Cast-in-place concrete",
            "Carbon steel (rebar)",
            "Carbon steel (rebar)_reused",
            "Plywood",
            "Cold-formed, galvanized steel",
            "Cold-formed, galvanized steel_reused",
            "Hot-rolled, structural steel",
            "Hot-rolled, structural steel_reused",
            "Cold-formed, structural steel",
            "Cold-formed, structural steel_reused",
            "Concrete masonry unit",
            "Solid modular brick",
            "Solid modular brick_reused",
            "Type S mortar",
        ]
    }
    classification_map.update(
        {
            m: "Non-structural"
            for m in [
                "Oriented strand board",
                "Softwood",
                "Stucco",
                "Polyisocyanurate foam board",
                "Expanded polystyrene foam",
                "Glass mat gypsum board",
                "Aluminum",
                "Aluminum, 20% recycled content",
                "#15 felt",
                "#30 felt",
                "Transite",
                "Thermoplastic olefin",
                "Polyvinyl butyral interlayer film",
                "Asphalt built-up roof membrane",
                "Granulated modified bitumen cap sheet",
                "Asphalt shingles",
                "Wood cladding (softwood)",
                "Clay tiles",
                "Modified bitumen membrane",
                "Laminated glass",
            ]
        }
    )
    new_bldg_demand["Material classification"] = new_bldg_demand["Material"].map(
        classification_map
    )

    # set path for processed_data 
    processed_data_path = os.path.join(settings.BASE_DIR, "demand_supply_availability/static/processed_data")
    os.makedirs(processed_data_path, exist_ok=True)

    # export to JSON format for visualization in webtool
    new_bldg_demand.to_json(
        os.path.join(processed_data_path, "new_bldg_demand.json"), orient="records"
    )
    concrete_demand.to_json(
        os.path.join(processed_data_path, "concrete_demand.json"), orient="records"
    )

    print("new_bldg_demand.json updated.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Estimate baseline building material demand."
    )
    parser.add_argument(
        "--new_types", nargs="+", required=True, help="New building type(s)"
    )
    parser.add_argument(
        "--new_sizes",
        nargs="+",
        type=float,
        required=True,
        help="Size(s) for new building(s) (GSF)",
    )
    parser.add_argument(
        "--state", required=True, help="State for new construction (e.g., California)"
    )
    parser.add_argument(
        "--reuse",
        action="store_true",
        help="Reuse materials from demolished buildings?",
    )
    parser.add_argument(
        "--old_types",
        nargs="*",
        default=[],
        help="Optional demolished building type(s)",
    )
    parser.add_argument(
        "--old_sizes",
        nargs="*",
        type=float,
        default=[],
        help="Optional size(s) for demolished building(s) (GSF)",
    )

    args = parser.parse_args()

    # validate new building sizes match types
    if len(args.new_types) != len(args.new_sizes):
        raise ValueError(
            f"Number of new building sizes ({len(args.new_sizes)}) must match number of new building types ({len(args.new_types)})"
        )

    # validate old building sizes match types, only if --reuse is set and lists are provided
    if args.reuse:
        if len(args.old_types) != len(args.old_sizes):
            raise ValueError(
                f"Number of old building sizes ({len(args.old_sizes)}) must match number of old building types ({len(args.old_types)})"
            )

    est_base_demand(
        new_building_types=args.new_types,
        new_building_sizes=args.new_sizes,
        state=args.state,
        reused_materials=args.reuse,
        old_building_types=args.old_types,
        old_building_sizes=args.old_sizes,
    )

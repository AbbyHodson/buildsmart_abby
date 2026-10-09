# import necessary libraries
import pandas as pd
import os
from django.conf import settings
import argparse

# construct path to material cost by building archetype, as compiled by Josefine Olsson using RSMeans data
base_mat_cost_path = os.path.join(
    settings.BASE_DIR, "demand_supply_availability/static/raw_data/material_costs.xlsx"
)

# read in material cost by building archetype
base_mat_cost = pd.read_excel(base_mat_cost_path, sheet_name='Sheet2')

def est_base_cost(
    new_building_types,
    new_building_sizes,
    reused_materials,
    old_building_types=None,
    old_building_sizes=None,
):
    """
    Estimates 2026 material cost for buildings, with the option of using materials sourced from demolished buildings, and exports to a .JSON file for front-end visualization

    Args:
        new_building_types (list): archetype(s) of new building(s)
        new_building_sizes (list): size(s) of new building(s) (GSF)
        reused_materials (bool): whether reused materials should be included
        old_building_types (list, optional): archetype(s) of demolished building(s)
        old_building_sizes (list, optional): size(s) of demolished building(s) (GSF)

    """
    # identify material cost for selected building archetype
    type_cost = base_mat_cost[
        base_mat_cost["Building Archetype"].isin(new_building_types)
    ]

    # add size column for new buildings
    i = 0
    for new_building in new_building_types:
        type_cost.loc[
            type_cost["Building Archetype"] == new_building, "Size"
        ] = new_building_sizes[i]
        i += 1

    # multiply cost intensity by building size and drop size column
    for col in type_cost.columns.difference(["Building Archetype", "Size"]):
        type_cost[col] = type_cost[col] * type_cost["Size"]
    type_cost.drop(columns=["Size"], inplace=True)

    # sum material cost across building types and drop materials not relevant for selected building(s)
    new_bldg_cost = (
        type_cost.loc[:, type_cost.columns != "Building Archetype"]
        .sum(axis=0)
        .loc[lambda x: x != 0]
    )

    # if reusing materials, identify whether demolished buildings contain reusable materials
    if reused_materials:
        # identify materials that can be reused within demolished buildings
        reused_available = base_mat_cost[
            base_mat_cost["Building Archetype"].isin(old_building_types)
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

        # assume cost intensity of reused materials is zero
        for col in reused_available.columns.difference(["Building Archetype", "Size"]):
            reused_available[col] = 0 * reused_available["Size"]
        reused_available.drop(columns=["Size"], inplace=True)

        # sum material cost from demolished buildings
        old_bldg_cost = (
            reused_available.loc[:, reused_available.columns != "Building Archetype"]
            .sum(axis=0)
            .loc[lambda x: x != 0]
        )

        # add relevant reused materials into main dataframe
        new_bldg_cost = pd.concat([new_bldg_cost, old_bldg_cost])

        for col in [
            "Carbon steel (rebar)",
            "Cold-formed, galvanized steel",
            "Hot-rolled, structural steel",
            "Cold-formed, structural steel",
            "Solid modular brick",
        ]:
            # remove reused materials that are not needed for new building construction
            if col + "_reused" in new_bldg_cost.index:
                if col not in new_bldg_cost.index:
                    new_bldg_cost.drop(col + "_reused", inplace=True)
                # if reused material is needed for new building construction, correct amount of material used for new construction
                else:
                    if new_bldg_cost[col + "_reused"] > new_bldg_cost[col]:
                        new_bldg_cost[col + "_reused"] = new_bldg_cost[col]

    # reformat new_bldg_cost as a dataframe for ease of plotting
    new_bldg_cost = pd.DataFrame(new_bldg_cost)
    new_bldg_cost["Material"] = new_bldg_cost.index.values
    new_bldg_cost.reset_index(drop=True, inplace=True)
    new_bldg_cost.rename(columns={0: "Baseline Cost (2026 USD)"}, inplace=True)

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
    new_bldg_cost["Material classification"] = new_bldg_cost["Material"].map(
        classification_map
    )

    # set path for processed_data 
    processed_data_path = os.path.join(settings.BASE_DIR, "demand_supply_availability/static/processed_data")
    os.makedirs(processed_data_path, exist_ok=True)

    # export to JSON format for visualization in webtool
    new_bldg_cost.to_json(
        os.path.join(processed_data_path, "new_bldg_cost.json"), orient="records"
    )
    print("new_bldg_cost.json updated.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Estimate baseline building material cost."
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

    est_base_cost(
        new_building_types=args.new_types,
        new_building_sizes=args.new_sizes,
        reused_materials=args.reuse,
        old_building_types=args.old_types,
        old_building_sizes=args.old_sizes,
    )
#!/usr/bin/env python3
"""
Create Compressed CSV files for ingest into Neo4j

Relationships are generally are set to be bottom up, or detailed nodes toward more generic nodes;
For example concept relations are from bottom up. So "Tylenol" -contains-> "Acetimenophen". Same
for sematic type nodes, a "Mammal" -isa-> "Organism"

This script currently doesn't leverage relationships in the opposite direction since Neo4j can
search either direction anyway.
"""
import logging
import logging.config
from pathlib import Path
from typing import List, Optional

import pandas as pd
import yaml

from rxnorm import graph, rrf


class MissingDataException(ValueError):
    pass


def get_neo_rrf():
    return graph.NeoRRF(
        "bolt+ssc://127.0.0.1:7687",
        "neo4j",
        "neo4j",
    )


def check_missing_columns(required_cols: List, df: pd.DataFrame, df_name: str):
    missing = False
    for col in required_cols:
        if col not in df.columns:
            logger.error(f"Missing column: {col} in {df_name}.")
            missing = True
    if missing:
        raise MissingDataException("Required columns are missing.")


def create_rel_connections(neo_rrf: graph.NeoRRF, rel: pd.DataFrame):
    rxcui = "rxcui1"
    rela = "rela"
    rxaui = "rxaui1"

    cui_filter = ~rel["rela"].isna() & ~rel["rxcui1"].isna()
    rel_cui = rel[cui_filter]
    cui_check_list = [rxcui, rela]
    check_missing_columns(cui_check_list, rel_cui, "RXREL-CUI")

    aui_filter = ~rel["rela"].isna() & ~rel["rxaui1"].isna()
    rel_aui = rel[aui_filter]
    aui_check_list = [rxaui, rela]
    check_missing_columns(aui_check_list, rel_aui, df_name="RXREL-AUI")
    rel_aui = rel.loc[aui_filter, aui_check_list]

    neo_rrf.merge_rel_connections(rel_cui)


def create_rxcui_nodes(neo_rrf: graph.NeoRRF, conso: pd.DataFrame):
    tty = "tty"
    code = "code"
    rxcui = "rxcui"
    rxaui = "rxaui"
    col_check_list = [rxcui, rxaui, tty, code]
    check_missing_columns(col_check_list, conso, df_name="RXCONSO")

    columns_to_keep = col_check_list + ["brand", "generic", "str"]
    columns_to_keep = [
        column_name for column_name in columns_to_keep if column_name in conso.columns
    ]
    tty_keep = (
        conso[tty].str.startswith("SBD")
        | conso[tty].str.startswith("SCD")
        | conso[tty].isin(["BN", "IN"])
    )

    conso_rx = conso.loc[tty_keep, columns_to_keep]
    dedupe_conso_rx = conso_rx.drop_duplicates(subset=["rxcui", "tty"])
    logger.warning(
        f"Dropping any duplicate RXCUI values...dropped {len(conso_rx)-len(dedupe_conso_rx)}"
    )
    neo_rrf.create_conso_nodes_by_tty(dedupe_conso_rx)
    # neo_rrf.create_conso_nodes_by_tty(conso_rx)


def create_sty_nodes_and_relationships(sty: pd.DataFrame) -> Path:
    """
    Semantic type nodes include things like "animals", "vitamins", "Food", "Clinical Drug", "Organic Chemical", etc.
    These are structured in a tree / hierarchy A1.1 -> A1.1.2 -> A1.1.2.3 and so on.

    """
    sty_nodes = (
        sty.groupby("stn")[["tui", "sty"]]
        .value_counts()
        .rename("sty_count")
        .reset_index()
    ).copy()

    sty_nodes.rename(
        columns={
            "sty_count": "reference_count",
        },
        inplace=True,
    )
    semantic_types_nodes_path = Path("tui_semantic_types_nodes.csv")
    graph.save_node_csv_file(
        sty_nodes, filename=semantic_types_nodes_path, id_col="tui", node_label="STY"
    )


def create_ndc_nodes_and_relationships(sat: pd.DataFrame) -> List[Path]:
    """
    Creates paths from NDC nodes to RXCUI nodes.
    Returns list of files created.
    """
    files_written = []
    ndc = "ndc"
    rxcui = "rxcui"
    rxaui = "rxaui"
    col_check_list = [ndc, rxcui, rxaui]
    breakpoint()

    ndc_data = (
        sat[(sat["atn"] == "NDC") & (sat["suppress"] == "N") & (sat["sab"] == "RXNORM")]
        .rename(columns={"atv": ndc})
        .drop_duplicates(subset=ndc)
    )
    ndc_data[ndc] = ndc_data[ndc].apply(graph._standardize_ndc_11)

    # Make the CSV!
    ndc_node_path = Path("ndc_nodes.csv")
    node_path = graph.save_node_csv_file(
        ndc_data[[ndc, rxcui, rxaui, "brand"]].rename(
            columns={ndc: f"{ndc}:ID({ndc.upper()})"}
        ),
        filename=ndc_node_path,
        node_label=ndc,
    )

    if node_path.exists() and node_path == ndc_node_path:
        files_written.append(ndc_node_path)

    ndc_relationships_path = Path("ndc_cui_relations.csv")

    saved_path = graph.save_relationship_csv_file(
        ndc_data.loc[
            ndc_data["sab"] == "RXNORM", [ndc, rxaui, rxcui]
        ].drop_duplicates(),
        filename=ndc_relationships_path,
        start_col=ndc,
        start_label="NDC",
        end_col=rxcui,
        end_label="RXCUI",
        rela_type="aka",
    )

    if saved_path.exists() and saved_path == ndc_relationships_path:
        files_written.append(ndc_relationships_path)
        logger.info(
            f"NDC Nodes and RXCUI relationships files created with {len(ndc_data)} records"
        )

    return files_written


def create_relationship_map(rel, rela_type) -> pd.DataFrame:
    relation_cols = ["rxcui1", "rxaui1", "rxcui2", "rxaui2", "rela"]
    rel_map = (
        rel[(rel["rela"] == rela_type)][relation_cols]
        .rename(columns={"rela": ":TYPE"})
        .copy()
    )
    logger.info(
        f"Created relationship map data for {rela_type} with {len(rel_map)} records"
    )
    return rel_map


def process_generic_meds(scd, tradename_map, concept_brands):
    # Using left join since not all generic meds will have a brand name
    generic_meds = (
        scd.rename(columns={"str": "generic"})
        .merge(
            tradename_map,
            left_on="rxcui",
            right_on="rxcui2",
            how="left",
        )
        .merge(
            concept_brands,
            left_on="rxcui1",
            right_on="rxcui",
            how="left",
            suffixes=("", "_BN"),
        )
    )

    # Fill in blank names
    noname = generic_meds["brand"].isna()
    generic_meds.loc[noname, "brand"] = generic_meds.loc[noname, "generic"]

    # Remove duplicate RXCUI
    original_len = len(generic_meds)
    generic_dedupe = generic_meds.drop_duplicates(subset=["rxcui", "rxcui_BN"])
    generic_dupes = generic_dedupe.duplicated(subset="rxcui")
    generic_dedupe.loc[generic_dupes, "rxcui"] = generic_dedupe.loc[
        generic_dupes, "rxcui_BN"
    ]
    final_len = len(generic_dedupe)
    logger.warning(
        f"Dropped {original_len - final_len} records from the SCD data, still have {final_len} records."
    )

    logger.info("Generic meds data processed")
    return generic_dedupe


def read_and_feather_rxnorm_data(filepath, create_feather=True):
    """
    Goal is to read data from files saved locally.
    Uses feather files if they exist.
    Creates them if not and create_feather flag is set.
    """
    feather_path = filepath.with_suffix(".feather")
    if feather_path.exists():
        rxnorm_data = rrf.standardize_columns(pd.read_feather(feather_path))
    else:
        rxnorm_data = rrf.read_rrf_sty(filepath=filepath)
        if create_feather:
            rxnorm_data.to_feather(feather_path)
    return rxnorm_data


def rxnorm_only(rx_df):
    rx_filter = rx_df["sab"] == "RXNORM"
    logger.info(
        "Keeping only RXNORM values: "
        f"removed {sum(~rx_filter)} rows, "
        f"kept {sum(rx_filter)} records"
    )
    return rx_df[rx_filter]


def main(
    conso_filepath: Optional[Path] = None,
    rel_filepath: Optional[Path] = None,
    sat_filepath: Optional[Path] = None,
    skip: Optional[Path] = None,
    focus: Optional[Path] = None,
):
    """
    Main function that orchestrates filling the Neo4j DB with data from RxNorm files.

    Args:
        conso_filepath  Location for the RXCONSO.RRF(.gz) file
    """
    conso_filepath = Path("./") / "rrf" / "RXNCONSO.RRF.gz"
    rel_filepath = Path("./") / "rrf" / "RXNREL.RRF.gz"
    sat_filepath = Path("./") / "rrf" / "RXNSAT.RRF.gz"
    sty_filepath = Path("./") / "rrf" / "RXNSTY.RRF.gz"

    if not (
        conso_filepath.exists() and rel_filepath.exists() and sat_filepath.exists()
    ):
        raise ValueError("Missing RRF file(s).")

    neo_rrf = get_neo_rrf()

    sty = read_and_feather_rxnorm_data(sty_filepath)
    rel = read_and_feather_rxnorm_data(rel_filepath)
    sat = read_and_feather_rxnorm_data(sat_filepath)
    conso = read_and_feather_rxnorm_data(conso_filepath)

    # rel = rxnorm_only(rel)
    # sat = rxnorm_only(sat)

    rela_types = ["consists_of", "has_ingredient", "contains", "has_tradename"]
    relationship_maps = {}
    for rela_type in rela_types:
        rela_map = create_relationship_map(rel, rela_type=rela_type)
        relationship_maps[rela_type] = rela_map
    logger.info("Relationship mapping data created")

    # Bring ingredients and other types together based on brand vs generic
    # This makes it possible to track all generic meds while including related brand names as "the same"
    # while also keeping track of branded meds that have no generic alternative
    scd = group_nodes_by_tty(conso, tty_type="IN", semantic_type="SCD", group="generic")

    concept_brands = conso.rename(columns={"str": "brand"})[
        ["rxcui", "brand"]
    ].drop_duplicates(subset="rxcui")
    generic_meds = process_generic_meds(
        scd, relationship_maps["has_tradename"], concept_brands
    )

    sat = sat.merge(
        concept_brands,
        on="rxcui",
        how="left",
        suffixes=("", "_BN"),
    )
    # Create NDC to RxCUI first since that's the "entry" for claims look ups
    create_ndc_nodes_and_relationships(sat)
    logger.info(f"NDC nodes and relationships data ready, {len(sat)} records")

    # Create Semantic Type nodes
    create_sty_nodes_and_relationships(sty)
    logger.info("STY nodes and relationships data ready")

    create_rxcui_nodes(neo_rrf, generic_meds)
    logger.info("RXCUI TTY nodes and relationships data ready")

    # Seems like some brand name meds do not have a generic alternative. Need to keep those separately.
    sbd = group_nodes_by_tty(conso, tty_type="BN", semantic_type="SBD", group="brand")
    sbd_filter = (
        ~sbd["rxcui"].isin(generic_meds["rxcui"])
        # & ~sbd["rxcui"].isin(generic_meds["rxcui1"])
        # & ~sbd["rxcui"].isin(scd["rxcui"])
        & (sbd["sab"] == "RXNORM")
    )
    sbd_unique = sbd.loc[sbd_filter]

    logger.warning("No brand name file being made! It was causing duplicates.")
    create_rxcui_nodes(neo_rrf, sbd_unique)

    for rela_type, rel_map in relationship_maps.items():
        mapping_filter1 = rel_map["rxcui1"].isin(generic_meds["rxcui"]) | rel_map[
            "rxcui1"
        ].isin(sbd_unique["rxcui"])
        mapping_filter2 = rel_map["rxcui2"].isin(generic_meds["rxcui"]) | rel_map[
            "rxcui2"
        ].isin(generic_meds["rxcui"])
        mapping_diff = (~mapping_filter1) & (~mapping_filter2)
        if any(mapping_diff):
            logger.warning(
                f"Missing {mapping_diff.sum()} record matches for {rela_type}"
            )
        graph.save_relationship_csv_file(
            rel_map.loc[~mapping_diff, :],
            filename=Path(f"rel_{rela_type}.csv"),
            start_col="rxcui2",
            end_col="rxcui1",
        )
    breakpoint()


def group_nodes_by_tty(node_df, tty_type, semantic_type, group):
    """
    Creates nodes for each TTY
    """
    # Semantic Brand Drug
    tty_filter = node_df["tty"] == tty_type
    semantic_filter = node_df["tty"].str.startswith(semantic_type)
    return node_df[
        (tty_filter | semantic_filter) & (node_df["suppress"] == "N")
    ].rename(columns={"str": group})


if __name__ == "__main__":
    # TODO add argparse to get directory where files are saved,
    # then parse each file
    logging_config_file = "./configs/logging.yml"

    # Important to use "yaml.safe_load()" to prevent possible parsing error attacks
    with open(logging_config_file, "r") as f:
        logging_config = yaml.safe_load(f.read())["logging"]

    logging.config.dictConfig(logging_config)
    logger = logging.getLogger(
        __name__
    )  # This should match one of the "loggers" in the config file.
    """
    The special Python __name__ variable will evaluate
    to the module name when code is imported, or to "__main__"
    when running a script directly.
    """

    log_filename = logging_config["handlers"]["file"]["filename"]
    logger.info(f"Logging here: {log_filename}")
    main()

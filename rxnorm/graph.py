import copy
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

import neo4j

logger = logging.getLogger(__name__)


class RRFNode:
    def __init(self, labels: List, properties: Dict):
        self.labels = labels
        self.properties = properties


class NeoRRF:
    driver = None

    def __init__(self, uri, user, password, run_db_test=True):
        self.driver = neo4j.GraphDatabase.driver(uri, auth=(user, password))
        if run_db_test:
            try:
                self.driver.verify_connectivity()
            except Exception as de:
                # raise neo4j.exceptions.DatabaseUnavailable(
                #     "Could not connect to the DB."
                # ) from de
                echo "Not connected to DB"
                pass

    def close(self):
        # Don't forget to close the driver connection when you are finished with it
        self.driver.close()

    #  def merge_rel_connections(self, nodes_df, db_name="neo4j"):
    #      """
    #      Thread safe. Creates a session and uses Neo4j MERGE to create nodes for RXCUI
    #      that are related to RXREL RXAUI values.
    #      """
    #      with self.driver.session(database=db_name) as session:
    #          for _, node in nodes_df.iterrows():
    #              node_type = "rxcui"
    #              if not node["rxcui1"]:
    #                  node_type = "rxaui"
    #              n1 = f"{node_type}1"
    #              n2 = f"{node_type}2"

    #              query_n1 = f'(n1: RXCUI {{ {node_type.lower()}:"{node[n1]}" }})'
    #              query_n2 = f'(n2: RXCUI {{ {node_type.lower()}:"{node[n2]}" }})'
    #              query_r = node["rela"]
    #              query = (
    #                  f"MATCH {query_n1} "
    #                  f"MATCH {query_n2} "
    #                  "WITH n1, n2 "
    #                  f"WHERE not (n2)-[]->(n1) "
    #                  f"MERGE (n1)-[:{query_r}]->(n2)"
    #              )
    #              session.execute_write(
    #                  lambda tx: tx.run(
    #                      query,
    #                  )
    #              )

    def create_conso_nodes_by_tty(
        self, node_df, out_dir=Path("./neo4j_import"), compress=False
    ):
        """
        Thread safe. Creates a session and uses Neo4j MERGE to create nodes for RXCUI
        that are related to RXSAT NDC values.
        """
        rxaui = "rxaui"
        rxcui = "rxcui"
        node_lower = node_df.copy()
        for label in node_lower["tty"].unique():
            nodes_by_label = node_lower[node_lower["tty"] == label]
            # Order of the labels matters. First one is the ID
            escaped_label = self._standardize_node_label_list([rxcui, rxaui, label])
            if "str" in nodes_by_label.columns:
                nodes_by_label = nodes_by_label.rename(columns={"str": "name"})

            nodes_filename = Path(f"rxcui_{label}_nodes.csv")
            save_node_csv_file(
                nodes_by_label, nodes_filename, id_col=rxcui, node_label=escaped_label
            )

    # def merge_ndc_cui_relationship(self, node_df, relation, db_name="neo4j"):
    #     """
    #     Thread safe. Creates a session and uses Neo4j MERGE to create nodes for NDC nodes
    #     that are related to RxCUI values.
    #     """
    #     ndc = "ndc"
    #     rxcui = "rxcui"
    #     rxaui = "rxaui"
    #     with self.driver.session(database=db_name) as session:
    #         for idx, node in node_df.iterrows():
    #             node1 = {
    #                 "labels": [ndc],
    #                 "properties": {
    #                     "ndc": node[ndc],
    #                 },
    #             }
    #             node2 = {
    #                 "labels": [rxcui],
    #                 "properties": {
    #                     "rxcui": node[rxcui],
    #                     rxaui.lower(): node[rxaui],
    #                 },
    #             }
    #             self._merge_and_return_relationship_single(
    #                 session, node1, node2, relation
    #             )

    @staticmethod
    def _standardize_ndc_11(ndc: str) -> str:
        return re.sub(r"[-_+\(\) ]", "", ndc).zfill(11)

    @staticmethod
    def _standardize_node_label_list(labels: List) -> List:
        return [
            label.upper().replace("\\u0060", "`").replace("`", "``") for label in labels
        ]

    @staticmethod
    def _standardize_rel_label(labels: List) -> List:
        return [label.lower() for label in labels]

    def _set_up_path_merge_queries(self, node1, node2, relation):
        """
        Creates the parametrized query for Cypher
        """
        labels = "labels"
        properties = "properties"
        node1_label = self._standardize_node_label(node1[labels])
        node2_label = self._standardize_node_label(node2[labels])

        if not isinstance(node1[properties], dict) or not isinstance(
            node2[properties], dict
        ):
            raise ValueError("Node properties must be provided as a dictionary")

        node1_properties = ",".join(
            [f"{key}: $node1_{key}" for key in node1[properties]]
        )
        node2_properties = ",".join(
            [f"{key}: $node2_{key}" for key in node2[properties]]
        )
        node1_merge = f"MERGE (n1:{':'.join(node1_label)} {{ {node1_properties} }})"
        node2_merge = f"MERGE (n2:{':'.join(node2_label)} {{ {node2_properties} }})"
        relation_merge = f"MERGE (n1)-[:{relation}]->(n2) " "RETURN n1, n2"
        return " ".join([node1_merge, node2_merge, relation_merge])

    def _merge_and_return_relationship_single(self, session, node1, node2, relation):
        properties = "properties"

        # Parameters inserted by Cypher
        property_parameters = {
            f"node1_{key}": value for key, value in node1[properties].items()
        } | {f"node2_{key}": value for key, value in node2[properties].items()}
        query = self._set_up_path_merge_queries(node1, node2, relation)

        return session.run(
            query,
            **property_parameters,
        )


def save_node_csv_file(
    df: pd.DataFrame,
    filename: Path,
    id_col: Optional[str] = None,
    node_label: Optional[str] = None,
    compress=False,
) -> Path:
    """
    Helps to make sure names and column usage are standardized to fit the Neo4j CSV format guidance.
    """
    save_df = df.copy()
    filename = Path(filename)
    label_str = ":LABEL"

    if id_col and id_col in save_df.columns:
        new_id_col = id_col
        if isinstance(node_label, str):
            new_id_col = f"{id_col}:ID({node_label.upper()})"
        else:
            new_id_col = f"{id_col}:ID({node_label[0].upper()})"
        save_df.rename(columns={id_col: new_id_col}, inplace=True)

    # Ensure ID is unique!!!!
    original_len = len(save_df)
    for col_name in save_df.columns:
        if ":ID" in col_name:
            save_df.drop_duplicates(subset=col_name, inplace=True)
    new_len = len(save_df)
    len_change = original_len - new_len
    if len_change != 0:
        logger.warning(
            f"Dropped {len_change} rows from data going into {filename}. {new_len} records left."
        )

    if all(label_str not in column_name for column_name in save_df.columns):
        if node_label:
            if isinstance(node_label, list):
                node_label = ";".join(node_label)
            save_df[label_str] = node_label.upper()
        else:
            errors.append("No label for the nodes provided")

    compression = None
    if compress:
        compression = "gzip"
        filename = Path(f"{str(filename)}.gz")
    save_df.dropna(how="all", axis=1).drop_duplicates().to_csv(
        filename, compression=compression, index=False
    )

    if filename.exists():
        logger.info(f"Saved {filename}.")
        return filename


def save_relationship_csv_file(
    df: pd.DataFrame,
    filename: Path,
    start_col: Optional[str] = None,
    start_label: Optional[str] = "RXCUI",
    end_col: Optional[str] = None,
    end_label: Optional[str] = "RXCUI",
    rela_type: Optional[str] = None,
    compress: Optional[bool] = False,
) -> Path:
    """
    Helps to make sure names and column usage are standardized to fit the Neo4j CSV format guidance.
    """
    save_df = df.copy()
    start_id = ":START_ID"
    end_id = ":END_ID"
    type_str = ":TYPE"

    _standardize_rel_label(save_df)
    if start_col and start_col in save_df.columns:
        new_start_col = f"{start_col}:START_ID({start_label.upper()})"
        save_df.rename(
            columns={start_col: new_start_col},
            inplace=True,
        )

    if end_col and end_col in save_df.columns:
        new_end_col = f"{end_col}:END_ID({end_label.upper()})"
        save_df.rename(columns={end_col: new_end_col}, inplace=True)

    errors = []
    if all(start_id not in column_name for column_name in save_df.columns):
        errors.append("No starting Node ID provided")

    if all(end_id not in column_name for column_name in save_df.columns):
        errors.append("No ending Node ID provided")

    if errors:
        msg = ""
        for error in errors:
            logger.error(error)
            msg = msg + " " + error

        raise ValueError(msg.strip())

    if all(type_str not in column_name for column_name in save_df.columns):
        if rela_type:
            save_df[type_str] = rela_type.lower().strip()
        else:
            errors.append("No type for the relationships provided")

    compression = None
    if compress:
        compression = "gzip"
        filename = Path(f"{str(filename)}.gz")

    save_df.dropna(how="all", axis=1).drop_duplicates().to_csv(
        filename, compression=compression, index=False
    )

    if filename.exists():
        logger.info(f"Saved {filename}.")
        return filename


def _standardize_ndc_11(ndc: str) -> str:
    return re.sub(r"[-_+\(\) ]", "", ndc).zfill(11)[:11]


def _standardize_node_label_list(labels: List) -> List:
    return ":".join(
        [label.upper().replace("\\u0060", "`").replace("`", "``") for label in labels]
    )


def _standardize_rel_label(df: pd.DataFrame) -> None:
    for col_name in df.columns:
        df.rename(columns={col_name: col_name.lower().strip().replace("`", "``")})

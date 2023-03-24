import gzip as gz
import warnings
from pathlib import Path
from typing import List

import pandas as pd


def std_col_ref(text_series: pd.Series) -> pd.Series:
    """Applies text standardization techniques so that labels / column names become pre predictable.
    The standardized text makes matching column names dynamically much simpler.
    Transformations include, removing most punctuation, replacing whitespace, and lowercase.

    NOTE - The order of these transformations is important. For example, if spaces are converted
    to underscore after double underscores (_ _) are removed, then it will potentially create
    new columns that have double underscores in the name.

    Args:
        text_series: Pandas Series with the column names or labels to standardize.

    Returns:
        new_text: Transformed pandas series with the standardization applied."""
    new_text = text_series.str.strip()
    new_text = new_text.str.replace(r"\s+", "_", regex=True)
    new_text = new_text.str.replace("[-]+", "_", regex=True)
    new_text = new_text.str.replace("/", "_", regex=False)
    new_text = new_text.str.replace("\\", "_", regex=False)
    new_text = new_text.str.replace(".", "_", regex=False)
    new_text = new_text.str.replace("#", "num", regex=False)
    new_text = new_text.str.replace("(", "", regex=False)
    new_text = new_text.str.replace(")", "", regex=False)
    new_text = new_text.str.replace("[!@#$%^&*]+", "", regex=True)
    new_text = new_text.str.replace("[_]+", "_", regex=True)
    new_text = new_text.str.lower()
    return new_text


def standardize_columns(
    df: pd.DataFrame, drop_na_cols: bool = False, inplace: bool = True
) -> pd.DataFrame:
    """Standardizes column names and references:

    Args:
        df: The dataframe which will have its columns standardized
        drop_na_cols: Bool switch to drop columns that are entirely empty (NA)
        inplace: Bool switch to determine whether the original dataframe is modified or
                 a new one is created

    Returns:
        pd.DataFrame: The dataframe with the columns standardized
    """
    if not inplace:
        df = copy.deepcopy(df)
    the_columns = df.columns
    the_columns = std_col_ref(the_columns)
    df.columns = the_columns
    if drop_na_cols:
        df = df.dropna(axis=1, how="all")
    return df


def _rrf_to_df(rrf_path: Path, headers):
    df = pd.read_csv(
        rrf_path,
        names=headers,
        delimiter="|",
        dtype="string",
        escapechar="ä",
        index_col=False,
    ).dropna(how="all", axis=1)
    return standardize_columns(df)


def _read_rrf(filepath: Path, headers: List):
    if filepath.suffix != ".gz":
        return _rrf_to_df(filepath, headers)
    with gz.open(filepath, "rt") as rrf_file:
        return _rrf_to_df(rrf_file, headers)


def read_rrf_conso(filepath: Path = Path("RXNCONSO.RRF.gz")):
    headers = [
        "rxcui",
        "lat",
        "ts",
        "lui",
        "stt",
        "sui",
        "ispref",
        "rxaui",
        "saui",
        "scui",
        "sdui",
        "sab",
        "tty",
        "code",
        "str",
        "srl",
        "suppress",
        "cvf",
    ]

    return _read_rrf(filepath, headers)


def read_rrf_rel(filepath: Path = Path("RXNREL.RRF.gz")):
    headers = [
        "rxcui1",
        "rxaui1",
        "stype1",
        "rel",
        "rxcui2",
        "rxaui2",
        "stype2",
        "rela",
        "rui",
        "srui",
        "sab",
        "sl",
        "dir",
        "rg",
        "suppress",
        "cvf",
    ]

    return _read_rrf(filepath, headers)


def read_rrf_sat(filepath: Path = Path("RXNSAT.RRF.gz")):
    headers = [
        "rxcui",
        "lui",
        "sui",
        "rxaui",
        "stype",
        "code",
        "atui",
        "satui",
        "atn",
        "sab",
        "atv",
        "suppress",
        "cvf",
    ]

    return _read_rrf(filepath, headers)


def read_rrf_sty(filepath: Path = Path("RXNSTY.RRF.gz")):
    headers = [
        "rxcui",
        "tui",
        "stn",
        "sty",
        "atui",
        "cvf",
    ]
    return _read_rrf(filepath, headers)

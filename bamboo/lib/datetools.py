from calendar import timegm
import copy
from datetime import datetime

from dateutil.parser import parse as date_parse
import numpy as np
from pandas import Series

from bamboo.lib.schema_builder import DATETIME, SIMPLETYPE
from bamboo.lib.utils import is_float_nan


def recognize_dates(dframe):
    """Convert data columns to datetimes.

    Check if object columns in a dataframe can be parsed as dates.
    If yes, rewrite column with values parsed as dates.

    Args:

    - dframe: The DataFrame to convert columns in.

    Returns:
        A DataFrame with column values convert to datetime types.
    """
    new_dframe = copy.deepcopy(dframe)
    for idx, dtype in enumerate(dframe.dtypes):
        if dtype.type == np.object_:
            _convert_column_to_date(new_dframe, dframe.columns[idx])
    return new_dframe


def recognize_dates_from_schema(schema, dframe):
    """Convert columes to datetime if column in *schema* is of type datetime.

    Args:

    - schema: Schema to define columns of type datetime.
    - dframe: The DataFrame to convert columns in.

    Returns:
        A DataFrame with column values convert to datetime types.
    """
    new_dframe = copy.deepcopy(dframe)
    dframe_columns = dframe.columns.tolist()
    for column, column_schema in schema.items():
        if column in dframe_columns and\
                column_schema[SIMPLETYPE] == DATETIME:
            _convert_column_to_date(new_dframe, column)
    return new_dframe


def _is_potential_date(value):
    return not (is_float_nan(value) or isinstance(value, bool))


def _convert_column_to_date(dframe, column):
    """Inline conversion of column in dframe to date type."""
    try:
        new_column = Series([
            date_parse(field) if _is_potential_date(field) else field for
            field in dframe[column].tolist()])
        dframe[column] = new_column
    except ValueError:
        # it is not a correctly formatted date
        pass
    except OverflowError:
        # it is a number that is too large to be a date
        pass


def parse_str_to_unix_time(value):
    return parse_date_to_unix_time(date_parse(value))


def parse_date_to_unix_time(date):
    return timegm(date.utctimetuple())


def col_is_date_simpletype(column_schema):
    return column_schema[SIMPLETYPE] == DATETIME


def parse_timestamp_query(query, schema):
    """Interpret date column queries as JSON."""
    if query != {}:
        datetime_columns = [
            column for (column, schema) in
            schema.items() if
            schema[SIMPLETYPE] == DATETIME and column in query.keys()]
        for date_column in datetime_columns:
            query[date_column] = dict([(
                key,
                datetime.fromtimestamp(int(value))) for (key, value) in
                query[date_column].items()])
    return query
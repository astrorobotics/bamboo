import simplejson as json

from bson import json_util
from pandas import Series

from bamboo.core.frame import DATASET_OBSERVATION_ID
from bamboo.lib.datetools import parse_timestamp_query
from bamboo.lib.jsontools import JSONError
from bamboo.lib.utils import call_async
from bamboo.models.abstract_model import AbstractModel


class Observation(AbstractModel):

    __collectionname__ = 'observations'

    @classmethod
    def delete_all(cls, dataset, query={}):
        """Delete the observations for *dataset*.

        Args:

        - dataset: The dataset to delete observations for.
        - query: An optional query to restrict deletion.

        """
        query.update({
            DATASET_OBSERVATION_ID: dataset.dataset_observation_id
        })
        cls.collection.remove(query, safe=True)

    @classmethod
    def find(cls, dataset, query=None, select=None, limit=0, order_by=None,
             as_cursor=False):
        """Return observation rows matching parameters.

        Args:

        - dataset: Dataset to return rows for.
        - query: Optional query to restrict matching rows to.
        - select: Optional select to limit returned values.
        - limit: Limit on the number of returned rows.
        - order_by: Order parameter for rows.

        Returns:
            A list of dictionaries matching the passed in *query* and other
            parameters.

        Raises:
            JSONError: An error is the query could not be parsed.
        """
        try:
            query = (query and json.loads(
                query, object_hook=json_util.object_hook)) or {}

            query = parse_timestamp_query(query, dataset.schema)
        except ValueError, err:
            raise JSONError('cannot decode query: %s' % err.__str__())

        if select:
            try:
                select = json.loads(select, object_hook=json_util.object_hook)
            except ValueError, err:
                raise JSONError('cannot decode select: %s' % err.__str__())

        query[DATASET_OBSERVATION_ID] = dataset.dataset_observation_id
        return super(cls, cls).find(
            query, select, as_dict=True, limit=limit, order_by=order_by,
            as_cursor=as_cursor)

    def save(self, dframe, dataset):
        """Save data in *dframe* with the *dataset*.

        Encode *dframe* for MongoDB, and add fields to identify it with the
        passed in *dataset*. All column names in *dframe* are converted to
        slugs using the dataset's schema.  The dataset is update to store the
        size of the stored data. A background task to cache a summary of the
        dataset is launched.

        Args:

        - dframe: The DataFrame (or BambooFrame) to store.
        - dataset: The dataset to store the dframe in.

        """
        # build schema for the dataset after having read it from file.
        if not dataset.SCHEMA in dataset.record:
            dataset.build_schema(dframe)

        # save the data, if there is any
        num_columns = len(dataset.record[dataset.SCHEMA].keys())
        num_rows = 0
        if dframe is not None:
            labels_to_slugs = dataset.build_labels_to_slugs()

            # if column name is not in map assume it is already slugified
            # (i.e. NOT a label)
            dframe = dframe.rename(columns=dict([
                (column, labels_to_slugs.get(column, column)) for column in
                dframe.columns.tolist()]))

            id_column = Series([dataset.dataset_observation_id] * len(dframe))
            id_column.name = DATASET_OBSERVATION_ID
            dframe = dframe.join(id_column)

            self.batch_save(dframe)
            num_rows = len(dframe)

        # add metadata to dataset, discount ID column
        dataset.update({
            dataset.NUM_COLUMNS: num_columns,
            dataset.NUM_ROWS: num_rows,
            dataset.STATE: self.STATE_READY,
        })

        call_async(dataset.summarize, dataset)
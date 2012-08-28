import json

from bson import json_util

from config.db import Database
from lib.constants import DATASET_OBSERVATION_ID, DB_BATCH_SIZE, SCHEMA
from lib.exceptions import JSONError
from lib.mongo import mongo_to_df
from lib.utils import build_labels_to_slugs, slugify_columns
from models.abstract_model import AbstractModel
from models.dataset import Dataset


class Observation(AbstractModel):

    __collectionname__ = 'observations'

    @classmethod
    def delete(cls, dataset):
        """
        Delete the observations for *dataset*.
        """
        cls.collection.remove({
            DATASET_OBSERVATION_ID: dataset[DATASET_OBSERVATION_ID]
        })

    @classmethod
    def find(cls, dataset, query='{}', select=None, as_df=False):
        """
        Try to parse query if exists, then get all rows for ID matching query,
        or if no query all.  Decode rows from mongo and return.
        """
        if query:
            try:
                query = json.loads(query, object_hook=json_util.object_hook)
            except ValueError, e:
                raise JSONError('cannot decode query: %s' % e.__str__())

        if select:
            try:
                select = json.loads(select, object_hook=json_util.object_hook)
            except ValueError, e:
                raise JSONError('cannot decode select: %s' % e.__str__())

        query[DATASET_OBSERVATION_ID] = dataset[DATASET_OBSERVATION_ID]
        cursor = cls.collection.find(query, select)

        if as_df:
            return mongo_to_df(cursor)
        return cursor

    @classmethod
    def save(cls, dframe, dataset):
        """
        Convert *dframe* to mongo format, iterate through rows adding ids for
        *dataset*, insert in chuncks of size *DB_BATCH_SIZE*.
        """
        # build schema for the dataset after having read it from file.
        if not SCHEMA in dataset:
            Dataset.build_schema(dataset, dframe.dtypes)

        # add metadata to file
        dataset_observation_id = dataset[DATASET_OBSERVATION_ID]
        rows = []

        labels_to_slugs = build_labels_to_slugs(dataset)

        # if column name is not in map assume it is already slugified
        # (i.e. NOT a label)
        dframe.columns = [labels_to_slugs.get(column, column) for column in
                          dframe.columns.tolist()]

        for row_index, row in dframe.iterrows():
            row = row.to_dict()
            row[DATASET_OBSERVATION_ID] = dataset_observation_id
            rows.append(row)
            if len(rows) > DB_BATCH_SIZE:
                # insert data into collection
                cls.collection.insert(rows, safe=True)
                rows = []

        if len(rows):
            cls.collection.insert(rows, safe=True)

    @classmethod
    def update(cls, dframe, dataset):
        """
        Update *dataset* by overwriting all observations with the given
        *dframe*.
        """
        previous_dtypes = cls.find(dataset, as_df=True).dtypes.to_dict()
        new_dtypes = dframe.dtypes.to_dict().items()
        cols_to_add = dict([(name, dtype) for name, dtype in
                            new_dtypes if name not in previous_dtypes])
        Dataset.update_schema(dataset, cols_to_add)
        cls.delete(dataset)
        cls.save(dframe, dataset)
        return cls.find(dataset, as_df=True)

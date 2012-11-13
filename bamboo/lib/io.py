import simplejson as json
import os
import tempfile

from celery.task import task
from pandas import read_csv

from bamboo.lib.datetools import recognize_dates
from bamboo.lib.utils import call_async
from bamboo.models.dataset import Dataset


@task
def import_dataset(dataset, dframe=None, filepath_or_buffer=None,
                   delete=False):
    """For reading a URL and saving the corresponding dataset."""
    if filepath_or_buffer:
        dframe = recognize_dates(read_csv(filepath_or_buffer))
    if delete:
        os.unlink(filepath_or_buffer)
    dataset.save_observations(dframe)


def create_dataset_from_url(url, allow_local_file=False):
    """Load a URL, read from a CSV, create a dataset and return the unique ID.

    Args:

    - url: URL to load file from.
    - allow_local_file: Allow URL to refer to a local file.

    Raises:
        IOError: For an unreadable file or a bad URL.

    Returns:
        The created dataset.
    """
    if not allow_local_file and isinstance(url, basestring)\
            and url[0:4] == 'file':
        raise IOError

    dataset = Dataset()
    dataset.save()
    call_async(import_dataset, dataset, filepath_or_buffer=url)

    return dataset


def create_dataset_from_csv(csv_file):
    """Create a dataset from a CSV file.

    Args:

    - csv_file: The CSV File to create a dataset from.

    Returns:
        The created dataset.
    """
    # need to write out to a named tempfile in order
    # to get a handle for pandas *read_csv* function
    tmpfile = tempfile.NamedTemporaryFile(delete=False)
    tmpfile.write(csv_file.file.read())

    # pandas needs a closed file for *read_csv*
    tmpfile.close()

    dataset = Dataset()
    dataset.save()

    call_async(import_dataset, dataset, filepath_or_buffer=tmpfile.name,
               delete=True)

    return dataset


def create_dataset_from_schema(schema):
    """Create a dataset from a SDF schema file (JSON).

    Args:

    - schema: The SDF (JSON) file to create a dataset from.

    Returns:
        The created dataset.
    """
    schema = json.loads(schema.file.read())

    dataset = Dataset()
    dataset.save()
    dataset.set_schema(schema)

    call_async(import_dataset, dataset)

    return dataset
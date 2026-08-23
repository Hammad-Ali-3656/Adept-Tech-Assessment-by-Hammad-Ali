import pytest

from src.data_prep import load_clean
from src.model import ChurnModel


@pytest.fixture(scope="session")
def df():
    return load_clean()


@pytest.fixture(scope="session")
def model():
    return ChurnModel.load()

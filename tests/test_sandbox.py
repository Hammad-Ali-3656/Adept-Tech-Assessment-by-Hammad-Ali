import pytest

from src.agent import sandbox


def run(code, df):
    return sandbox.run(code, df)


def test_basic_expression(df):
    out = run("df['Churn'].value_counts()", df)
    assert out["ok"] and "5174" in out["output"]


def test_result_variable_and_print(df):
    out = run("result = len(df)\nprint('rows', result)", df)
    assert out["ok"] and "7043" in out["output"]


@pytest.mark.parametrize("bad", [
    "import os",
    "__import__('os')",
    "open('/etc/passwd')",
    "df.to_csv('/tmp/x.csv')",
    "pd.read_csv('/etc/passwd')",
    "().__class__.__mro__",
    "eval('1+1')",
    "exec('x=1')",
    "getattr(df, 'to_csv')",
    "globals()",
])
def test_escapes_blocked(bad, df):
    out = run(bad, df)
    assert not out["ok"]
    assert "sandbox" in out["error"] or "blocked" in out["error"]


def test_timeout(df):
    out = sandbox.run("x = 0\nfor i in range(10**10):\n    x += 1", df, timeout=1.5)
    assert not out["ok"] and "exceeded" in out["error"]


def test_runtime_error_returned_not_raised(df):
    out = run("df['NoSuchColumn'].mean()", df)
    assert not out["ok"] and "KeyError" in out["error"]


def test_mutation_does_not_leak(df):
    n = len(df)
    run("df.drop(df.index, inplace=True)", df)
    assert len(df) == n  # sandbox works on a copy

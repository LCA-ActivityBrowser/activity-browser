import sqlite3
import pandas as pd
import pickle
import sys

def load(fp: str, database_name: str, fields: list[str]):
    con = sqlite3.connect(fp)
    sql = f"SELECT data FROM activitydataset WHERE database = '{database_name}'"
    raw_df = pd.read_sql(sql, con)
    con.close()

    df = pd.DataFrame([pickle.loads(x) for x in raw_df["data"]])
    if df.empty:
        return df

    df["key"] = list(zip(df["database"], df["code"]))
    df.index = pd.MultiIndex.from_tuples(df["key"], names=["database", "code"])
    df = df.reindex(columns=fields)[fields]
    return df

if __name__ == '__main__':
    filepath = sys.argv[1]
    database_name = sys.argv[2]
    columns = sys.argv[3:]
    df = load(filepath, database_name, columns)

    sys.stdout.buffer.write(pickle.dumps(df))

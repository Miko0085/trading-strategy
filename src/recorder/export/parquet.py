from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


def write_parquet(rows, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(list(rows)), path)


def export_sqlite(store, directory, tables):
    destination = Path(directory)
    destination.mkdir(parents=True, exist_ok=True)
    paths = []
    for table in tables:
        if not table.replace("_", "").isalnum():
            raise ValueError("invalid table")
        columns = store.db.execute(f"PRAGMA table_info({table})").fetchall()
        schema = pa.schema(
            [
                (
                    r[1],
                    pa.int64()
                    if "INT" in r[2].upper()
                    else pa.float64()
                    if "REAL" in r[2].upper()
                    else pa.string(),
                )
                for r in columns
            ]
        )
        path = destination / f"{table}.parquet"
        query = store.db.execute(f"SELECT * FROM {table}")
        with pq.ParquetWriter(path, schema) as writer:
            while rows := query.fetchmany(10000):
                writer.write_table(pa.Table.from_pylist([dict(r) for r in rows], schema=schema))
        paths.append(path)
    return paths

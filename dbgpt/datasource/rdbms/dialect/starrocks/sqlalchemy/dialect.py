"""StarRocks dialect for SQLAlchemy."""

# Copyright 2021-present StarRocks, Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https:#www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import logging
from typing import Any, Dict, List, Optional, cast

from sqlalchemy import exc, log, text
from sqlalchemy.dialects.mysql.pymysql import MySQLDialect_pymysql
from sqlalchemy.engine import Connection

from dbgpt.datasource.rdbms.dialect.starrocks.sqlalchemy import datatype

logger = logging.getLogger(__name__)


@log.class_logger
class StarRocksDialect(MySQLDialect_pymysql):  # type: ignore
    """StarRocks dialect for SQLAlchemy."""

    # Caching
    # Warnings are generated by SQLAlchmey if this flag is not explicitly set
    # and tests are needed before being enabled
    supports_statement_cache = False

    name = "starrocks"

    def __init__(self, *args, **kw):
        """Create a new StarRocks dialect."""
        super(StarRocksDialect, self).__init__(*args, **kw)

    def has_table(self, connection, table_name, schema: Optional[str] = None, **kw):
        """Return True if the given table is present in the database."""
        self._ensure_has_table_connection(connection)

        if schema is None:
            schema = self.default_schema_name

        assert schema is not None

        quote = self.identifier_preparer.quote_identifier
        full_name = quote(table_name)
        if schema:
            full_name = "{}.{}".format(quote(schema), full_name)

        res = connection.execute(text(f"DESCRIBE {full_name}"))
        return res.first() is not None

    def get_schema_names(self, connection, **kw):
        """Return a list of schema names available in the database."""
        rp = connection.exec_driver_sql("SHOW schemas")
        return [r[0] for r in rp]

    def get_table_names(self, connection, schema: Optional[str] = None, **kw):
        """Return a Unicode SHOW TABLES from a given schema."""
        current_schema: str = cast(str, schema or self.default_schema_name)

        charset = self._connection_charset

        rp = connection.exec_driver_sql(
            "SHOW FULL TABLES FROM %s"
            % self.identifier_preparer.quote_identifier(current_schema)
        )

        return [
            row[0]
            for row in self._compat_fetchall(rp, charset=charset)
            if row[1] == "BASE TABLE"
        ]

    def get_view_names(self, connection, schema: Optional[str] = None, **kw):
        """Return a Unicode SHOW TABLES from a given schema."""
        if schema is None:
            schema = self.default_schema_name
        current_schema = cast(str, schema)
        charset = self._connection_charset
        rp = connection.exec_driver_sql(
            "SHOW FULL TABLES FROM %s"
            % self.identifier_preparer.quote_identifier(current_schema)
        )
        return [
            row[0]
            for row in self._compat_fetchall(rp, charset=charset)
            if row[1] in ("VIEW", "SYSTEM VIEW")
        ]

    def get_columns(  # type: ignore
        self,
        connection: Connection,
        table_name: str,
        schema: Optional[str] = None,
        **kw,
    ) -> List[Dict[str, Any]]:  # type: ignore
        """Return information about columns in `table_name`."""
        if not self.has_table(connection, table_name, schema):
            raise exc.NoSuchTableError(f"schema={schema}, table={table_name}")
        schema = schema or self._get_default_schema_name(connection)

        quote = self.identifier_preparer.quote_identifier
        full_name = quote(table_name)
        if schema:
            full_name = "{}.{}".format(quote(schema), full_name)

        res = connection.execute(text(f"SHOW COLUMNS FROM {full_name}"))
        columns = []
        for record in res:
            column = dict(
                name=record.Field,
                type=datatype.parse_sqltype(record.Type),
                nullable=record.Null == "YES",
                default=record.Default,
            )
            columns.append(column)
        return columns

    def get_pk_constraint(
        self, connection, table_name, schema: Optional[str] = None, **kw
    ):
        """Return information about the primary key constraint."""
        return {  # type: ignore  # pep-655 not supported
            "name": None,
            "constrained_columns": [],
        }

    def get_unique_constraints(  # type: ignore
        self,
        connection: Connection,
        table_name: str,
        schema: Optional[str] = None,
        **kw,
    ) -> List[Dict[str, Any]]:
        """Return information about unique constraints."""
        return []

    def get_check_constraints(  # type: ignore
        self,
        connection: Connection,
        table_name: str,
        schema: Optional[str] = None,
        **kw,
    ) -> List[Dict[str, Any]]:
        """Return information about check constraints."""
        return []

    def get_foreign_keys(  # type: ignore
        self,
        connection: Connection,
        table_name: str,
        schema: Optional[str] = None,
        **kw,
    ) -> List[Dict[str, Any]]:
        """Return information about foreign keys."""
        return []

    def get_primary_keys(
        self,
        connection: Connection,
        table_name: str,
        schema: Optional[str] = None,
        **kw,
    ) -> List[str]:
        """Return the primary key columns of the given table."""
        pk = self.get_pk_constraint(connection, table_name, schema)
        return pk.get("constrained_columns")  # type: ignore

    def get_indexes(self, connection, table_name, schema: Optional[str] = None, **kw):
        """Get table indexes about specified table."""
        return []

    def has_sequence(
        self,
        connection: Connection,
        sequence_name: str,
        schema: Optional[str] = None,
        **kw,
    ) -> bool:
        """Return True if the given sequence is present in the database."""
        return False

    def get_sequence_names(
        self, connection: Connection, schema: Optional[str] = None, **kw
    ) -> List[str]:
        """Return a list of sequence names."""
        return []

    def get_temp_view_names(
        self, connection: Connection, schema: Optional[str] = None, **kw
    ) -> List[str]:
        """Return a list of temporary view names."""
        return []

    def get_temp_table_names(
        self, connection: Connection, schema: Optional[str] = None, **kw
    ) -> List[str]:
        """Return a list of temporary table names."""
        return []

    def get_table_options(
        self, connection, table_name, schema: Optional[str] = None, **kw
    ):
        """Return a dictionary of options specified when the table was created."""
        return {}

    def get_table_comment(  # type: ignore
        self,
        connection: Connection,
        table_name: str,
        schema: Optional[str] = None,
        **kw,
    ) -> Dict[str, Any]:
        """Return the comment for a table."""
        return dict(text=None)

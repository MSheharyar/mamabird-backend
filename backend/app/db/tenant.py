import os
from supabase import create_client, Client


class TenantSafeQuery:
    """
    Wraps the Supabase client and auto-appends client_id to every query,
    preventing cross-tenant data leaks.
    """

    def __init__(self, client_id: str):
        self._client: Client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_SERVICE_KEY"),
        )
        self._client_id = client_id

    def table(self, table_name: str):
        return _TenantTable(self._client.table(table_name), self._client_id)


class _TenantTable:
    def __init__(self, query_builder, client_id: str):
        self._qb = query_builder
        self._client_id = client_id

    def select(self, *args, **kwargs):
        return self._qb.select(*args, **kwargs).eq("client_id", self._client_id)

    def insert(self, data: dict, **kwargs):
        data = {**data, "client_id": self._client_id}
        return self._qb.insert(data, **kwargs)

    def update(self, data: dict, **kwargs):
        return self._qb.update(data, **kwargs).eq("client_id", self._client_id)

    def delete(self, **kwargs):
        return self._qb.delete(**kwargs).eq("client_id", self._client_id)

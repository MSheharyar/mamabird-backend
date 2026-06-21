from supabase import Client


class TenantSafeQuery:
    """
    Wraps a shared Supabase client and auto-appends client_id to every
    query, preventing cross-tenant data leaks. Pass via FastAPI Depends
    using get_tenant_db from app.api.dependencies.
    """

    def __init__(self, client: Client, client_id: str):
        self._client = client
        self._client_id = client_id

    @property
    def client_id(self) -> str:
        return self._client_id

    def table(self, table_name: str) -> "_TenantTable":
        return _TenantTable(self._client.table(table_name), self._client_id)

    def rpc(self, fn_name: str, params: dict):
        return self._client.rpc(fn_name, params)


class _TenantTable:
    def __init__(self, query_builder, client_id: str):
        self._qb = query_builder
        self._client_id = client_id

    def select(self, *args, **kwargs):
        return self._qb.select(*args, **kwargs).eq("client_id", self._client_id)

    def insert(self, data: dict, **kwargs):
        return self._qb.insert({**data, "client_id": self._client_id}, **kwargs)

    def update(self, data: dict, **kwargs):
        return self._qb.update(data, **kwargs).eq("client_id", self._client_id)

    def delete(self, **kwargs):
        return self._qb.delete(**kwargs).eq("client_id", self._client_id)

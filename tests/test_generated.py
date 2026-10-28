"""The generated namespaces must match api-inventory/inventory.json exactly."""

import inspect
import json
import re
from pathlib import Path

import pytest

from confluence_dc import AsyncConfluence, Confluence
from confluence_dc._endpoint import Namespace

INVENTORY = json.loads(
    (Path(__file__).parent.parent / "api-inventory" / "inventory.json").read_text()
)
USER = {(e["method"], e["path"]) for e in INVENTORY["endpoints"] if e["audience"] == "user"}
ADMIN = {(e["method"], e["path"]) for e in INVENTORY["endpoints"] if e["audience"] == "admin"}


def namespaces(client):
    for name, ns in vars(client).items():
        if isinstance(ns, Namespace):
            yield name, ns
    for group in ("experimental", "internal"):
        for name, ns in vars(getattr(client, group)).items():
            yield f"{group}.{name}", ns


def generated(client):
    for ns_name, ns in namespaces(client):
        for attr, fn in inspect.getmembers(type(ns), inspect.isfunction):
            if hasattr(fn, "spec"):
                yield ns_name, attr, fn


@pytest.fixture(scope="module")
def methods():
    return list(generated(Confluence("https://x", token="t")))


def test_every_user_endpoint_generated_once(methods):
    keys = [(fn.spec.method, fn.spec.path) for _, _, fn in methods]
    assert len(keys) == len(set(keys))
    assert set(keys) == USER


def test_no_admin_endpoints(methods):
    assert not {(fn.spec.method, fn.spec.path) for _, _, fn in methods} & ADMIN


def test_tiers_map_to_namespaces(methods):
    for ns, _, fn in methods:
        if fn.spec.path.startswith("/rest/api/"):
            assert "." not in ns, ns
        elif fn.spec.path.startswith("/rest/experimental"):
            assert ns.startswith("experimental."), ns
        else:
            assert ns.startswith("internal."), ns


def test_path_params_are_required_positionals(methods):
    for ns, attr, fn in methods:
        wires = re.findall(r"\{(\w+)\}", fn.spec.path)
        assert [w for _, w in fn.spec.path_params] == wires, f"{ns}.{attr}"
        params = inspect.signature(fn).parameters
        for py, _ in fn.spec.path_params:
            p = params[py]
            assert p.default is inspect.Parameter.empty, f"{ns}.{attr}({py})"
            assert p.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_every_method_documented(methods):
    for ns, attr, fn in methods:
        doc = fn.__doc__ or ""
        assert f"``{fn.spec.method} {fn.spec.path}``" in doc, f"{ns}.{attr}"


def test_sync_and_async_expose_same_surface():
    sync = {(ns, attr) for ns, attr, _ in generated(Confluence("https://x", token="t"))}
    asyn = {(ns, attr) for ns, attr, _ in generated(AsyncConfluence("https://x", token="t"))}
    assert sync == asyn

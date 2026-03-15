# mesh-mcp — MCP server for NLM Medical Subject Headings (MeSH) APIs
# Copyright (C) 2026  May S. Chan (University of Toronto)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from mcp.server.fastmcp import FastMCP
import requests
import traceback

mcp = FastMCP("mesh mcp server")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BASE        = "https://id.nlm.nih.gov/mesh"
_LOOKUP_BASE = f"{_BASE}/lookup"
_HEADERS     = {"User-Agent": "mesh mcp server/1.0 (contact: ms.chan@utoronto.ca)"}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get(url: str, params: dict = None) -> dict:
    """
    Make a GET request and return parsed JSON as {"data": ...}, or {"error": ...}.
    """
    try:
        response = requests.get(url, params=params, headers=_HEADERS, timeout=10)
        response.raise_for_status()
        try:
            return {"data": response.json()}
        except Exception as json_err:
            return {
                "error": f"Failed to parse JSON: {json_err}",
                "raw_response": response.text[:2000],
                "traceback": traceback.format_exc(),
            }
    except Exception as e:
        return {
            "error": str(e),
            "type": type(e).__name__,
            "traceback": traceback.format_exc(),
        }


def _normalise_id(value: str) -> str:
    """
    Accept a full URI (http://id.nlm.nih.gov/mesh/D003920) or bare code
    (D003920) and return the bare code.
    """
    return value.rstrip("/").split("/")[-1].strip()


def _text(field) -> str:
    """
    Extract string value from a MeSH JSON-LD language-tagged literal.
    These come as {'@language': 'en', '@value': 'some text'} dicts.
    Falls back gracefully if the field is already a plain string or missing.
    """
    if isinstance(field, dict):
        return field.get("@value", "").strip()
    if isinstance(field, str):
        return field.strip()
    return ""


def _uri_to_id(uri: str) -> str:
    """Extract the bare MeSH code from a full URI string."""
    return uri.rstrip("/").split("/")[-1]


def _resolve_label(ui: str) -> str:
    """
    Fetch the preferred label for a MeSH UI code from its .json record.
    Returns the label string, or the UI code itself if the fetch fails.
    """
    result = _get(f"{_BASE}/{ui}.json")
    if "error" in result:
        return ui
    data = result["data"]
    if isinstance(data, dict):
        return _text(data.get("label", ui))
    return ui


# ---------------------------------------------------------------------------
# Tool: search_mesh
# ---------------------------------------------------------------------------

@mcp.tool()
def search_mesh(query: str, match: str = "startsWith", limit: int = 10) -> dict:
    """
    Search MeSH descriptors by label using the NLM Lookup autocomplete endpoint.

    Use this to find the MeSH UI code and URI for a biomedical concept before
    calling get_mesh_record or get_mesh_qualifiers.

    Parameters
    ----------
    query : str
        The label string to search for (e.g. "diabetes", "neoplasms").
    match : str
        Matching strategy:
          "startsWith" — left-anchored (default, analogous to LCSH suggest2)
          "contains"   — substring match anywhere in the label
          "exact"      — exact match only
    limit : int
        Maximum number of results to return (default 10, max 50).

    Returns
    -------
    dict
        A 'results' list of {label, ui, uri} dicts, or an 'error' key.
        'ui'  is the MeSH unique identifier (e.g. "D003920").
        'uri' is the full RDF URI (e.g. "http://id.nlm.nih.gov/mesh/D003920").
    """
    result = _get(
        f"{_LOOKUP_BASE}/descriptor",
        params={"label": query, "match": match, "limit": min(limit, 50)},
    )
    if "error" in result:
        return result

    raw = result["data"]
    if not isinstance(raw, list):
        return {"error": "Unexpected response format from NLM lookup", "data": raw}

    results = []
    for item in raw:
        uri   = item.get("resource", "")
        label = item.get("label", "")
        ui    = _uri_to_id(uri) if uri else ""
        results.append({"label": label, "ui": ui, "uri": uri})
    return {"results": results}


# ---------------------------------------------------------------------------
# Tool: get_mesh_record
# ---------------------------------------------------------------------------

@mcp.tool()
def get_mesh_record(descriptor: str) -> dict:
    """
    Retrieve a full MeSH descriptor record including scope note (annotation),
    tree numbers with their top-level category letters, broader descriptors,
    and see-also cross-references.

    Use this after search_mesh to obtain cataloging details for a confirmed
    MeSH heading.

    Parameters
    ----------
    descriptor : str
        The MeSH UI code (e.g. "D003920") or full URI returned by search_mesh.

    Returns
    -------
    dict
        A structured record containing:
          - ui             : MeSH unique identifier (e.g. "D003920")
          - uri            : Full RDF URI
          - label          : Preferred heading label
          - annotation     : Scope note / indexing annotation (if present)
          - dateIntroduced : Year the heading was introduced
          - lastUpdated    : Date the record was last updated
          - treeNumbers    : List of tree number strings (e.g. "C18.452.394.750")
          - treeCategories : Top-level category letters derived from tree numbers
          - broader        : List of {label, ui} dicts for parent descriptors
          - seeAlso        : List of {label, ui} dicts for cross-references
          - qualifierCount : Number of allowable qualifiers (full list via
                             get_mesh_qualifiers)
    """
    ui = _normalise_id(descriptor)
    result = _get(f"{_BASE}/{ui}.json")
    if "error" in result:
        return result

    data = result["data"]
    if not isinstance(data, dict):
        return {"error": f"Unexpected response format for descriptor {ui}", "data": data}

    out = {
        "ui":  ui,
        "uri": data.get("@id", f"http://id.nlm.nih.gov/mesh/{ui}"),
    }

    # ── Label ────────────────────────────────────────────────────────────────
    out["label"] = _text(data.get("label", ui))

    # ── Annotation (scope note / indexing guidance) ───────────────────────
    annotation = _text(data.get("annotation", ""))
    if annotation:
        out["annotation"] = annotation

    # ── Dates ─────────────────────────────────────────────────────────────
    if data.get("dateIntroduced"):
        out["dateIntroduced"] = str(data["dateIntroduced"])[:4]   # year only
    if data.get("lastUpdated"):
        out["lastUpdated"] = str(data["lastUpdated"])

    # ── Tree numbers ──────────────────────────────────────────────────────
    # treeNumber is a list of full URIs like
    # "http://id.nlm.nih.gov/mesh/C18.452.394.750"
    # The tree number string itself is the last path segment.
    raw_trees = data.get("treeNumber", [])
    if isinstance(raw_trees, str):
        raw_trees = [raw_trees]

    tree_numbers = [_uri_to_id(t) for t in raw_trees if t]
    if tree_numbers:
        out["treeNumbers"] = sorted(tree_numbers)
        categories = sorted(set(tn[0] for tn in tree_numbers if tn))
        out["treeCategories"] = categories

    # ── Broader descriptors ───────────────────────────────────────────────
    # broaderDescriptor is a list of URI strings; resolve each to a label.
    raw_broader = data.get("broaderDescriptor", [])
    if isinstance(raw_broader, str):
        raw_broader = [raw_broader]

    broader = []
    for uri in raw_broader:
        b_ui  = _uri_to_id(uri)
        b_lbl = _resolve_label(b_ui)
        broader.append({"label": b_lbl, "ui": b_ui})
    if broader:
        out["broader"] = broader

    # ── See also ─────────────────────────────────────────────────────────
    raw_see = data.get("seeAlso", [])
    if isinstance(raw_see, str):
        raw_see = [raw_see]

    see_also = []
    for uri in raw_see:
        s_ui  = _uri_to_id(uri)
        s_lbl = _resolve_label(s_ui)
        see_also.append({"label": s_lbl, "ui": s_ui})
    if see_also:
        out["seeAlso"] = see_also

    # ── Qualifier count (hint to call get_mesh_qualifiers) ────────────────
    raw_quals = data.get("allowableQualifier", [])
    if isinstance(raw_quals, str):
        raw_quals = [raw_quals]
    out["qualifierCount"] = len(raw_quals)

    return out


# ---------------------------------------------------------------------------
# Tool: get_mesh_qualifiers
# ---------------------------------------------------------------------------

@mcp.tool()
def get_mesh_qualifiers(descriptor: str, include_annotations: bool = False) -> dict:
    """
    Retrieve the allowable subheading qualifiers for a MeSH descriptor.

    MeSH qualifiers (subheadings) refine the topical focus of a heading —
    for example "Diabetes Mellitus/therapy" or "Neoplasms/diagnosis". Only
    qualifiers designated by NLM as allowable for the given descriptor are
    returned.

    This is the MeSH equivalent of the maySubdivideGeographically check used
    in the cataloger MCP server for LCSH headings.

    Note: The NLM public API does not expose qualifier abbreviations (e.g.
    /su for surgery). Use the full qualifier label when constructing headings
    in MARC: $a Diabetes Mellitus $x surgery.

    Parameters
    ----------
    descriptor : str
        The MeSH UI code (e.g. "D003920") or full URI returned by search_mesh.
    include_annotations : bool
        If True, fetch each qualifier's .json record to include its indexing
        annotation. Makes up to 34 additional HTTP requests — use only when
        you need the annotation text for a specific qualifier. Default False.

    Returns
    -------
    dict
        Contains:
          - descriptor     : The UI code queried
          - qualifierCount : Total number of allowable qualifiers
          - qualifiers     : List of {label, ui, uri} dicts sorted
                             alphabetically. If include_annotations=True,
                             each dict also has an 'annotation' key.
    """
    ui = _normalise_id(descriptor)

    result = _get(f"{_LOOKUP_BASE}/qualifiers", params={"descriptor": ui})
    if "error" in result:
        return result

    raw = result["data"]
    if not isinstance(raw, list):
        return {"error": "Unexpected response format from NLM qualifiers endpoint", "data": raw}

    qualifiers = []
    for item in raw:
        q_uri   = item.get("resource", "")
        q_label = item.get("label", "")
        q_ui    = _uri_to_id(q_uri) if q_uri else ""

        entry = {"label": q_label, "ui": q_ui, "uri": q_uri}

        if include_annotations and q_ui:
            ann_result = _get(f"{_BASE}/{q_ui}.json")
            if "data" in ann_result:
                ann_text = _text(ann_result["data"].get("annotation", ""))
                if ann_text:
                    entry["annotation"] = ann_text

        qualifiers.append(entry)

    qualifiers.sort(key=lambda x: x["label"])

    return {
        "descriptor":     ui,
        "qualifierCount": len(qualifiers),
        "qualifiers":     qualifiers,
    }


# ---------------------------------------------------------------------------
# Tool: get_mesh_tree
# ---------------------------------------------------------------------------

@mcp.tool()
def get_mesh_tree(descriptor: str) -> dict:
    """
    Retrieve the MeSH tree hierarchy for a descriptor: its tree numbers,
    the full name of each top-level category, and its immediate broader
    (parent) descriptors.

    Use this to understand where a heading sits within the MeSH hierarchy,
    helping to determine whether the heading is specific enough for the work
    or whether a broader heading would be more appropriate.

    MeSH tree number top-level categories:
      A  Anatomy
      B  Organisms
      C  Diseases
      D  Chemicals and Drugs
      E  Analytical, Diagnostic and Therapeutic Techniques and Equipment
      F  Psychiatry and Psychology
      G  Phenomena and Processes
      H  Disciplines and Occupations
      I  Anthropology, Education, Sociology and Social Phenomena
      J  Technology, Industry, and Agriculture
      K  Humanities
      L  Information Science
      M  Named Groups
      N  Health Care
      V  Publication Characteristics
      Z  Geographicals

    Parameters
    ----------
    descriptor : str
        The MeSH UI code (e.g. "D003920") or full URI returned by search_mesh.

    Returns
    -------
    dict
        Contains:
          - ui          : MeSH unique identifier
          - label       : Preferred heading label
          - treeNumbers : List of tree number strings
          - categories  : List of {letter, name} dicts for top-level categories
          - broader     : List of {label, ui} dicts for parent descriptors
    """
    _CATEGORY_NAMES = {
        "A": "Anatomy",
        "B": "Organisms",
        "C": "Diseases",
        "D": "Chemicals and Drugs",
        "E": "Analytical, Diagnostic and Therapeutic Techniques and Equipment",
        "F": "Psychiatry and Psychology",
        "G": "Phenomena and Processes",
        "H": "Disciplines and Occupations",
        "I": "Anthropology, Education, Sociology and Social Phenomena",
        "J": "Technology, Industry, and Agriculture",
        "K": "Humanities",
        "L": "Information Science",
        "M": "Named Groups",
        "N": "Health Care",
        "V": "Publication Characteristics",
        "Z": "Geographicals",
    }

    record = get_mesh_record(descriptor)
    if "error" in record:
        return record

    return {
        "ui":          record["ui"],
        "label":       record.get("label", ""),
        "treeNumbers": record.get("treeNumbers", []),
        "categories": [
            {"letter": c, "name": _CATEGORY_NAMES.get(c, "Unknown")}
            for c in record.get("treeCategories", [])
        ],
        "broader": record.get("broader", []),
    }


# ---------------------------------------------------------------------------
# Resources (optional convenience wrappers)
# ---------------------------------------------------------------------------

@mcp.resource("mesh://search/{query}")
def mesh_search_resource(query: str) -> dict:
    return search_mesh(query)


@mcp.resource("mesh://record/{ui}")
def mesh_record_resource(ui: str) -> dict:
    return get_mesh_record(ui)


@mcp.resource("mesh://qualifiers/{ui}")
def mesh_qualifiers_resource(ui: str) -> dict:
    return get_mesh_qualifiers(ui)


@mcp.resource("mesh://tree/{ui}")
def mesh_tree_resource(ui: str) -> dict:
    return get_mesh_tree(ui)


# ---------------------------------------------------------------------------
# Server startup
# ---------------------------------------------------------------------------

def start_mcp_server(port: int = None):
    """Entry point — starts in HTTP/SSE mode if port given, else stdio."""
    if port is not None:
        import uvicorn
        print(f"Starting MeSH MCP server on HTTP port {port}")
        uvicorn.run(mcp.sse_app(), host="0.0.0.0", port=port)
    else:
        mcp.run()


if __name__ == "__main__":
    start_mcp_server()

# MeSH MCP

An experimental MCP (Model Context Protocol) server connecting Claude to the U.S. National
Library of Medicine (NLM) Medical Subject Headings (MeSH) linked data APIs, built to investigate the potential of large language models in subject analysis and authority control.

-----

## What This Server Does

MeSH MCP connects Claude Desktop to the NLM MeSH APIs, allowing you to search and retrieve MeSH authority data directly within your AI-assisted cataloging workflow.


Once installed, you can ask Claude things like:

- *"Search MeSH for terms related to osmotic stress"*
- *"Find the MeSH descriptor for CRISPR gene editing"*
- *"What is the scope note for this MeSH descriptor?"*
- *"Look up the full record for descriptor D011506"*

The server handles all the API calls, parses the responses, and returns
structured data Claude can reason about.

-----

## Who This Is For

- **Catalogers and metadata staff** using Claude Desktop who want
  AI-assisted subject description grounded in real MeSH vocabulary data
- **Library and repository staff** working with health sciences or
  biomedical research outputs — theses, datasets, grey literature —
  where MeSH is the preferred controlled vocabulary
- **Developers** integrating MeSH lookups into MCP-based systems

-----

## Tools

| Tool | Description |
|------|-------------|
| `search_mesh` | Search MeSH descriptors by label using the NLM lookup autocomplete endpoint. Supports `startsWith` (default), `contains`, and `exact` matching. Returns a list of `{label, ui, uri}` dicts. |
| `get_mesh_record` | Retrieve the full record for a MeSH descriptor by UI code or URI. Returns label, annotation (scope note), tree numbers, tree categories, broader descriptors, see-also cross-references, and qualifier count. |
| `get_mesh_qualifiers` | Retrieve the allowable subheading qualifiers for a descriptor (e.g. `Diabetes Mellitus/therapy`). Optionally includes per-qualifier indexing annotations. |
| `get_mesh_tree` | Retrieve the MeSH tree hierarchy for a descriptor: tree numbers, top-level category names, and immediate broader (parent) descriptors. |

-----

## Notes on Search Behaviour

**`search_mesh` uses left-anchored matching by default** (`startsWith`), which matches from the beginning of the heading label. Searching `diabetes` will find `Diabetes Mellitus` and related headings, but searching `mellitus` will not. When a `startsWith` search returns no results, use `match="contains"` to search anywhere in the label.

**For highly specialized or emerging concepts** without a direct MeSH
equivalent — such as specific protein families or recently coined
terminology — search with a broader parent term and review the returned
hierarchy to identify the best available descriptor.

**Use `get_mesh_record` to verify before assigning.** Retrieve the full
record to confirm the scope note matches the intended concept,
particularly when multiple candidate terms are returned. Tree numbers
indicate where the term sits in the MeSH hierarchy and can guide
selection of broader or narrower terms.

-----

## Installation

### Requirements

- Python 3.11 or later
- Claude Desktop (or another MCP-compatible host)

### Install from GitHub

```bash
pip install git+https://github.com/YOUR_USERNAME/mesh-mcp.git
```

### Install from a local clone

```bash
git clone https://github.com/YOUR_USERNAME/mesh-mcp.git
cd mesh-mcp
pip install -e .
```

On Windows with Anaconda, use Anaconda Prompt and add
`--break-system-packages` if prompted.

-----

## Claude Desktop Configuration

After installation, add the server to your `claude_desktop_config.json`.
Claude Desktop uses a restricted PATH that does not include the Python
bin directory, so the full path to the command is required.

To find your exact path, run the following in Terminal (Mac) or
Anaconda Prompt (Windows):

- **Mac:** `which mesh-mcp`
- **Windows:** `where mesh-mcp`

The examples below are illustrative only — your actual path will differ
depending on your Python version and installation method.

**Mac (example):**

```json
{
  "mcpServers": {
    "mesh": {
      "command": "/Library/Frameworks/Python.framework/Versions/3.13/bin/mesh-mcp"
    }
  }
}
```

**Windows/Anaconda (example):**

```json
{
  "mcpServers": {
    "mesh": {
      "command": "C:\\Users\\username\\anaconda3\\Scripts\\mesh-mcp.exe"
    }
  }
}
```

Always replace the path with the actual output of the `which` or `where`
command on your machine.

**Finding your config file:**

- **Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

After editing the config, quit Claude Desktop completely and reopen it.
The MeSH tools will be available in your next conversation.

### Verifying the installation

Once Claude Desktop is open, ask: *"What cataloger tools do you have
available?"* — you should see all four MeSH tools listed.

-----

## Troubleshooting

**Tools not appearing in Claude Desktop**

- Confirm the package installed without errors: `pip show mesh-mcp`
- Confirm the command is available: `mesh-mcp --help` (should start
  the server, not throw an error)
- Check that the config file path is correct for your OS
- Quit Claude Desktop fully (not just close the window) before reopening

**Changes to server.py not taking effect**

Python caches compiled bytecode in `__pycache__` folders. After editing
`server.py`, delete any `__pycache__` folders in the package directory
and restart Claude Desktop fully.

-----

## Data Source

MeSH is produced by the U.S. National Library of Medicine and is freely
available with no license required. Attribution is appreciated.

- [MeSH home](https://www.nlm.nih.gov/mesh/)
- [MeSH browser](https://meshb.nlm.nih.gov/)
- [MeSH RDF / linked data](https://hhs.github.io/meshrdf/)

-----

## License

GPLv3. See [LICENSE](LICENSE).

-----

## Development Note

The code in this project was developed in collaboration with Claude,
Anthropic's AI assistant. The design decisions — including tool
selection, search protocols, and the application of MeSH cataloging
practice to the server's behaviour — reflect the author's professional
cataloging expertise. Claude handled the implementation of those
decisions in Python.

-----

## Acknowledgement

This project was inspired by and adapted from KL Tang's
[cataloger-mcp](https://github.com/kltng/cataloger-mcp), extended here
to apply to MeSH vocabulary lookup.

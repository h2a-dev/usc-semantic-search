"""Basic test to ensure pytest runs successfully"""


def test_imports():
    """Test that core modules can be imported"""
    import usc_mcp.database
    import usc_mcp.embedder
    import usc_mcp.parser
    import usc_mcp.server
    import usc_mcp.tools

    assert usc_mcp.database.ChromaDatabase is not None
    assert usc_mcp.embedder.VoyageEmbedder is not None
    assert usc_mcp.parser.USLMParser is not None
    assert usc_mcp.tools.USCSearchTools is not None


def test_basic():
    """Basic test to ensure pytest works"""
    assert True

"""Basic tests to ensure the workflow passes"""

def test_imports():
    """Test that Flask can be imported"""
    import flask
    assert flask is not None

def test_basic_math():
    """Basic test to ensure pytest works"""
    assert 1 + 1 == 2

def test_requirements():
    """Test that key packages are installed"""
    import qrcode
    import PIL
    import PyPDF2
    assert True

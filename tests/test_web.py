from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_index_serves_the_page():
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert 'id="upload-form"' in response.text
    assert "cytoscape" in response.text


def test_index_with_id_serves_the_same_page():
    # El id lo lee el JavaScript; el servidor siempre manda el mismo HTML.
    response = client.get("/", params={"id": "00000000-0000-0000-0000-000000000000"})
    assert response.status_code == 200
    assert 'id="upload-form"' in response.text


def test_static_files_are_served():
    script = client.get("/static/app.js")
    assert script.status_code == 200
    assert "javascript" in script.headers["content-type"]

    styles = client.get("/static/styles.css")
    assert styles.status_code == 200
    assert styles.headers["content-type"].startswith("text/css")


def test_index_is_not_in_the_api_docs():
    assert "/" not in client.get("/openapi.json").json()["paths"]


def test_cytoscape_is_served_from_the_repo():
    # La página no depende de un CDN: Cytoscape va en app/static/vendor/.
    response = client.get("/static/vendor/cytoscape.min.js")
    assert response.status_code == 200
    assert "cytoscape" in response.text


def test_index_has_my_analyses_section():
    page = client.get("/").text
    assert 'id="history-list"' in page
    # app.js usa HistoryStore, así que history.js tiene que cargarse antes.
    assert page.index("/static/history.js") < page.index("/static/app.js")


def test_index_loads_blast_radius_before_app():
    page = client.get("/").text
    assert 'id="blast-info"' in page
    # app.js usa las funciones de blast-radius.js.
    assert page.index("/static/blast-radius.js") < page.index("/static/app.js")


def test_blast_radius_script_is_served():
    response = client.get("/static/blast-radius.js")
    assert response.status_code == 200
    assert "function highlightBlastRadius" in response.text


def test_history_script_is_served():
    response = client.get("/static/history.js")
    assert response.status_code == 200
    assert "class HistoryStore" in response.text


def test_index_loads_node_details_before_app():
    page = client.get("/").text
    assert 'id="node-details"' in page
    # app.js usa nodeDetails de node-details.js.
    assert page.index("/static/node-details.js") < page.index("/static/app.js")


def test_node_details_script_is_served():
    response = client.get("/static/node-details.js")
    assert response.status_code == 200
    assert "function nodeDetails" in response.text


def test_index_loads_theme_before_the_page_is_drawn():
    page = client.get("/").text
    assert 'id="theme-toggle"' in page
    # theme.js va sin defer y antes de app.js para aplicar el tema desde el inicio.
    assert '<script src="/static/theme.js"></script>' in page
    assert page.index("/static/theme.js") < page.index("/static/app.js")


def test_theme_script_is_served():
    response = client.get("/static/theme.js")
    assert response.status_code == 200
    assert "function initialTheme" in response.text

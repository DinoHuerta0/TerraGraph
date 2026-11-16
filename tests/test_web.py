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


def test_history_script_is_served():
    response = client.get("/static/history.js")
    assert response.status_code == 200
    assert "class HistoryStore" in response.text

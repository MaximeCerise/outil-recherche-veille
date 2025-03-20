from fastapi import FastAPI
import requests
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import xml.etree.ElementTree as ET
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

GITHUB_API = "https://api.github.com/search/repositories"
ARXIV_API = "http://export.arxiv.org/api/query"
SCINAPSE_API = "https://api.scinapse.io/search"
GOOGLE_SCHOLAR_API = "https://serpapi.com/search.json"
SERPAPI_KEY = "743f818cfcf1f42e011e3e9a9babfa56ce95ea112fba659bcc80140fb318aced"
SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1/paper/search"

@app.get("/search_semantic")
def search_papers(query: str):
    params = {
        "query": query,
        "fields": "title,authors,url,abstract,year",
        "sort": "year"  # Trie par année de publication (du plus récent au plus ancien)
    }
    response = requests.get(SEMANTIC_SCHOLAR_API, params=params)
    
    if response.status_code == 200:
        data = response.json()
        return data.get("data", [])
    else:
        return {"error": f"API request failed with status {response.status_code}"}
@app.get("/search_github")
def search_github(query: str):
    params = {"q": query, "sort": "stars", "order": "desc"}
    headers = {"Accept": "application/vnd.github.v3+json"}
    response = requests.get(GITHUB_API, params=params, headers=headers)
    data = response.json()
    return data.get("items", [])

@app.get("/search_arxiv")
def search_arxiv(query: str):
    params = {
        "search_query": query,
        "start": 0,
        "max_results": 10,
        "sortBy": "submittedDate",  # Trie par date de soumission
        "sortOrder": "descending"   # Du plus récent au plus ancien
    }
    response = requests.get(ARXIV_API, params=params)

    if response.status_code != 200:
        return []

    root = ET.fromstring(response.text)
    namespace = {"arxiv": "http://www.w3.org/2005/Atom"}

    articles = []
    for entry in root.findall("arxiv:entry", namespace):
        title = entry.find("arxiv:title", namespace).text.strip()
        summary = entry.find("arxiv:summary", namespace).text.strip()
        link = entry.find("arxiv:id", namespace).text.strip()
        published = entry.find("arxiv:published", namespace).text.strip()

        articles.append({
            "title": title,
            "summary": summary,
            "url": link,
            "published": published
        })

    return articles

@app.get("/search_scinapse")
def search_scinapse(query: str):
    params = {"query": query}
    response = requests.get(SCINAPSE_API, params=params)
    return response.json()

@app.get("/search_google_scholar")
def search_google_scholar(query: str):
    params = {
        "q": query,
        "engine": "google_scholar",
        "api_key": SERPAPI_KEY
    }
    
    response = requests.get(GOOGLE_SCHOLAR_API, params=params)
    data = response.json()

    results = []
    for article in data.get("organic_results", []):
        title = article.get("title", "Titre inconnu")
        summary = article.get("snippet", "Résumé non disponible")
        date = article.get("publication_info", {}).get("summary","date non dispo")
        link = article.get("link", "Lien non disponible")

        results.append({
            "title": title,
            "date": date,
            "summary": summary,
            "link": link
        })
    print(results)
    return results

@app.get("/", response_class=HTMLResponse)
def home():
    with open("static/index.html", "r", encoding="utf-8") as file:
        return file.read()

@app.get("/results", response_class=HTMLResponse)
def show_results(query: str):
    papers = search_papers(query)
    github_repos = search_github(query)
    scinapse_results = search_scinapse(query)
    google_scholar_results = search_google_scholar(query)
    
    with open("static/results.html", "r", encoding="utf-8") as file:
        html_template = file.read()

    semantic_html = "".join(
        f"<li><a href='{paper.get('url', '#')}'><strong>{paper.get('title', 'Titre inconnu')}</strong></a> "
        f"- {', '.join([author['name'] for author in paper.get('authors', [])])} "
        f"({paper.get('year', 'N/A')})</li>"
        f"<strong>Résumé :</strong> {paper.get('abstract', 'Résumé non disponible')}</li>"
        for paper in papers
    )
    
    github_html = "".join(
        f"<li><a href='{repo['html_url']}'>{repo['name']}</a> - ⭐ {repo['stargazers_count']}</li>"
        for repo in github_repos
    )
    
    
    scinapse_html = "".join(
        f"<li>{paper['title']}</li>"
        for paper in scinapse_results.get("data", [])
    )
    
    google_scholar_html = "".join(
        f"<li>"
        f"<a href='{result.get('link', '#')}'><strong>{result.get('title', 'Titre inconnu')}</strong></a><br>"
        f"<em>{result.get('date', {})}</em><br>"
        f"<strong>Résumé :</strong>{result.get('summary', 'Résumé non disponible')}"
        f"</li>"
        for result in google_scholar_results  # On itère directement sur la liste
    )

    
    return (html_template.replace("{{github_results}}", github_html)
            .replace("{{semantic_results}}", semantic_html)
            .replace("{{scinapse_results}}", scinapse_html)
            .replace("{{google_scholar_results}}", google_scholar_html)
            .replace("{{query}}", query))

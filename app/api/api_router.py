import re
import networkx as nx
from fastapi import HTTPException, APIRouter
from itertools import combinations
from app.services.book_service import fetch_book_info, fetch_book_content
from app.core.connexiondb import Connection

router = APIRouter()

index_table = Connection(db_uri='mongodb://localhost:27017/', db_name='booksdb').get_collection('index')


@router.get("/{book_id}")
async def get_book_info(book_id: int):
    try:
        book_info = fetch_book_info(book_id)
    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=f"Erreur lors de la récupération des informations du livre avec l'ID {book_id}: {e}")

    if "error" in book_info:
        raise HTTPException(status_code=404, detail=f"Impossible de trouver le livre avec l'ID {book_id}")

    return book_info


@router.get("/{book_id}/read")
async def get_book_info(book_id: int):
    try:
        book_content = fetch_book_content(book_id)
    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=f"Erreur lors de la récupération du contenu du livre avec l'ID {book_id}: {e}")

    if "error" in book_content:
        raise HTTPException(status_code=404, detail=f"Impossible de trouver le livre avec l'ID {book_id}")

    return book_content


# @router.get("/page={page_num}")
# def get_page_books(page_num: int):
#     try:
#         url = f"https://gutendex.com/books/page={page_num}"
#         response = requests.get(url)
#     except Exception as e:
#         raise HTTPException(status_code=500,
#                             detail=f"Erreur lors de la récupération des informations des livre")
#     return json.loads(response.content.decode())


@router.get("/search")
async def search_books(q: str):
    q = q.strip().lower()
    # Recherche des documents contenant le mot-clé dans la table des index
    results = index_table.find({"word": {"$regex": f".*{q}.*"}})

    # Création du graphe de Jaccard pour les documents correspondants
    G = nx.Graph()
    for result in results:
        books = result["books"]
        for i, book1 in enumerate(books):
            G.add_node(book1["book_id"])
            for book2 in books[i + 1:]:
                intersection_size = len(set(book1["position"]).intersection(set(book2["position"])))
                union_size = len(set(book1["position"]).union(set(book2["position"])))
                if union_size > 0:
                    similarity = intersection_size / union_size
                    G.add_edge(book1["book_id"], book2["book_id"], weight=similarity)

    # Calcul de l'indice pagerank pour chaque document
    pageranks = nx.pagerank(G)

    # Création de la liste des livres correspondants
    books = []
    for result in results:
        for book in result["books"]:
            book_id = book["book_id"]
            count = book["count"]
            pagerank = pageranks.get(book_id, 0)
            books.append({"book_id": book_id, "count": count, "pagerank": pagerank})

    # Tri des livres en fonction de l'indice pagerank décroissant
    sorted_books = sorted(books, key=lambda x: x["pagerank"], reverse=True)

    # Récupération des deux ou trois livres les plus pertinents
    top_books = sorted_books[:3]

    # Recherche des voisins des livres les plus pertinents
    neighbors = set()
    for book in top_books:
        for neighbor in G.neighbors(book["book_id"]):
            if neighbor not in [book["book_id"] for book in top_books]:
                neighbors.add(neighbor)

    # Renvoi de la liste des livres correspondants et des voisins des livres les plus pertinents
    return {"books": sorted_books, "neighbors": list(neighbors)}


@router.get('/search/regex')
async def search_books_by_regex(regex: str):
    regex = re.compile(regex)
    results = index_table.find({'word': {'$regex': regex}})

    # Construire le graphe de Jaccard à partir des livres qui contiennent le mot-clé
    G = nx.Graph()
    books = {}
    for result in results:
        for book in result['books']:
            book_id = book['book_id']
            if book_id not in books:
                books[book_id] = {'count': 0, 'words': set()}
            books[book_id]['count'] += book['count']
            books[book_id]['words'].add(result['word'])

    for book1, book2 in combinations(books.keys(), 2):
        common_words = books[book1]['words'].intersection(books[book2]['words'])
        if common_words:
            jaccard_coefficient = len(common_words) / len(books[book1]['words'].union(books[book2]['words']))
            G.add_edge(book1, book2, weight=jaccard_coefficient)

    # Calculer le PageRank pour chaque livre
    pagerank_scores = nx.pagerank(G)

    # Tri des livres en fonction de leur indice PageRank
    sorted_books = sorted(books.items(), key=lambda x: pagerank_scores.get(x[0], 0), reverse=True)
    sorted_books = [{'book_id': book_id, 'count': book['count']} for book_id, book in sorted_books]

    return {'books': sorted_books}

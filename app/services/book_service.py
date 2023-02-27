import re

import pymongo
import requests
import json
import nltk
import concurrent.futures
from nltk.corpus import stopwords
from app.core.connexiondb import Connection

connexion = Connection(db_uri='mongodb://localhost:27017/', db_name='booksdb')

start_id = 0
end_id = 2000
book_ids = range(start_id, end_id)

nltk.download('stopwords')
stopwords = set(stopwords.words('english'))


def fetch_book_info(book_id: int) -> str:
    """
    Récupère les informations d'un livre en utilisant l'API de Gutendex
    """
    url = f"https://gutendex.com/books/{book_id}"
    response = requests.get(url)
    return json.loads(response.content.decode())


def fetch_book_content(book_id: int):
    """
    Récupère le contenu d'un livre via l'API de Gutemberg
    """
    url = f"https://gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt"

    try:
        response = requests.get(url)
        response.raise_for_status()  # Vérifie si la réponse contient un code de statut 4xx ou 5xx
    except Exception as e:
        print(f"Impossible de récupérer le contenu du livre avec l'ID {book_id}: {e}")
        return None
    return response.content.decode()


def count_word_occurrences(content: str, word: str) -> int:
    """
    Compte le nombre d'occurrences d'un mot dans le contenu d'un livre
    """
    return content.lower().count(word)


def filter_words(words: list) -> list:
    """
    Filtre les mots qui ont 3 caractères numériques ou moins
    """
    return [word for word in words if len(re.findall(r'\w', word)) > 2 and word not in stopwords]


def create_index():
    index_table = connexion.get_collection('index')
    batch_size = 100  # Nombre de documents à insérer à chaque opération d'insertion
    batch = []  # Liste pour stocker les résultats à insérer

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        # Pour chaque livre, exécuter la fonction fetch_and_process_book() en parallèle en utilisant un thread
        futures = [executor.submit(fetch_and_process_book, book_id) for book_id in book_ids]

        # Récupérer les résultats et les ajouter à la liste batch
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result is not None:
                batch.extend(result)

            # Insertion des résultats en batch
            if len(batch) >= batch_size:
                index_table.insert_many(batch)
                batch = []

        # Insertion des résultats restants
        if len(batch) > 0:
            index_table.insert_many(batch)

    # Utilisation de l'index pour améliorer les performances
    index_table.create_index([('word', pymongo.ASCENDING)])
    index_table.create_index([('book_id', pymongo.ASCENDING)])


def fetch_and_process_book(book_id):
    """
    Récupère les informations et le contenu d'un livre, puis traite les données et retourne les résultats sous forme de liste.
    """
    # Récupération des informations du livre
    book_info = fetch_book_info(book_id)

    # Vérification que les informations du livre ne sont pas None
    if book_info is None:
        print(f"Les informations du livre avec l'ID {book_id} n'ont pas pu être récupérées.")
        return None

    # Récupération du contenu du livre
    content = fetch_book_content(book_id)

    # Vérification que le contenu du livre n'est pas None
    if content is None:
        print(f"Le contenu du livre avec l'ID {book_id} n'a pas pu être récupéré.")
        return None

    # Comptage du nombre de mots différents
    unique_words = set(re.findall(r'\b\w+\b', content.lower()))

    # Filtrage des mots de 1 ou 2 caractères alphanumériques
    filtered_words = filter_words(unique_words)

    # Création des résultats pour ce livre
    book_results = []
    for word in filtered_words:
        result = {"word": word, "book_ids": []}
        if not connexion.get_collection('index').find_one({"word": word}):
            # Si le mot n'existe pas encore dans la collection, on l'insère avec un id vide
            result["_id"] = connexion.get_collection('index').insert_one(result).inserted_id
        else:
            # Sinon, on récupère l'id du document existant
            existing_doc = connexion.get_collection('index').find_one({"word": word})
            result["_id"] = existing_doc["_id"]
            result["book_ids"] = existing_doc["book_ids"]
        result["book_ids"].append(book_id)
        book_results.append(result)

    # Mise à jour des résultats pour chaque mot
    for result in book_results:
        connexion.get_collection('index').update_one(
            {"_id": result["_id"]},
            {"$set": {"book_ids": result["book_ids"]}}
        )

    return book_results


create_index()

import re
import requests
import json
from app.core.connexiondb import Connection

connexion = Connection(db_uri='mongodb://localhost:27017/', db_name='booksdb')

index_table = connexion.get_collection('index')

start_id = 0
end_id = 12
book_ids = range(start_id, end_id)


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
    Filtre les mots qui ont 2 caractères numériques ou moins
    """
    return [word for word in words if len(re.findall(r'\w', word)) > 2]


def create_index():
    for book_id in book_ids:
        # Récupération du contenu du livre
        content = fetch_book_content(book_id)

        # Vérification que le contenu du livre n'est pas None
        if content is None:
            print(f"Le contenu du livre avec l'ID {book_id} n'a pas pu être récupéré.")
            continue

        # Comptage du nombre de mots différents
        unique_words = set(re.findall(r'\b\w+\b', content.lower()))
        print(f"{len(unique_words)} mots différents dans le livre {book_id}")

        # Filtrage des mots de 1 ou 2 caractères alphanumériques
        filtered_words = filter_words(unique_words)
        print(f"{len(filtered_words)} mots filtrés dans le livre {book_id}")

        # Comptage du nombre d'occurrences pour chaque mot filtré
        word_counts = {}
        for word in filtered_words:
            count = count_word_occurrences(content, word)
            word_counts[word] = count

        # Insertion des mots et de leur liste de livres associés dans la collection pour la table des index
        for word, count in word_counts.items():
            book_list = index_table.find_one({"word": word})
            if book_list is None:
                book_list = {"word": word, "books": []}
            book_list["books"].append({"book_id": book_id, "count": count})
            index_table.replace_one({"word": word}, book_list, upsert=True)


create_index()

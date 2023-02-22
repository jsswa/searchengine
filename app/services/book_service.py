import re
import requests
from pymongo import MongoClient

mongo_client = MongoClient("mongodb://localhost:27017/")
db = mongo_client["booksdb"]
index_collection = db['index']

start_id = 0
end_id = 12
book_ids = range(start_id, end_id)


def fetch_book_info(book_id: int) -> str:
    """
    Récupère les informations d'un livre en utilisant l'API de Gutendex
    """
    url = f"https://gutendex.com/books/{book_id}"
    response = requests.get(url)
    return response.content.decode()

def fetch_book_content(book_id: int):
    """
    Récupère le contenu d'un livre via l'API de Gutemberg
    """
    url = f"https://gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt"
    response = requests.get(url)
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

print(book_ids)

for book_id in book_ids:
    # Récupération du contenu du livre
    content = fetch_book_content(book_id)

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
        book_list = index_collection.find_one({"word": word})
        if book_list is None:
            book_list = {"word": word, "books": []}
        book_list["books"].append({"book_id": book_id, "count": count})
        index_collection.replace_one({"word": word}, book_list, upsert=True)
